"""Independent expanded paper Gx/Gy and evolving transverse state acceptance."""
import copy,sys,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'AG')]
import beam_dynamics_6d as bd
from AG.longitudinal_state import inspect_longitudinal_state
from AG.beamline_sim import compute_emittance


def initial():
 b=bd.make_beam_100keV(Ne=100e-15/bd.E_CHARGE,sigma_delta=1e-4,eps_nx_um=.08,eps_ny_um=.08)
 b.eps_nz=inspect_longitudinal_state(b)['epsilon_from_covariance_mm_mrad']*1e-6
 return b


def paper_theta_Gx(b):
 """Unreduced Eq.(18); independently grouped using extended precision."""
 t=np.longdouble
 sx,sy,sz,nx,ny,nz,tx,ty,tz,g,p,be=map(t,[b.sigma_x,b.sigma_y,b.sigma_z,b.nu_x,b.nu_y,b.nu_z,b.theta_x,b.theta_y,b.theta_z,b.gamma,b.p0,b.beta])
 a={k:t(v) for k,v in bd.alpha_at(float(sx/(g*sz)),float(sy/(g*sz))).items()}
 fb=(t(bd.E_CHARGE)/(t(bd.M_E)*t(bd.C_LIGHT)**2))*t(b.Ne)*t(bd.E_CHARGE)/(8*t(np.pi)*np.sqrt(t(np.pi))*t(bd.EPSILON_0))
 bracket=3*(3*tx*tx*a['x']-nx*nx*a['xx'])/(sx*sz)
 bracket+=(8*ty*ty*a['x']-ny*ny*a['xy'])/(8*sx*sz)
 bracket+=(1-p*p)*(2*tz*tz*a['x']-nz*nz*a['xz'])/(2*sx*sz)
 return (fb*nx*a['x']/(be*be*g**3*sx*sz)-fb*nx*bracket/(2*g)
     -fb*ny*(8*tx*tx*a['y']-nx*nx*a['xy'])/(8*g*sy*sz)
     -fb*nz*(1-p*p)*(2*g*g*sz*sz*tx*tx*a['z']-nx*nx*sx*sy*a['xz'])/(2*g*sx*sy*g*g*sz*sz))


def swap(b):
 b=b.copy();b.sigma_x,b.sigma_y=b.sigma_y,b.sigma_x;b.nu_x,b.nu_y=b.nu_y,b.nu_x;b.eps_nx,b.eps_ny=b.eps_ny,b.eps_nx
 return b

class TransverseGTests(unittest.TestCase):
 def test_rejected_trial_stage_preserves_analytic_solution(self):
  # y'=-10y has a positive exponential solution. A deliberately large
  # initial trial can cross zero, while the exact solution remains valid.
  def rhs(s,y):
   if y[0]<=0:raise bd._TrialStateOutsideDomain('trial outside positive domain')
   return -10*y
  solver=bd._DomainCheckedRK45(rhs,0.,np.array([1.]),.49,first_step=.49,rtol=1e-8,atol=1e-10)
  while solver.status=='running':solver.step()
  self.assertEqual(solver.status,'finished')
  self.assertGreater(solver.domain_rejections,0)
  np.testing.assert_allclose(solver.y,np.exp(-4.9),rtol=2e-6)
 def test_paper_expansion(self):
  for energy in (100_000.,5_000_000.):
   for sign in (-1,1):
    b=initial();b.gamma=bd.beamK_to_gamma(energy)
    b.sigma_y*=1.7;b.nu_x=sign*.002;b.nu_y=-sign*.001;b.nu_z=sign*.00002
    b.C_zd=b.gamma**2*b.sigma_z*b.nu_z
    b.sigma_delta=b.gamma**2*np.sqrt(b.nu_z**2+(b.eps_nz/(b.p0*b.gamma**2*b.sigma_z))**2)
    fx,fy,_=bd.space_charge_forces(b,model='gaussian');rates=bd.space_charge_area_log_rates(b)
    for axis,f,n,th,ref in [(0,fx,b.nu_x,b.theta_x,paper_theta_Gx(b)),(1,fy,b.nu_y,b.theta_y,paper_theta_Gx(swap(b)))]:
     actual=n*f+.5*rates[axis]*(th*th-n*n)
     np.testing.assert_allclose(actual,ref,rtol=3e-12,atol=1e-26)
 def test_drift_no_sc_preserves_area(self):
  b=initial();b.Ne=0;b.nu_x=-.0004
  s,st=bd.propagate(b,(0,.1),n_points=40)
  analytic=np.sqrt((b.sigma_x+s*b.nu_x)**2+(s*b.eps_nx/(b.p0*b.sigma_x))**2)
  np.testing.assert_allclose(st[:,0],analytic,rtol=2e-7)
  np.testing.assert_allclose(st[:,12],b.eps_nx,rtol=2e-14)
 def test_real_sc_state_reconstruction_and_split(self):
  b=initial();s,st=bd.propagate(b,(0,.05),n_points=51)
  self.assertEqual(st.shape,(51,14));self.assertNotEqual(st[-1,12],st[0,12])
  end=bd.Beam6D.from_state(st[-1],st[-1,11],b.Ne,b.eps_nx,b.eps_ny,b.eps_nz)
  self.assertEqual(end.eps_nx,st[-1,12])
  s1,t1=bd.propagate(b,(0,.025),n_points=21)
  mid=bd.Beam6D.from_state(t1[-1],t1[-1,11],b.Ne,b.eps_nx,b.eps_ny,b.eps_nz)
  s2,t2=bd.propagate(mid,(.025,.05),n_points=21)
  np.testing.assert_allclose(t2[-1,[0,1,2,4,5,12,13]],st[-1,[0,1,2,4,5,12,13]],rtol=2e-7,atol=1e-20)
  em=compute_emittance(st,b.eps_nx,b.eps_ny,b.eps_nz)
  np.testing.assert_allclose(em['eps_n_x'],st[:,12],rtol=1e-14)
  np.testing.assert_allclose(st[:,12],st[:,13],rtol=1e-14)
 def test_linear_external_and_ellipsoid(self):
  for model in ('gaussian','ellipsoid'):
   b=initial()
   if model=='gaussian':b.Ne=0
   external=lambda s,b:(-300*b.sigma_x,-300*b.sigma_y,0.,0.,0.,0.)
   _,st=bd.propagate(b,(0.,.05),n_points=20,external_force_func=external,sc_model=model)
   np.testing.assert_allclose(st[:,12],b.eps_nx,rtol=2e-14)
 def test_zero_area(self):
  b=initial();b.eps_nx=b.eps_ny=0
  _,st=bd.propagate(b,(0,.01),n_points=10)
  self.assertTrue(np.all(st[:,12:14]==0))
 def test_legacy_no_sc_flag_matches_explicit_no_sc(self):
  from AG.beamline_sim import BeamlineSim
  b=initial();sim=BeamlineSim(b,[],.02)
  _,flag=sim.run(n_points=20,sc_on=False);_,explicit=sim.run_no_sc(n_points=20)
  np.testing.assert_array_equal(flag,explicit);self.assertEqual(sim.beam0.Ne,b.Ne)


def main():
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(TransverseGTests));return 0 if r.wasSuccessful() else 1
if __name__=='__main__':sys.exit(main())
