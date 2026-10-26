#!/usr/bin/env python3
"""Benchmark 4 (v0.15): 0.5 m drift @500 fC, 100 keV — longitudinal SC
mechanism comparison.

Task E hardening: every model call specifies sc_model EXPLICITLY and the
printed label / metadata / actual model are cross-checked, so a label can
never silently disagree with the model that ran.  All three runs use the same
initial conditions, physical charge, propagation length and diagnostics.

  AG ellipsoid : run_ag(..., sc_model="ellipsoid")
  AG gaussian  : run_ag(..., sc_model="gaussian")
  OCELOT native: run_ocelot (particle tracking + PIC)

This script only fixes reproducibility/identification — it does NOT tune any
formula to make results agree, and no single comparison is used to declare a
model "correct".
"""
import sys, copy, os
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "AG"))
import numpy as np
from shared.params import load_config
from validation.backend import run_ag, run_ocelot

cfg = load_config()
c = copy.deepcopy(cfg)
c["lattice"]["elements"] = [
    {"name": "drift1", "type": "drift", "z_start": 0.0, "length": 0.5, "parameters": {}},
    {"name": "sample", "type": "sample", "z_start": 0.5, "length": 0.0, "parameters": {}}]
c["beam"]["charge_fC"] = 500.0
zq = 500.0

# ── explicit sc_model on every model call ──
ag_e = run_ag(c, "full", sc_enabled=True, solenoid_coupling=False,
              sc_model="ellipsoid")
ag_g = run_ag(c, "full", sc_enabled=True, solenoid_coupling=False,
              sc_model="gaussian")
r_oc = run_ocelot(c, "full", sc_enabled=True, n_particles=50000,
                  sc_mesh=[63, 63, 63])

# ── label / metadata / actual-model consistency ──
label_ok = (ag_e.meta.get("sc_model") == "ellipsoid"
            and ag_g.meta.get("sc_model") == "gaussian")
print("=" * 64)
print("Benchmark 4: 0.5m drift @500fC, 100 keV — longitudinal SC mechanism")
print("=" * 64)
print(f"  model-label check: AG-ellipsoid meta.sc_model="
      f"{ag_e.meta.get('sc_model')!r}, AG-gaussian meta.sc_model="
      f"{ag_g.meta.get('sc_model')!r}  "
      f"{'PASS' if label_ok else 'FAIL'}")


def s(r, k):
    return float(np.interp(zq, r.z_mm, getattr(r, k)))


print(f"{'':22s}{'σz[µm]':>10s}{'σδ[e-3]':>11s}{'sc_model':>12s}")
print(f"{'AG ellipsoid':>22s}{s(ag_e,'sigma_z_um'):>10.1f}"
      f"{s(ag_e,'sigma_delta_e3'):>11.4f}{str(ag_e.meta.get('sc_model')):>12s}")
print(f"{'AG gaussian':>22s}{s(ag_g,'sigma_z_um'):>10.1f}"
      f"{s(ag_g,'sigma_delta_e3'):>11.4f}{str(ag_g.meta.get('sc_model')):>12s}")
print(f"{'OCELOT native (PIC)':>22s}{s(r_oc,'sigma_z_um'):>10.1f}"
      f"{s(r_oc,'sigma_delta_e3'):>11.4f}{'particles':>12s}")
print()
print("关键判据 (AG drift 中 σδ 是否增长? 初始 0.1000e-3):")
print(f"  AG ellipsoid σδ: {s(ag_e,'sigma_delta_e3'):.4f}  |  "
      f"AG gaussian σδ: {s(ag_g,'sigma_delta_e3'):.4f}")
print(f"  OCELOT σδ: {s(r_oc,'sigma_delta_e3'):.4f}")
sys.exit(0 if label_ok else 1)
