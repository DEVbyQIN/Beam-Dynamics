#!/usr/bin/env python3
"""Longitudinal constraints, paper Gz, analytical drift and real SC->RF checks.

No reports/config/baselines are overwritten. The expanded Eq.(20) reference
is deliberately separate from the implementation's reduced F/G pairing.
"""
import copy
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'AG')]
import beam_dynamics_6d as bd
from AG.longitudinal_state import inspect_longitudinal_state, check_initial_longitudinal_state, history_diagnostics
from shared.params import load_config, config_sha
from validation.backend import run_ag


def initial_beam(sc=False, correlated=False):
    b = bd.make_beam_100keV(Ne=100e-15/bd.E_CHARGE if sc else 0,
        sigma_delta=1e-4, eps_nx_um=.08, eps_ny_um=.08)
    if correlated:
        b.C_zd = .35*b.sigma_z*b.sigma_delta
        b.nu_z = b.C_zd/(b.gamma**2*b.sigma_z)
    b.eps_nz = inspect_longitudinal_state(b)['epsilon_from_covariance_mm_mrad']*1e-6
    return b


def short_config():
    c=load_config()
    c['lattice']['elements']=[
        dict(name='drift',type='drift',z_start=0.,length=.02,parameters={}),
        dict(name='rf',type='rf_cavity',z_start=.02,length=.022,
             parameters=dict(frequency_GHz=2.856,voltage_kV=30.,phase_rad=3.1416)),
        dict(name='tail',type='drift',z_start=.042,length=.011,parameters={}),
        dict(name='sample',type='sample',z_start=.053,length=0.,parameters={})]
    c['output']['z_diagnostics_mm']=[0.,20.,53.]
    return c


def paper_theta_Gz(b):
    """Independent expanded Eq.(20), evaluated with long-double arithmetic.

    Uses the existing alpha interpolation, so this checks Gz transcription,
    not the accuracy of the alpha table or the Gaussian closure itself.
    """
    t=np.longdouble
    sx,sy,sz,nx,ny,nz,tx,ty,tz,g,p,be=map(t,[b.sigma_x,b.sigma_y,b.sigma_z,
        b.nu_x,b.nu_y,b.nu_z,b.theta_x,b.theta_y,b.theta_z,b.gamma,b.p0,b.beta])
    a={k:t(v) for k,v in bd.alpha_at(float(sx/(g*sz)),float(sy/(g*sz))).items()}
    fb=(t(bd.E_CHARGE)/(t(bd.M_E)*t(bd.C_LIGHT)**2))*t(b.Ne)*t(bd.E_CHARGE)/(8*t(np.pi)*np.sqrt(t(np.pi))*t(bd.EPSILON_0))
    bracket=3*(1-p*p)*(6*tz*tz*a['z']-nz*nz*a['zz'])/(2*sx*sy)
    bracket+=(2*g*g*sz*sz*tx*tx*a['z']-nx*nx*sx*sy*a['xz'])/(2*sx*sy*g*g*sz*sz)
    bracket+=(2*g*g*sz*sz*ty*ty*a['z']-ny*ny*sx*sy*a['yz'])/(2*sx*sy*g*g*sz*sz)
    return (fb*nz*a['z']/(be*be*g**3*sx*sy)-fb*nz*bracket/(2*g)
        -fb*nx*(2*tz*tz*a['x']-nz*nz*a['xz'])/(2*g*sx*sz)
        -fb*ny*(2*tz*tz*a['y']-nz*nz*a['yz'])/(2*g*sy*sz))


class LongitudinalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sc0=initial_beam(sc=True)
        cls.s,cls.states=bd.propagate(cls.sc0,(0.,.4),n_points=81)
        cls.end=bd.Beam6D.from_state(cls.states[-1],cls.states[-1,11],cls.sc0.Ne,
            cls.sc0.eps_nx,cls.sc0.eps_ny,cls.sc0.eps_nz)

    def test_correlated_input_constraint(self):
        b=initial_beam(correlated=True)
        self.assertTrue(check_initial_longitudinal_state(b,policy='error')['consistent'])
        self.assertAlmostEqual(b.theta_z,b.sigma_delta/b.gamma**2)

    def test_impossible_inputs(self):
        cases=[('sigma_z',0),('sigma_delta',-1e-4),('eps_nz',-1),
               ('gamma',1),('C_zd',1.),('nu_z',float('nan')),('sigma_delta',float('inf'))]
        for name,value in cases:
            with self.subTest(name=name,value=value):
                b=initial_beam(); setattr(b,name,value)
                with self.assertRaises(ValueError): inspect_longitudinal_state(b)

    def test_strict_initial_mismatch(self):
        b=initial_beam(); b.eps_nz=.02e-6
        with self.assertRaisesRegex(ValueError,'initial state is inconsistent'):
            check_initial_longitudinal_state(b,policy='error')

    def test_shared_input_priority_and_config_unchanged(self):
        c=short_config(); sha=config_sha(c)
        r=run_ag(c,'full',n_points=100,longitudinal_check='error')
        d=r.meta['longitudinal_initial_state']
        self.assertTrue(d['consistent']); self.assertFalse(d['epsilon_configured_used'])
        self.assertIsNone(d['epsilon_configured_mm_mrad'])
        self.assertAlmostEqual(d['epsilon_input_mm_mrad'],.01966515033425086,places=13)
        self.assertEqual(config_sha(c),sha)

    def test_invalid_input_fails_before_sc_setup(self):
        c=short_config(); c['initial_distribution']['sigma_delta']=float('nan')
        with patch.object(bd,'get_alpha_interpolators',side_effect=AssertionError('SC setup reached')):
            with self.assertRaisesRegex(ValueError,'sigma_delta must be finite'):
                run_ag(c,'full')

    def test_paper_eq20_independent_expansion(self):
        for energy in (100_000.,5_000_000.):
            for sign in (-1,1):
                b=initial_beam(sc=True)
                b.gamma=bd.beamK_to_gamma(energy)
                b.sigma_y*=1.7
                b.nu_x=.003; b.nu_y=-.002; b.nu_z=sign*.005
                # A finite thermal part makes the G/F difference observable.
                b.sigma_delta=b.gamma**2*.008
                b.C_zd=b.gamma**2*b.sigma_z*b.nu_z
                area=b.sigma_z**2*(b.theta_z**2-b.nu_z**2)
                fz=bd.space_charge_forces(b)[2]
                actual=b.nu_z*fz+.5*bd.longitudinal_sc_area_log_rate(b)*area/b.sigma_z**2
                expected=float(paper_theta_Gz(b))
                self.assertLess(abs(actual-expected)/max(abs(expected),1e-100),2e-13)

    def test_covariance_rhs_includes_sc(self):
        b=self.end; y=np.r_[b.state_vector(),b.gamma]
        dy=bd.envelope_ode(.4,y,b.Ne,b.eps_nx,b.eps_ny,b.eps_nz)
        fz=bd.space_charge_forces(b)[2]
        expected=b.sigma_delta**2/b.gamma**2+b.gamma**2*b.sigma_z*fz
        self.assertAlmostEqual(dy[5]/expected,1.,places=12)
        self.assertGreater(dy[4],0.)

    def test_analytical_correlated_drift(self):
        b=initial_beam(correlated=True)
        s,y=bd.propagate(b,(0.,.4),n_points=81,rtol=1e-10,atol=1e-12)
        a=1/b.gamma**2
        A=b.sigma_z**2+2*a*b.C_zd*s+a*a*b.sigma_delta**2*s*s
        C=b.C_zd+a*b.sigma_delta**2*s
        np.testing.assert_allclose(y[:,2],np.sqrt(A),rtol=1e-8,atol=0.)
        np.testing.assert_allclose(y[:,5],C,rtol=1e-8,atol=0.)
        np.testing.assert_allclose(y[:,4],b.sigma_delta,rtol=1e-8,atol=0.)

    def test_sc_state_and_rf_zero_identity(self):
        self.assertGreater(self.end.sigma_delta/self.sc0.sigma_delta,10.)
        self.assertTrue(inspect_longitudinal_state(self.end)['consistent'])
        out=bd.apply_rf_thin_lens(self.end,0.)
        np.testing.assert_array_equal(out.state_vector(),self.end.state_vector())

    def test_rf_matrix_roundtrip_and_determinant(self):
        b=self.end; H=-9.778852054935257
        S=np.array([[b.sigma_z**2,b.C_zd],[b.C_zd,b.sigma_delta**2]])
        L=np.array([[1.,0.],[H,1.]])
        out=bd.apply_rf_thin_lens(b,H)
        observed=np.array([[out.sigma_z**2,out.C_zd],[out.C_zd,out.sigma_delta**2]])
        np.testing.assert_allclose(observed,L@S@L.T,rtol=1e-12,atol=1e-22)
        self.assertLess(abs(np.linalg.det(observed)/np.linalg.det(S)-1),1e-9)
        back=bd.apply_rf_thin_lens(out,-H)
        np.testing.assert_allclose(back.state_vector(),b.state_vector(),rtol=1e-10,atol=1e-18)

    def test_rf_rejects_old_inconsistent_state(self):
        b=self.end.copy(); b.C_zd=0.
        with self.assertRaisesRegex(ValueError,'RF input has inconsistent'):
            bd.apply_rf_thin_lens(b,0.)

    def test_solver_failure_not_a_partial_success(self):
        class Failed:
            success=False; t=np.array([0.,.001]); message='injected early termination'
        with patch.object(bd,'solve_ivp',return_value=Failed()):
            with self.assertRaisesRegex(RuntimeError,'injected early termination'):
                bd.propagate(initial_beam(),(0.,.4))

    def test_cli_serializes_the_same_longitudinal_history(self):
        from AG.run_shared import main as cli
        c=short_config(); c['space_charge']['enabled']=True
        r=run_ag(c,'full')
        with tempfile.TemporaryDirectory(prefix='ued_longitudinal_cli_') as td:
            with contextlib.redirect_stdout(io.StringIO()):
                p=cli(out_dir=td,cfg_override=c)
            saved=json.loads(Path(p).read_text())
        self.assertEqual(saved['meta']['longitudinal_evolution'],r.meta['longitudinal_evolution'])
        for name,values in r.history().items():
            np.testing.assert_array_equal(saved['history'][name],values)

    def test_linear_ellipsoid_preserves_slope_emittance(self):
        b=initial_beam(sc=True)
        s,y=bd.propagate(b,(0.,.05),sc_model='ellipsoid',n_points=31)
        e=np.array(history_diagnostics(y)['epsilon_geometric_z_zprime_m'])
        np.testing.assert_allclose(e,e[0],rtol=1e-9,atol=0.)

    def test_zero_emittance_boundary_is_not_a_negative_variance(self):
        b=initial_beam(sc=True); b.sigma_delta=0.; b.eps_nz=0.
        s,y=bd.propagate(b,(0.,.02),n_points=21)
        d=history_diagnostics(y)
        self.assertLess(max(d['epsilon_geometric_z_zprime_m']),1e-11)
        self.assertGreater(y[-1,4],0.)


def main():
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LongitudinalTests))
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':
    sys.exit(main())
