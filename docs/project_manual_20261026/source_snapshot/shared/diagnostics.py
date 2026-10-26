"""Centered beam moments in the project's fixed-reference first-order coordinates.

No forces or tracking: zeta=-beta*tau [m], delta=p_oc/beta [1].
See beam_result_physics_note.md. Covariances use population (not N-1) weights.
"""
import numpy as np
from shared.constants import C_SI


def pair_moments(u, v, weights=None):
    u, v = np.asarray(u, float), np.asarray(v, float)
    if u.shape != v.shape or u.ndim != 1 or not u.size or not np.isfinite([u, v]).all():
        raise ValueError("moment coordinates must be nonempty finite equal-length vectors")
    w = np.ones(u.size) if weights is None else np.abs(np.asarray(weights, float))
    if w.shape != u.shape or not np.isfinite(w).all() or np.sum(w) <= 0:
        raise ValueError("moment weights must be finite, matching, and have positive total")
    w = w / np.sum(w)
    du, dv = u - np.sum(w*u), v - np.sum(w*v)
    return np.sum(w*du*du), np.sum(w*dv*dv), np.sum(w*du*dv)


def covariance_area(a, b, c):
    a, b, c = np.broadcast_arrays(np.asarray(a,float),np.asarray(b,float),np.asarray(c,float))
    product, det = a*b, a*b-c*c
    if (not np.isfinite([a,b,c]).all() or np.any(a < 0) or np.any(b < 0)
            or np.any(det < -64*np.finfo(float).eps*np.maximum(product,c*c))):
        raise ValueError("beam covariance is nonfinite or not positive semidefinite")
    return np.sqrt(np.maximum(det,0.))  # only the checked 64-epsilon PSD boundary


def longitudinal_diagnostics(sigma_z_m, sigma_delta, C_zdelta_m, gamma):
    s, d, c, g = np.broadcast_arrays(*[np.asarray(v,float) for v in
        (sigma_z_m,sigma_delta,C_zdelta_m,gamma)])
    if not np.isfinite([s,d,c,g]).all() or np.any(d < 0) or np.any(s <= 0) or np.any(g <= 1):
        raise ValueError("diagnostics require positive size and gamma>1")
    beta = np.sqrt(1.-1./g**2)
    area = covariance_area(s*s,d*d,c)
    return {"C_zdelta_m":c, "chirp_per_m":c/(s*s),
            "eps_nz_mm_mrad":beta*g*area*1e6,
            "eps_z_zprime_m":area/g**2,
            "sigma_t_fs":s/(beta*C_SI)*1e15,
            "beta_ref":beta, "gamma_ref":g}


def particle_diagnostics(p, ref):
    beta, gamma = ref['beta'], ref['gamma']
    weights = np.abs(p.q_array)
    if not np.any(weights):
        weights = None  # zero-charge beam still has a well-defined distribution
    ax,bx,cx=pair_moments(p.x(),p.px(),weights)
    ay,by,cy=pair_moments(p.y(),p.py(),weights)
    az,bz,cz=pair_moments(-beta*p.tau(),p.p()/beta,weights)
    diag=longitudinal_diagnostics(np.sqrt(az),np.sqrt(bz),cz,gamma)
    diag.update(sigma_x_um=np.sqrt(ax)*1e6,sigma_y_um=np.sqrt(ay)*1e6,
                sigma_z_um=np.sqrt(az)*1e6,sigma_delta_e3=np.sqrt(bz)*1e3,
                eps_nx_mm_mrad=beta*gamma*covariance_area(ax,bx,cx)*1e6,
                eps_ny_mm_mrad=beta*gamma*covariance_area(ay,by,cy)*1e6,
                energy_keV=ref['E_keV'])
    return {k:float(v) for k,v in diag.items()}
