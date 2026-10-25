"""Tests of the independent reference, without production tracking runs."""
import math
import sys
from pathlib import Path
import unittest
import numpy as np
import mpmath as mp
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from validation.rf_gaussian_reference import (gaussian_reference, compare_references,
    time_kick_on_cloud, cloud_moments, iid_clt_halfwidth95,tabulated_sampler_reference,
    sampler_interval_reference)


def parameters(sigma=300e-6):
    return dict(sigma_z_m=sigma,sigma_delta=1e-4,covariance_m=0.,beta=.548220432878698,
        gamma=1+100/511,energy_total_eV=611000.,voltage_V=30000.,frequency_Hz=2.856e9,phase_rad=3.1416)


class ReferenceTests(unittest.TestCase):
    def test_quadrature_vs_characteristic_function_with_initial_correlation(self):
        p=parameters(1200e-6);p.update(phase_rad=.37,covariance_m=0.3*p['sigma_z_m']*p['sigma_delta'])
        q=gaussian_reference(**p,method='quadrature',dps=45)
        a=gaussian_reference(**p,method='analytic',dps=65)
        self.assertLess(max(compare_references(q,a).values()),1e-25)

    def test_zero_voltage_and_linear_covariance(self):
        p=parameters();p['voltage_V']=0.
        for method in ('quadrature','analytic','linear'):
            v=gaussian_reference(**p,method=method)['values']
            self.assertAlmostEqual(v['sigma_delta'],p['sigma_delta'],places=15)
            self.assertEqual(v['variance_nonlinear_delta'],0.)
        p=parameters();p['covariance_m']=.2*p['sigma_z_m']*p['sigma_delta']
        v=gaussian_reference(**p,method='linear')['values'];H=v['H_linear_per_m']
        self.assertAlmostEqual(v['C_m'],p['covariance_m']+H*p['sigma_z_m']**2,places=17)
        self.assertAlmostEqual(v['D_m2'],p['sigma_z_m']**2*p['sigma_delta']**2-p['covariance_m']**2,delta=1e-30)

    def test_phase_reversal_and_small_span(self):
        p=parameters(30e-6)
        a=gaussian_reference(**p,method='analytic')['values']
        p['phase_rad']+=math.pi
        b=gaussian_reference(**p,method='analytic')['values']
        self.assertAlmostEqual(a['chirp_per_m'],-b['chirp_per_m'],places=12)
        self.assertAlmostEqual(a['sigma_delta'],b['sigma_delta'],places=14)
        self.assertLess(abs(a['chirp_per_m']/a['H_linear_per_m']-1),1e-5)

    def test_moment_translation_and_residual_identity(self):
        z=np.array([-2.,-.5,.7,2.]);d=np.array([1.,-.3,.8,2.])
        a=cloud_moments(z,d,.7);b=cloud_moments(z+19,d-73,.7)
        for key in ('A_m2','B','C_m','D_m2','eps_nz_mm_mrad','sigma_uncorrelated_delta'):
            self.assertAlmostEqual(a[key],b[key],delta=abs(a[key])*1e-13)
        self.assertAlmostEqual(a['D_m2'],a['A_m2']*a['B']-a['C_m']**2,places=13)

    def test_reference_detects_replaced_linear_particle_kick(self):
        p=parameters(3000e-6);z=np.linspace(-3,3,101)*p['sigma_z_m'];d=np.zeros_like(z)
        actual=time_kick_on_cloud(z,d,**{k:p[k] for k in ('beta','energy_total_eV','voltage_V','frequency_Hz','phase_rad')})
        tangent=gaussian_reference(**p,method='linear')['values']['H_linear_per_m']*z
        self.assertGreater(float(np.max(abs(actual-tangent))),.01)

    def test_single_cloud_uncertainty_is_finite(self):
        rng=np.random.default_rng(104729);z=rng.normal(size=20000)*300e-6;d=-17*z+rng.normal(size=z.size)*1e-4
        u=iid_clt_halfwidth95(z,d,.655)
        self.assertTrue(all(np.isfinite(v) and v>0 for v in u.values()))
        self.assertLess(u['chirp_per_m'],.01)

    def test_sampler_population_reference_and_order(self):
        p=parameters(3000e-6);p.pop('covariance_m')
        a=tabulated_sampler_reference(**p,order=8)['values']
        b=tabulated_sampler_reference(**p,order=16)['values']
        for key in ('sigma_delta','chirp_per_m','eps_nz_mm_mrad','sigma_uncorrelated_delta'):
            self.assertLess(abs(a[key]/b[key]-1),1e-12)
        self.assertGreater(abs(a['input_sigma_z_m']/p['sigma_z_m']-1),1e-6)

    def test_sampler_highprecision_independently_resolves_small_residual(self):
        p=parameters(30e-6);p.pop('covariance_m')
        a=sampler_interval_reference(**p,dps=45)
        b=sampler_interval_reference(**p,dps=65)
        with mp.workdps(85):
            for k in b['high_precision']:
                self.assertLess(abs(mp.mpf(a['high_precision'][k])/mp.mpf(b['high_precision'][k])-1),mp.mpf('1e-20'))
        double=tabulated_sampler_reference(**p)['values']
        self.assertLess(abs(double['variance_nonlinear_delta']/b['values']['variance_nonlinear_delta']-1),1e-6)


def main():
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReferenceTests))
    return int(not result.wasSuccessful())
if __name__=='__main__':raise SystemExit(main())
