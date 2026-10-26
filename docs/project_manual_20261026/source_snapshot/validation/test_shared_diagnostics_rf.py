"""Independent time/field RF references and formal saved diagnostics (no report overwrite)."""
import contextlib,copy,io,json,tempfile,unittest,warnings
from pathlib import Path
import sys
import numpy as np
from scipy.integrate import quad
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from shared.constants import C_SI,M_E_SI,E_SI
from shared.beam_physics import BeamReference
from shared.params import load_config,parse
from shared.diagnostics import pair_moments,longitudinal_diagnostics
from shared.rf_model import coefficients
from validation.test_runner_contract import short_config

class SharedPhysicsTests(unittest.TestCase):
 def test_centered_weighted_moments(self):
  u=np.array([1.,2.,4.]);v=np.array([-3.,2.,5.]);w=np.array([1.,2.,3.])
  cov=np.cov(np.stack([u,v]),aweights=w,ddof=0)
  np.testing.assert_allclose(pair_moments(u+120,v-300,w),[cov[0,0],cov[1,1],cov[0,1]],rtol=1e-13)
  with self.assertRaisesRegex(ValueError,'weights'):pair_moments(u,v,[0,0,0])
 def test_config_derived_emittance_and_legacy_warning(self):
  c=load_config();self.assertNotIn('epsilon_nz_mm_mrad',c['initial_distribution'])
  expected=parse(c).beam.eps_nz
  c['initial_distribution']['epsilon_nz_mm_mrad']=100.
  with warnings.catch_warnings(record=True) as ws:
   warnings.simplefilter('always');p=parse(c)
  self.assertEqual(p.beam.eps_nz,expected);self.assertTrue(any('obsolete' in str(w.message) for w in ws))
 def test_covariance_constraints(self):
  with self.assertRaisesRegex(ValueError,'semidefinite'):longitudinal_diagnostics(1.,1.,2.,2.)
  from shared.beam_result import BeamResult
  kwargs=dict(route='saved',z_mm=[0.],sigma_x_um=[1.],sigma_y_um=[1.],sigma_z_um=[1e6],eps_nx_mm_mrad=[.08],eps_ny_mm_mrad=[.08],energy_keV=[100.],sigma_delta_e3=[1000.],C_zdelta_m=[0.])
  good=BeamResult(**kwargs)
  with self.assertRaisesRegex(ValueError,'inconsistent saved diagnostic'):
   BeamResult(**kwargs,eps_nz_mm_mrad=-good.eps_nz_mm_mrad)
 def test_rf_from_time_energy(self):
  from GPT模拟 import ued_beamline_v2 as oc
  from ocelot.cpbd.beam import generate_parray
  from AG.runner import rf_thin_lens_H
  c=load_config();rf=next(e for e in c['lattice']['elements'] if e['type']=='rf_cavity')
  for energy in (30.,100.,1000.):
   c['beam']['energy_keV']=energy;ref=oc.run_params(c)
   for phi in (0.,.37,np.pi,np.pi/2):
    rf['parameters']['phase_rad']=phi
    for voltage in (0.,30.):
     rf['parameters']['voltage_kV']=voltage
     p=generate_parray(nparticles=7,charge=1e-15,energy=(energy+511)*1e-6)
     p.rparticles[:]=0.;dt=np.linspace(-1e-12,1e-12,7);p.rparticles[4]=C_SI*dt
     oc.apply_rf_kick(p,rf,ref=ref)
     expected=voltage*1e3*(np.sin(phi-2*np.pi*2.856e9*dt)-np.sin(phi))
     np.testing.assert_allclose(p.p()*ref['beta']*ref['E_total_eV'],expected,rtol=2e-12,atol=2e-11)
     self.assertEqual(p.p()[3],0.)
   rf['parameters'].update(voltage_kV=30.,phase_rad=np.pi)
   dt=1e-16;om=2*np.pi*2.856e9;gain=lambda t:30000*np.sin(np.pi-om*t)
   # Differentiate the TIME gain, convert with dE/dp=v and zeta=-v*dt.
   de_dz=(gain(dt)-gain(-dt))/(-2*ref['beta']*C_SI*dt)
   h_ref=de_dz/(ref['beta']**2*ref['E_total_eV'])
   self.assertAlmostEqual(rf_thin_lens_H(c,rf)/h_ref,1.,delta=3e-6) # documented rest-energy convention difference
 def test_transverse_from_lorentz_field_integral(self):
  rf={'frequency_GHz':2.856,'voltage_kV':30.,'phase_rad':np.pi}
  L=.022;omega=2*np.pi*2.856e9
  for energy in (30.,100.,1000.):
   br=BeamReference.from_energy_keV(energy);v=br.velocity
   a=lambda s:np.cos(np.pi*s/L)**2
   da=lambda s:-np.pi/L*np.sin(2*np.pi*s/L)
   integ=quad(lambda s:a(s)*np.cos(omega*s/v),-L/2,L/2,epsabs=1e-14)[0]
   e0=30000/integ
   for phi in (0.,np.pi,.37):
    rf['phase_rad']=phi
    # Integrate q(Er-v Btheta)/v independently; both endpoint fields vanish.
    impulse_over_r=quad(lambda s:E_SI*e0/(2*v)*(da(s)*np.sin(omega*s/v-phi)
             +v/C_SI**2*omega*a(s)*np.cos(omega*s/v-phi)),-L/2,L/2,epsabs=1e-30)[0]
    k_field=impulse_over_r/br.p0
    k_code=coefficients(rf,br.beta,br.gamma,br.gamma*M_E_SI*C_SI**2/E_SI)[1]
    self.assertAlmostEqual(k_code/k_field,1.,delta=2e-12)
 def test_formal_cli_outputs_and_events(self):
  from AG import run_shared
  from GPT模拟 import ued_beamline_v2 as oc
  from validation.backend import run_ag,run_ocelot
  c=short_config(load_config());c['beam']['n_particles']=1500
  with tempfile.TemporaryDirectory() as out,contextlib.redirect_stdout(io.StringIO()):
   for model,cli in ((run_ag,run_shared.main),(run_ocelot,oc.main)):
    r=model(c,'full');path=cli(out_dir=out,cfg_override=c)
    d=json.loads(Path(path).read_text());h=d['history']
    for key in ('C_zdelta_m','chirp_per_m','eps_nz_mm_mrad','sigma_t_fs','energy_keV'):
     np.testing.assert_array_equal(h[key],r.history()[key])
    for p in d['probes']:
     self.assertAlmostEqual(p['chirp_per_m']*(p['sigma_z_um']*1e-6)**2,p['C_zdelta_m'],delta=1e-20)
   for sc in (False,True):
    o=oc.run_from_config(c,dz=.007,sc_enabled=sc)
    ev=o['rf_events'][0];self.assertAlmostEqual(ev['z_actual_m'],.02,places=12)
    self.assertEqual(len(o['rf_events']),1)
    self.assertAlmostEqual(o['history']['z_mm'][0],0.)
 def test_comparison_preserves_fractional_and_actual_planes(self):
  from shared.compare import print_probe_table,_interp_history
  row=lambda z,actual:dict(z_mm=z,z_actual_mm=actual,z_exact=z==actual,sigma_x_um=1.,eps_nx_mm_mrad=.08)
  routes={'AG':{'probes':[row(22.1,22.1),row(22.4,22.4)]},'GPT':{'probes':[row(22.1,25),row(22.4,25)]}}
  out=io.StringIO()
  with contextlib.redirect_stdout(out):print_probe_table(routes)
  self.assertIn('22.1',out.getvalue());self.assertIn('22.4',out.getvalue());self.assertIn('DIFFERENT ACTUAL',out.getvalue())
  with self.assertRaisesRegex(ValueError,'outside'):_interp_history({'z_mm':[0,1],'x':[1,2]},'x',2)


def main():
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SharedPhysicsTests))
 return 0 if result.wasSuccessful() else 1
if __name__=='__main__':sys.exit(main())
