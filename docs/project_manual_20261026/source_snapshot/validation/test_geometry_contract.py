"""Geometry failures and a changed-RF integration case; no default output writes."""
import contextlib,copy,io,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from shared.geometry import validate_geometry
from shared.params import load_config


def adjusted_config():
    c=load_config();p=next(e for e in c['lattice']['elements'] if e['type']=='rf_cavity')['parameters']
    c['lattice']['elements']=[
        dict(name='cathode',type='cathode',z_start=0.,length=0.),
        dict(name='d1',type='drift',z_start=0.,length=.025),
        dict(name='rf1',type='rf_cavity',z_start=.025,length=.030,parameters=p),
        dict(name='d2',type='drift',z_start=.055,length=.012),
        dict(name='sample',type='sample',z_start=.067,length=0.)]
    c['output'].update(z_diagnostics_mm=[0,25,55,67],step_size_m=.001)
    c['beam']['n_particles']=300;c['space_charge']['enabled']=False
    return c


class GeometryTests(unittest.TestCase):
    def test_default_and_no_mutation(self):
        c=load_config();before=copy.deepcopy(c);g=validate_geometry(c)
        self.assertAlmostEqual(g['sample_m'],.777);self.assertEqual(c,before)

    def test_invalid_geometries(self):
        cases=[(2,'length',.04,'overlap'),(2,'z_start',.03,'gap'),
               (2,'z_start',.02,'overlap'),(2,'length',-1.,'nonnegative'),
               (2,'z_start',float('nan'),'finite'),(2,'length',0.,'positive'),
               (4,'z_start',.068,'gap'),(4,'length',.001,'zero length'),
               (2,'name','d1','duplicate')]
        for i,k,v,reason in cases:
            with self.subTest(k=k,v=v):
                c=adjusted_config();c['lattice']['elements'][i][k]=v
                with self.assertRaisesRegex(ValueError,reason):validate_geometry(c)

    def test_order_sample_and_probes(self):
        c=adjusted_config();c['lattice']['elements'].reverse()
        with self.assertRaisesRegex(ValueError,'gap'):validate_geometry(c)
        c=adjusted_config();c['lattice']['elements'].pop()
        with self.assertRaisesRegex(ValueError,'terminal'):validate_geometry(c)
        c=adjusted_config();c['output']['z_diagnostics_mm']=[68]
        with self.assertRaisesRegex(ValueError,'outside'):validate_geometry(c)

    def test_invalid_numeric_and_probe_inputs(self):
        for value in (True,'0.025',float('inf')):
            c=adjusted_config();c['lattice']['elements'][2]['z_start']=value
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'finite number'):
                validate_geometry(c)
        for output,reason in ((None,'mapping'),({'z_diagnostics_mm':67},'list'),
                              ({'z_diagnostics_mm':[float('nan')]},'finite number')):
            c=adjusted_config();c['output']=output
            with self.subTest(output=output),self.assertRaisesRegex(ValueError,reason):
                validate_geometry(c)

    def test_roundoff_tolerance_is_not_a_physical_gap(self):
        c=adjusted_config()
        c['lattice']['elements'][3]['z_start']+=1e-16
        before=copy.deepcopy(c)
        validate_geometry(c)
        self.assertEqual(c,before)
        c['lattice']['elements'][3]['z_start']+=1e-10
        with self.assertRaisesRegex(ValueError,'gap'):validate_geometry(c)

    def test_stage_builders_preserve_changed_magnet_and_RF_geometry(self):
        from GPT模拟 import ued_beamline_v2 as gpt
        c=adjusted_config()
        c['lattice']['elements'][1:2]=[
            dict(name='d0',type='drift',z_start=0.,length=.01),
            dict(name='sol1',type='solenoid',z_start=.01,length=.005,
                 parameters={'B_field_T':.02}),
            dict(name='d1',type='drift',z_start=.015,length=.01)]
        for step,active in gpt.STEP_ACTIVE.items():
            lat,rfs=gpt.build_lattice_from_shared(c,active)
            nonzero=[e for e in c['lattice']['elements'] if e['length']>0]
            self.assertEqual(len(lat.sequence),len(nonzero))
            cursor=0.
            for built,expected in zip(lat.sequence,nonzero):
                self.assertAlmostEqual(cursor,expected['z_start'],places=13)
                self.assertEqual(built.l,expected['length'])
                self.assertEqual(type(built).__name__,
                    'Solenoid' if expected['type']=='solenoid' and step>=2 else 'Drift')
                cursor+=built.l
            self.assertAlmostEqual(cursor,.067,places=13)
            self.assertEqual([e['z_start'] for e in rfs],[.025] if step>=3 else [])

    def test_formal_routes_reject_before_execution(self):
        from unittest.mock import patch
        from AG import runner,run_shared
        from GPT模拟 import ued_beamline_v2 as gpt
        c=adjusted_config();c['lattice']['elements'][2]['z_start']=.026
        with patch.object(gpt,'generate_parray',side_effect=AssertionError('must not generate')):
            for call in (lambda:runner.run_from_config(c),lambda:run_shared.main(cfg_override=c),
                         lambda:gpt.run_from_config(c),lambda:gpt.main(cfg_override=c,step=3),
                         lambda:gpt.build_lattice_from_shared(c,{'rf_cavity'})):
                with self.assertRaisesRegex(ValueError,'rf1: gap'):call()

    def test_adjusted_RF_real_routes_and_saved_outputs(self):
        from validation.backend import run_ag,run_ocelot
        from AG import run_shared
        from GPT模拟 import ued_beamline_v2 as gpt
        for sc in (False,True):
            with self.subTest(sc=sc):
                c=adjusted_config();c['space_charge'].update(enabled=sc,mesh=[33,33,33])
                with tempfile.TemporaryDirectory(prefix='ued_geometry_') as tmp,contextlib.redirect_stdout(io.StringIO()):
                    a=run_ag(c,'full',n_points=80);o=run_ocelot(c,'full')
                    ap=run_shared.main(out_dir=tmp,cfg_override=c)
                    gpt.main(out_dir=tmp,cfg_override=c,step=4)
                    saved=[json.loads(Path(ap).read_text()),json.loads((Path(tmp)/'GPT_results.json').read_text())]
                metas=[(a.meta,a.z_mm[-1]),(o.meta,o.z_mm[-1])]
                metas.extend((r['meta'],r['history']['z_mm'][-1]) for r in saved)
                for meta,last in metas:
                    self.assertAlmostEqual(last,67.,places=9)
                    self.assertAlmostEqual(meta['geometry']['sample_m'],.067,places=12)
                    self.assertEqual(meta['sc_effective'],sc)
                    self.assertEqual(len(meta['rf_events']),1)
                    self.assertAlmostEqual(meta['rf_events'][0]['z_actual_m'],.025,places=12)
                if sc:
                    for meta in (o.meta,saved[1]['meta']):
                        self.assertGreater(meta['sc_apply_count'],0)
                        self.assertAlmostEqual(meta['sc_coverage_stop_m'],.067,places=12)
                self.assertTrue(all(meta['geometry']==a.meta['geometry'] for meta,_ in metas))


def main():
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(GeometryTests))
    return 0 if r.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
