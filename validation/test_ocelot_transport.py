"""Actual map selection and independent fixed-reference transport checks.

No AG comparison is used as the mathematical reference.  The free-particle
reference follows E^2=m^2c^4+c^2|p|^2 and flight time L/v_s.  Short formal
driver tests check execution/serialization only, not SC physical precision.
"""
import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from scipy.linalg import expm

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from ocelot import Drift, Solenoid, MagneticLattice, SecondTM, TransferMap
from ocelot.common.globals import m_e_GeV
from GPT模拟 import ued_beamline_v2 as model
from shared.params import load_config
from validation.backend import run_ocelot

E=.000611   # total energy [GeV], consistent with the production input
L=.1


def exact_drift(X, length=L, energy=E):
    """Independent mass-shell/free-flight reference in native coordinates."""
    Y=np.asarray(X,dtype=np.longdouble).copy()
    beta=np.sqrt(1-(np.longdouble(m_e_GeV)/np.longdouble(energy))**2)
    a,b,q=Y[1].copy(),Y[3].copy(),Y[5].copy()
    ps=np.sqrt(1+2*q/beta+q*q-a*a-b*b)
    Y[0]+=np.longdouble(length)*a/ps
    Y[2]+=np.longdouble(length)*b/ps
    Y[4]+=np.longdouble(length)*((1/beta+q)/ps-1/beta)
    return Y.astype(float)


def short_config(sc=False):
    c=copy.deepcopy(load_config())
    c['beam']['n_particles']=1500
    c['space_charge'].update(enabled=sc,mesh=[33,33,33])
    elements=[]
    s=0.
    for name,kind,length,params in [
        ('cathode','cathode',0.,{}),('d1','drift',.012,{}),
        ('sol','solenoid',.006,{'B_field_T':.05}),
        ('rf','rf_cavity',.022,{'frequency_GHz':2.856,'voltage_kV':30.,'phase_rad':3.1416}),
        ('d2','drift',.013,{}),('sample','sample',0.,{})]:
        elements.append(dict(name=name,type=kind,z_start=s,length=length,parameters=params))
        s+=length
    c['lattice']['elements']=elements
    c['output'].update(step_size_m=.007,z_diagnostics_mm=[0,12,18,40,53])
    return c


def quiet(fn,*args,**kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args,**kwargs)


class OcelotTransportTest(unittest.TestCase):
    def test_formal_builder_uses_verified_family_methods(self):
        cfg=load_config()
        for active in model.STEP_ACTIVE.values():
            for markers in [False,True]:
                lat,_=model.build_lattice_from_shared(cfg,active,keep_zero_markers=markers)
                for e in lat.sequence:
                    expected=TransferMap if isinstance(e,Solenoid) else SecondTM
                    self.assertTrue(all(type(tm) is expected for tm in e.tms),e.id)
                self.assertEqual(lat.ued_transport_policy,'drift_second_order_solenoid_linear_v1')

    def test_silent_fallback_is_a_hard_failure(self):
        original=model.MagneticLattice
        def reverting(sequence,**kwargs):
            return original(sequence,method={'global':TransferMap})
        with patch.object(model,'MagneticLattice',side_effect=reverting):
            with self.assertRaisesRegex(RuntimeError,'tracking method mismatch.*drift1'):
                model.build_lattice_from_shared(load_config(),model.STEP_ACTIVE[4])

    def test_native_drift_matches_independent_quadratic_expansion(self):
        gamma=E/m_e_GeV; beta=np.sqrt(1-1/gamma**2)
        X=np.zeros((6,4))
        X[1]=[.007,-.003,.002,.008];X[3]=[.003,.007,-.004,.001]
        X[5]=[.01,-.008,.005,-.006]
        a,b,q=X[1],X[3],X[5]
        expected=X.copy()
        expected[0]+=L*a*(1-q/beta)
        expected[2]+=L*b*(1-q/beta)
        expected[4]+=L*(-q/(beta**2*gamma**2)+(a*a+b*b)/(2*beta)
                        +3*q*q/(2*beta**3*gamma**2))
        actual=X.copy();Drift(l=L,tm=SecondTM).apply(actual,E)
        np.testing.assert_allclose(actual,expected,rtol=3e-14,atol=3e-18)

    def test_drift_error_has_expected_truncation_order(self):
        errors={TransferMap:[],SecondTM:[]}
        for scale in [.01,.005,.0025]:
            X=np.zeros((6,4));X[1]=scale*np.array([.7,-.3,.2,.8])
            X[3]=scale*np.array([.3,.7,-.4,.1]);X[5]=scale*np.array([1.,-.8,.5,-.6])
            for tm in errors:
                actual=X.copy();Drift(l=L,tm=tm).apply(actual,E)
                errors[tm].append(float(np.max(np.abs(actual[[0,2,4]]-exact_drift(X)[[0,2,4]]))))
        for tm,order in [(TransferMap,2),(SecondTM,3)]:
            ratios=np.array(errors[tm][:-1])/errors[tm][1:]
            np.testing.assert_allclose(ratios,2**order,rtol=.04)
        print('Drift max position/time-coordinate errors [m]:',
              {tm.__name__:v for tm,v in errors.items()})

    def test_solenoid_linear_map_from_independent_hamiltonian(self):
        # H=((px+k*y)^2+(py-k*x)^2)/2 in the paraxial, on-momentum
        # hard-edge model.  Its generator includes entrance/exit convention;
        # an unfringed uniform-B RK trajectory would be a different model.
        k=22.37494840236591;length=.06
        A=np.array([[0,1,k,0],[-k*k,0,0,k],[-k,0,0,1],[0,-k,-k*k,0]])
        independent=expm(length*A)
        native=Solenoid(l=length,k=k,tm=TransferMap).R(E)[0][:4,:4]
        np.testing.assert_allclose(native,independent,rtol=5e-13,atol=8e-14)

    def test_installed_solenoid_second_order_has_documented_gap(self):
        beta=np.sqrt(1-(m_e_GeV/E)**2)
        k=22.37494840236591;length=.06
        so=Solenoid(l=length,k=k,tm=SecondTM)
        np.testing.assert_array_equal(so.T(E)[0],Drift(l=length,tm=SecondTM).T(E)[0])
        tensor=so.T(E)[0]
        native_xq=float(tensor[0,0,5]+tensor[0,5,0])
        required=k*length*np.sin(2*k*length)/beta
        self.assertEqual(native_xq,0.)
        self.assertGreater(abs(required),1.)
        # This test locks the known library limit. A library update supplying
        # a genuine solenoid map calls for renewed qualification, not removal
        # of the explicit linear policy without evidence.

    def test_short_formal_cli_adapter_and_saved_methods(self):
        cfg=short_config()
        formal=quiet(model.run_from_config,cfg)
        adapter=quiet(run_ocelot,cfg,'full')
        with tempfile.TemporaryDirectory(prefix='ued_transport_') as d:
            path=quiet(model.main,out_dir=d,cfg_override=cfg,step=4)
            saved=json.loads(Path(path).read_text())
        for key,values in formal['history'].items():
            np.testing.assert_array_equal(values,saved['history'][key],err_msg=key)
            if hasattr(adapter,key):
                np.testing.assert_array_equal(values,getattr(adapter,key),err_msg=key)
        for meta in [formal['meta'],adapter.meta,saved['meta']]:
            self.assertEqual(meta['transport_policy'],'drift_second_order_solenoid_linear_v1')
            self.assertEqual(meta['ocelot_version'],'26.06.1')
            self.assertTrue(meta['transport_limits'])
            for e in meta['lattice_sequence']:
                self.assertEqual(e['tracking_methods'],['TransferMap' if e['type']=='Solenoid' else 'SecondTM'])
        self.assertAlmostEqual(formal['rf_events'][0]['z_actual_m'],.018,places=13)
        self.assertAlmostEqual(formal['history']['z_mm'][-1],53.,places=10)

    def test_short_sc_preserves_map_metadata_and_runtime_contract(self):
        cfg=short_config(sc=True)
        formal=quiet(model.run_from_config,cfg)
        adapter=quiet(run_ocelot,cfg,'full')
        for key,values in formal['history'].items():
            if hasattr(adapter,key):
                np.testing.assert_array_equal(values,getattr(adapter,key),err_msg=key)
        m=formal['meta']
        self.assertTrue(m['sc_effective']);self.assertGreater(m['sc_apply_count'],0)
        self.assertAlmostEqual(m['sc_coverage_stop_m'],.053,places=13)
        self.assertAlmostEqual(m['rf_events'][0]['z_actual_m'],.018,places=13)
        self.assertEqual(m['transport_policy'],'drift_second_order_solenoid_linear_v1')

    def test_low_level_lattice_reports_its_actual_methods(self):
        cfg=short_config()
        cfg['physics_switches'].update(rf_longitudinal_kick=False,rf_transverse_kick=False)
        lat=MagneticLattice([Drift(l=.053)],method={'global':TransferMap})
        result=quiet(model.run_beamline,lat,[],cfg_override=cfg)
        self.assertEqual(result['meta']['transport_policy'],'caller_supplied')
        self.assertEqual(result['meta']['lattice_sequence'][0]['tracking_methods'],['TransferMap'])
        self.assertEqual(result['meta']['transport_limits'],[])


def main():
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(OcelotTransportTest)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':
    sys.exit(main())
