"""
Unified result container shared by production drivers and validation tests.

Both backends (AG, OCELOT) are reduced to this identical structure so the
framework can compare them field-by-field and plot AG vs OCELOT overlays.

Fields (each route owns its sampling grid; compare only within coverage):
  z_mm             [mm]
  sigma_x_um       [μm]  projected RMS
  sigma_y_um       [μm]
  sigma_z_um       [μm]  longitudinal RMS (physical zeta = -beta*c*Delta_t)
  eps_nx_mm_mrad   [mm·mrad]  normalized transverse emittance (x)
  eps_ny_mm_mrad   [mm·mrad]  normalized transverse emittance (y)
  energy_keV       [keV]  reference-particle kinetic energy
  sigma_delta_e3   [×10⁻³]
  chirp_m          [m⁻¹]  legacy alias of momentum chirp C(zeta,delta_p)/sigma_zeta^2
  time_res_fs      [fs]   RMS time spread σ_t = σ_z / (βc)
"""

import os
import json

import numpy as np

C_SI = 2.99792458e8


class BeamResult:
    def __init__(self, route, z_mm, sigma_x_um, sigma_y_um, sigma_z_um,
                 eps_nx_mm_mrad, eps_ny_mm_mrad,
                 energy_keV, sigma_delta_e3, chirp_m=None,
                 time_res_fs=None, meta=None, C_zdelta_m=None,
                 chirp_per_m=None, eps_nz_mm_mrad=None, eps_z_zprime_m=None,
                 sigma_t_fs=None, beta_ref=None, gamma_ref=None):
        self.route = route
        self.z_mm = np.asarray(z_mm, dtype=float)
        self.sigma_x_um = np.asarray(sigma_x_um, dtype=float)
        self.sigma_y_um = np.asarray(sigma_y_um, dtype=float)
        self.sigma_z_um = np.asarray(sigma_z_um, dtype=float)
        self.eps_nx_mm_mrad = np.asarray(eps_nx_mm_mrad, dtype=float)
        self.eps_ny_mm_mrad = np.asarray(eps_ny_mm_mrad, dtype=float)
        self.energy_keV = np.asarray(energy_keV, dtype=float)
        self.sigma_delta_e3 = np.asarray(sigma_delta_e3, dtype=float)
        self.chirp_m = chirp_m  # legacy alias; formal history uses chirp_per_m
        self.time_res_fs = (time_res_fs if time_res_fs is not None
                            else self._time_from_sigma_z())
        self.meta = meta or {}
        from shared.beam_physics import BeamReference
        self.gamma_ref = (np.asarray(gamma_ref,float) if gamma_ref is not None else
                          np.asarray([BeamReference.from_energy_keV(e).gamma for e in self.energy_keV]))
        self.beta_ref = (np.asarray(beta_ref,float) if beta_ref is not None else self._beta())
        self.sigma_t_fs = np.asarray(sigma_t_fs if sigma_t_fs is not None else self.time_res_fs)
        if C_zdelta_m is not None:
            from shared.diagnostics import longitudinal_diagnostics
            diag = longitudinal_diagnostics(self.sigma_z_um*1e-6,
                     self.sigma_delta_e3*1e-3,C_zdelta_m,self.gamma_ref)
            supplied=dict(chirp_per_m=chirp_per_m,eps_nz_mm_mrad=eps_nz_mm_mrad,
                          eps_z_zprime_m=eps_z_zprime_m,sigma_t_fs=sigma_t_fs,
                          beta_ref=beta_ref,gamma_ref=gamma_ref)
            for key,value in diag.items():
                original=supplied.get(key)
                if original is not None:
                    original=np.asarray(original,float)
                    agrees=np.allclose(original,value,rtol=128*np.finfo(float).eps,atol=0)
                    if key in ('eps_nz_mm_mrad','eps_z_zprime_m'):
                        # At a strongly chirped waist, det(Σ) is a subtraction
                        # of large products. Bound roundoff in the covariance
                        # products, not by a relative tolerance on tiny det.
                        a=(self.sigma_z_um*1e-6)**2
                        b=(self.sigma_delta_e3*1e-3)**2
                        c=np.asarray(C_zdelta_m)
                        area=(original*1e-6/(self.beta_ref*self.gamma_ref) if key=='eps_nz_mm_mrad'
                              else original*self.gamma_ref**2)
                        agrees=(np.all(original>=0) and np.all(np.abs(area**2-(a*b-c*c))<=64*np.finfo(float).eps*(a*b+c*c)))
                    if original.shape!=np.asarray(value).shape or not np.isfinite(original).all() or not agrees:
                        raise ValueError(f'inconsistent saved diagnostic {key}')
                    value=original  # validate, then preserve the driver's exact arrays
                setattr(self,key,np.asarray(value))
            self.chirp_m = self.chirp_per_m
            self.time_res_fs = self.sigma_t_fs

    def _beta(self):
        # single-source relativistic reference (v0.13)
        from shared.beam_physics import BeamReference
        return np.asarray([BeamReference.from_energy_keV(e).beta
                           for e in self.energy_keV])

    def _time_from_sigma_z(self):
        beta = self._beta()
        if np.any(beta < 1e-6):
            return np.full_like(self.sigma_z_um, np.nan)
        return self.sigma_z_um * 1e-6 / (beta * C_SI) * 1e15   # fs

    # ── comparison helpers ────────────────────────────────────────────────
    def at(self, field, z_mm):
        """Interpolate within the tracked range; never silently clamp outside."""
        query = np.asarray(z_mm, dtype=float)
        if (self.z_mm.size == 0 or not np.all(np.isfinite(query))
                or np.any(query < self.z_mm[0] - 1e-9)
                or np.any(query > self.z_mm[-1] + 1e-9)):
            raise ValueError("diagnostic position is outside the tracked range")
        return np.interp(z_mm, self.z_mm, getattr(self, field))

    def history(self):
        """The existing CLI history schema, without recomputing diagnostics."""
        from shared.output_schema import BASE_FIELDS, DIAGNOSTIC_FIELDS
        return {key: np.asarray(getattr(self,key)).tolist() for key in BASE_FIELDS+DIAGNOSTIC_FIELDS
                if hasattr(self,key)}

    @classmethod
    def from_history(cls, route, history, energy_keV, meta=None):
        data = dict(history)
        data.setdefault("energy_keV", np.full(len(history["z_mm"]), energy_keV))
        return cls(route=route, **data, meta=meta)

    def probes_at(self, positions_mm):
        """AG diagnostics: linear interpolation, with sampling method recorded."""
        from shared.output_schema import make_probe
        fields = ("sigma_x_um", "sigma_y_um", "sigma_z_um", "sigma_delta_e3",
                  "eps_nx_mm_mrad", "eps_ny_mm_mrad")
        from shared.diagnostics import longitudinal_diagnostics
        rows=[]
        for z in positions_mm:
            row={k:float(self.at(k,z)) for k in fields}
            row['energy_keV']=float(self.at('energy_keV',z))
            if hasattr(self,'C_zdelta_m'):
                # Interpolate the covariance, then derive chirp/emittance.
                # Interpolating derived values independently breaks constraints.
                a=float(np.interp(z,self.z_mm,(self.sigma_z_um*1e-6)**2))
                b=float(np.interp(z,self.z_mm,(self.sigma_delta_e3*1e-3)**2))
                row.update(sigma_z_um=np.sqrt(a)*1e6,sigma_delta_e3=np.sqrt(b)*1e3)
                row.update({k:float(v) for k,v in longitudinal_diagnostics(np.sqrt(a),np.sqrt(b),
                    self.at('C_zdelta_m',z),self.at('gamma_ref',z)).items()})
            rows.append(make_probe(z_mm=z,**row,z_actual_mm=float(z),
                         z_exact=bool(np.any(np.abs(self.z_mm-z)<1e-9)),
                         sampling="linear_interpolation_of_covariance"))
        return rows

    def metrics_vs(self, other, fields=None):
        """Max-relative deviation vs another BeamResult on the common z range."""
        zlo = max(self.z_mm[0], other.z_mm[0])
        zhi = min(self.z_mm[-1], other.z_mm[-1])
        if zhi <= zlo:
            return {}
        zq = np.linspace(zlo, zhi, 400)
        fields = fields or ["sigma_x_um", "sigma_y_um", "sigma_z_um",
                            "eps_nx_mm_mrad", "sigma_delta_e3"]
        out = {}
        for f in fields:
            a = np.interp(zq, self.z_mm, getattr(self, f))
            b = np.interp(zq, other.z_mm, getattr(other, f))
            scale = np.maximum(np.abs(b), 1e-12)
            out[f] = float(np.max(np.abs(a - b) / scale) * 100.0)
        return out

    def summary(self):
        i = len(self.z_mm) - 1
        return (f"{self.route}: z_end={self.z_mm[-1]:.0f}mm  "
                f"σ_x={self.sigma_x_um[-1]:.1f}  σ_y={self.sigma_y_um[-1]:.1f}  "
                f"σ_z={self.sigma_z_um[-1]:.1f} μm  "
                f"ε_nx={self.eps_nx_mm_mrad[-1]:.4f} mm·mrad  "
                f"σ_δ={self.sigma_delta_e3[-1]:.3f}e-3  "
                f"Δt={self.time_res_fs[-1]:.1f} fs")

    # ── IO ────────────────────────────────────────────────────────────────
    def to_dict(self):
        return dict(self.history(), **{
            "route": self.route,
            "z_mm": self.z_mm.tolist(),
            "sigma_x_um": self.sigma_x_um.tolist(),
            "sigma_y_um": self.sigma_y_um.tolist(),
            "sigma_z_um": self.sigma_z_um.tolist(),
            "eps_nx_mm_mrad": self.eps_nx_mm_mrad.tolist(),
            "eps_ny_mm_mrad": self.eps_ny_mm_mrad.tolist(),
            "energy_keV": self.energy_keV.tolist(),
            "sigma_delta_e3": self.sigma_delta_e3.tolist(),
            "chirp_m": np.asarray(self.chirp_m).tolist() if self.chirp_m is not None else None,
            "time_res_fs": self.time_res_fs.tolist(),
            "meta": self.meta,
        })

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        return path
