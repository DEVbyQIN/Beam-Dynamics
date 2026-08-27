#!/usr/bin/env python3
"""Benchmark 4 (v0.15): 0.5m drift @500fC, 100 keV — longitudinal SC mechanism.
AG ellipsoid (production default) / AG gaussian / OCELOT: compare σz, σδ, C_zδ."""
import sys, copy, os
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "AG"))
import numpy as np
from shared.params import load_config
from validation.backend import run_ag, run_ocelot
import AG.beam_dynamics_6d as core
from shared.constants import E_SI

cfg = load_config()
c = copy.deepcopy(cfg)
c["lattice"]["elements"] = [
    {"name": "drift1", "type": "drift", "z_start": 0.0, "length": 0.5, "parameters": {}},
    {"name": "sample", "type": "sample", "z_start": 0.5, "length": 0.0, "parameters": {}}]
c["beam"]["charge_fC"] = 500.0
zq = 500.0

ag_e = run_ag(c, "full", sc_enabled=True, solenoid_coupling=False)

gamma0 = core.beamK_to_gamma(100e3)
Ne = abs(500e-15) / E_SI
b0 = core.Beam6D(sigma_x=85e-6, sigma_y=85e-6, sigma_z=300e-6, sigma_xy=0.0,
                 sigma_delta=1e-4, C_zd=0.0, nu_x=0, nu_y=0, nu_z=0,
                 nu_xy=0, nu_delta=0, gamma=gamma0, Ne=Ne,
                 eps_nx=0.08e-6, eps_ny=0.08e-6, eps_nz=0.02e-6)
core.get_alpha_interpolators()
zg, stg = core.propagate(b0, (0.0, 0.5), n_points=51, sc_model='gaussian')

r_oc = run_ocelot(c, "full", sc_enabled=True, n_particles=50000, sc_mesh=[63, 63, 63])

def s(r, k):
    return float(np.interp(zq, r.z_mm, getattr(r, k)))

print("=" * 64)
print("Benchmark 4: 0.5m drift @500fC, 100 keV — 纵向 SC 机制")
print("=" * 64)
print(f"{'':14s}{'σz[µm]':>10s}{'σδ[e-3]':>11s}{'C_zδ[µm]':>12s}")
print(f"{'AG ellipsoid':>14s}{s(ag_e,'sigma_z_um'):>10.1f}{s(ag_e,'sigma_delta_e3'):>11.4f}{'—':>12s}")
print(f"{'AG gaussian':>14s}{stg[-1,2]*1e6:>10.1f}{stg[-1,4]*1e3:>11.4f}{stg[-1,5]*1e6:>12.4f}")
print(f"{'OCELOT native':>14s}{s(r_oc,'sigma_z_um'):>10.1f}{s(r_oc,'sigma_delta_e3'):>11.4f}{'—':>12s}")
print()
print("关键判据 (AG drift 中 σδ 是否增长? 初始 0.1000e-3):")
print(f"  AG ellipsoid σδ: {s(ag_e,'sigma_delta_e3'):.4f}  |  AG gaussian σδ: {stg[-1,4]*1e3:.4f}")
print(f"  OCELOT σδ: {s(r_oc,'sigma_delta_e3'):.4f}")
