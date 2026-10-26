"""Production alpha accuracy, failure policy, and formal-driver use."""
import sys,json,unittest,copy,contextlib,io,tempfile
from pathlib import Path
import numpy as np
from scipy.special import elliprd
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'AG')]
import beam_dynamics_6d as bd
from AG import alpha_coefficients as ac
from validation.alpha_reference import adaptive_alpha_reference

class AlphaNumericsTests(unittest.TestCase):
    def test_sphere_all_nine(self):
        expected=[1/3,1/3,1/3,.3,.3,.6,.8,.2,.2]
        np.testing.assert_allclose(list(bd.alpha_at(1,1).values()),expected,rtol=2e-14)
        self.assertLess(ac.TAIL_RELATIVE_BOUND,2.7e-15)

    def test_scalar_reference_non_nodes_and_outside_old_table(self):
        for x,y in [(.0127,.619),(.1,3.7),(39.810717,.01),(.37,2.41),(100,100),(376.721164,376.721164),(3000,.003)]:
            ref,error=adaptive_alpha_reference(x,y)
            self.assertLess(error,1e-9)
            np.testing.assert_allclose(list(bd.alpha_at(x,y).values()),ref,rtol=1e-9,atol=0)

    def test_high_precision_anchors(self):
        data=json.loads((ROOT/'validation/reference_data/ag_alpha_mp55_20261022.json').read_text())
        for r in data['anchors']:
            np.testing.assert_allclose(list(bd.alpha_at(r['kx'],r['ky']).values()),r['values'],rtol=1e-9,atol=0)

    def test_rd_identity_and_exchange_across_domain(self):
        for x in np.logspace(-6,6,7):
            for y in np.logspace(-6,6,7):
                a=bd.alpha_at(x,y);b=bd.alpha_at(y,x)
                ref=[x*x/3*elliprd(y*y,1.,x*x),y*y/3*elliprd(x*x,1.,y*y),x*y/3*elliprd(x*x,y*y,1.)]
                np.testing.assert_allclose([a['x'],a['y'],a['z']],ref,rtol=1e-9)
                for left,right in [('x','y'),('xx','yy'),('xz','yz'),('z','z'),('xy','xy'),('zz','zz')]:
                    self.assertAlmostEqual(a[left]/b[right],1.,delta=1e-10)
                self.assertAlmostEqual(y/x*a['x']+x/y*a['y']+a['z'],1.,delta=1e-10)

    def test_invalid_domain_and_cache_copy(self):
        for x,y in [(0,1),(-1,1),(np.nan,1),(1,np.inf),(1e-7,1),(1,1e7)]:
            with self.assertRaisesRegex(ValueError,'no clipping'):bd.alpha_at(x,y)
        a=bd.alpha_at(1,1);a['x']=-2
        self.assertGreater(bd.alpha_at(1,1)['x'],0)
        beam=bd.make_beam_100keV();beam.sigma_x=beam.gamma*beam.sigma_z*1e7
        with self.assertRaisesRegex(ValueError,'no clipping'):bd.space_charge_forces(beam)
        beam.Ne=0
        self.assertEqual(bd.space_charge_forces(beam),(0.,0.,0.))

    def test_actual_stage_range_collected_not_only_output_samples(self):
        from shared.params import load_config
        from validation.backend import run_ag
        from AG import run_shared
        from validation.test_runner_contract import short_config
        c=short_config(load_config());c['space_charge']['enabled']=True
        with tempfile.TemporaryDirectory() as out,contextlib.redirect_stdout(io.StringIO()):
            r=run_ag(c,'full');path=run_shared.main(out_dir=out,cfg_override=c)
            saved=json.loads(Path(path).read_text())
        ev=r.meta['sc_alpha_evaluation'];self.assertGreater(ev['calls'],0)
        self.assertEqual(ev['clipped_calls'],0);self.assertLessEqual(ev['max_relative_refinement_observed'],ac.RELATIVE_CHECK)
        self.assertFalse(r.meta['sc_alpha_table_domain']['gaussian_sc_uses_clipped_coefficients'])
        for k,v in r.history().items():np.testing.assert_array_equal(v,saved['history'][k])
        c['space_charge']['enabled']=False
        off=run_ag(c,'full');self.assertEqual(off.meta['sc_alpha_evaluation']['calls'],0)


def main():
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AlphaNumericsTests))
    return 0 if r.wasSuccessful() else 1
if __name__=='__main__':sys.exit(main())
