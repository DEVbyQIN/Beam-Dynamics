"""Analysis/adaptation contracts; no costly PIC runs and no report overwrite."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from validation import sc_scope_study as study

class ScopeStudyTests(unittest.TestCase):
 def test_fixed_config_and_no_shared_mutation(self):
  c=study.case_config(10,20000,95,.0005,104729)
  self.assertEqual(c['beam']['energy_keV'],100.)
  self.assertEqual(c['space_charge']['mesh'],[95]*3)
  self.assertEqual([r['type'] for r in c['lattice']['elements']],['cathode','drift','sample'])
  self.assertEqual(c['lattice']['elements'][-1]['z_start'],.05)
  self.assertFalse(study.load_config()['space_charge']['enabled'])
 def test_residual_moment_identity(self):
  rng=np.random.default_rng(27);raw=rng.normal(size=(6,5000));raw[4]*=.001;raw[5]=.3*raw[4]+rng.normal(0,1e-4,5000)
  beta=.548;d=study.residual_stats(raw,beta);z=-beta*raw[4];v=raw[5]/beta
  a,b,c=study.pair_moments(z,v)
  np.testing.assert_allclose((d['sigma_uncorrelated_delta_e3']*1e-3)**2,b-c*c/a,rtol=1e-13)
 def test_retained_initial_moments(self):
  cloud=dict(beta_gamma=.655,moments=[[1e-8,2e-6,2e-8],[2e-8,1e-6,-1e-8],[9e-8,1e-8,1e-9]])
  b=study.matched_initial_beam(10,cloud)
  for s,nu,theta,m in [(b.sigma_x,b.nu_x,b.theta_x,cloud['moments'][0]),(b.sigma_y,b.nu_y,b.theta_y,cloud['moments'][1])]:
   np.testing.assert_allclose([s*s,theta*theta,s*nu],m,rtol=1e-13)
  np.testing.assert_allclose([b.sigma_z**2,b.sigma_delta**2,b.C_zd],cloud['moments'][2],rtol=1e-13)
 def test_missing_version_is_not_verified_reuse(self):
  import importlib.metadata
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'old.json').write_text('[]')
   names=('GPT模拟/ued_beamline_v2.py','shared/params.py','shared/constants.py','shared/beam_physics.py','shared/diagnostics.py','shared/beam_result.py','shared/rf_model.py')
   context={'OCELOT':{'meta':{'provenance':{'source_sha256':{n:hashlib.sha256((study.ROOT/n).read_bytes()).hexdigest() for n in names},'dependency_versions':{'missing':'unavailable'}}}}}
   (p/'full_sc_diagnostic.json').write_text(json.dumps(context))
   with patch.object(importlib.metadata,'version',side_effect=importlib.metadata.PackageNotFoundError('missing')):
    _,gate=study.reuse_gate(p/'old.json')
   self.assertFalse(gate['source_and_versions_match']);self.assertEqual(gate['unknown_dependency_versions'],['missing'])
 def test_observer_is_restored_after_tracking_failure(self):
  original=study.diagnostics.particle_diagnostics
  with patch.object(study,'run_ocelot',side_effect=RuntimeError('tracking failed')):
   with self.assertRaisesRegex(RuntimeError,'tracking failed'):study.run_pic(study.case_config(10,50,33,.001,42))
  self.assertIs(study.diagnostics.particle_diagnostics,original)
 def test_signed_error_interval_and_pending_budget(self):
  rows=[]
  for seed in study.SEEDS:
   for q,pic in [(0,100.),(10,110.)]:
    value={k:pic for k in study.FIELDS};ag={k:100. for k in study.FIELDS}
    rows.append(dict(spec=dict(Q_fC=q,N=50000,mesh=63,dz_m=.001,seed=seed),PIC={'endpoint':value},AG={'endpoint':ag},AG_matched_retained_moments=ag))
  summary=study.summarize(rows);q10=next(r for r in summary if r['Q_fC']==10 and r['field']=='sigma_delta_e3')
  self.assertEqual(q10['screening_status'],'pending')
  self.assertAlmostEqual(q10['AG_relative_error_percent']['mean'],-100/11)
  self.assertAlmostEqual(q10['PIC_paired_growth_percent']['mean'],10.)
  base=next(r for r in rows if r['spec']['Q_fC']==10)
  for n,m,d in [(20000,63,.001),(50000,95,.001),(50000,63,.0005)]:
   r=copy.deepcopy(base);r['spec'].update(N=n,mesh=m,dz_m=d);rows.append(r)
  q10=next(r for r in study.summarize(rows) if r['Q_fC']==10 and r['field']=='sigma_delta_e3')
  self.assertEqual(q10['screening_status'],'not_supported')

def main():
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ScopeStudyTests));return 0 if r.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
