#!/usr/bin/env python3
"""
v0.15 native-scheduler SC diagnostics — READ-ONLY (production code untouched).

Establishes the OCELOT SC baseline under the NATIVE scheduler
(get_next_step, v0.14.1 task 1) with production parameters, replacing the
v0.14 manual-scheduler characterization numbers (which are retained only as
manual reference in sc_audit_diagnostics.py).

Scenarios (all pure drift 0.5 m, dz=0.005 → 100 steps, mirroring the v0.14
manual diagnostics so the two schedulers can be compared directly):
  1. smoke     : SC OFF vs ON @ 500 fC (same seed, identical particles)
  2. charge    : Q = 0/10/50/100/500/1000 fC monotonicity
  3. converge  : N (1e4/5e4/1e5), mesh (33/63/127), SC step (1/5/10) @ 500 fC
  4. full beam : production full beamline, SC ON @ 100 fC (production mesh 63³,
                 N=5e4, dz=0.001) — sample-plane effect vs no-SC

Every run goes through validation/backend.run_ocelot (the production entry
point) with a drift-only lattice (Drift 0.5 m + zero-length sample marker →
SC coverage [0, 0.5) exactly, HARD FAIL contract applies).

Usage: /opt/anaconda3/bin/python3 validation/sc_native_diagnostics.py
"""

import os
import sys
import copy
import time

import numpy as np

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
for p in (_THIS_DIR, os.path.dirname(_THIS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from shared.params import load_config  # noqa: E402
from validation.backend import run_ocelot  # noqa: E402

DZ = 0.005
L_DRIFT = 0.5


def drift_cfg(cfg, q_fC, mesh, nparticles, sc_step):
    """Deep-copied config with a drift-only lattice (native coverage [0,0.5))."""
    c = copy.deepcopy(cfg)
    c["lattice"]["elements"] = [
        {"name": "drift1", "type": "drift", "z_start": 0.0,
         "length": L_DRIFT, "parameters": {}},
        {"name": "sample", "type": "sample", "z_start": L_DRIFT,
         "length": 0.0, "parameters": {}},
    ]
    c["beam"]["charge_fC"] = q_fC
    c["beam"]["n_particles"] = nparticles
    c["space_charge"]["mesh"] = list(mesh)
    c["space_charge"]["step"] = sc_step
    return c


def run(cfg, q_fC, mesh, nparticles, sc_step, sc_on=True):
    c = drift_cfg(cfg, q_fC, mesh, nparticles, sc_step)
    r = run_ocelot(c, "full", sc_enabled=sc_on, n_particles=nparticles,
                   sc_step=sc_step, sc_mesh=list(mesh), dz=DZ)
    # sample-plane values (z = L_DRIFT)
    out = {}
    for k in ("sigma_x_um", "sigma_y_um", "sigma_z_um", "sigma_delta_e3",
              "eps_nx_mm_mrad", "eps_ny_mm_mrad"):
        out[k] = float(np.interp(L_DRIFT * 1e3, r.z_mm, getattr(r, k)))
    out["apply_count"] = r.meta.get("sc_apply_count", 0)
    out["effective"] = r.meta.get("sc_effective", False)
    out["z_max"] = float(r.z_mm[-1])
    return out, r


def main():
    cfg = load_config()
    print("=" * 70)
    print("  v0.15 native-scheduler SC diagnostics (production entry point)")
    print("=" * 70)
    t_start = time.time()

    # ── 1. smoke: SC OFF vs ON @ 500 fC ──
    print("\n[smoke] pure drift 0.5 m, 500 fC, mesh 63³, N=5e4, step 1")
    off, _ = run(cfg, 500.0, [63, 63, 63], 50000, 1, sc_on=False)
    on, r_on = run(cfg, 500.0, [63, 63, 63], 50000, 1, sc_on=True)
    print(f"  OFF: σx={off['sigma_x_um']:9.3f} σz={off['sigma_z_um']:9.3f} "
          f"εnx={off['eps_nx_mm_mrad']:.4f}")
    print(f"  ON : σx={on['sigma_x_um']:9.3f} σz={on['sigma_z_um']:9.3f} "
          f"εnx={on['eps_nx_mm_mrad']:.4f}  apply={on['apply_count']} "
          f"effective={on['effective']}")
    for k in ("sigma_x_um", "sigma_z_um", "eps_nx_mm_mrad"):
        d = on[k] - off[k]
        print(f"       Δ{k} = {d:+.3f} ({(d / abs(off[k])) * 100:+.2f}%)")
    # v0.14 MANUAL reference (same scenario): σx 725→2436 (+236%), σz 302→1595
    print("  (v0.14 manual ref @500 fC: σx 725→2436 µm +236%, σz→1595 µm +428%)")

    # ── 2. charge scan ──
    print("\n[charge scan] Q = 0/10/50/100/500/1000 fC (mesh 63, 5e4, step 1)")
    rows = []
    for q in (0.0, 10.0, 50.0, 100.0, 500.0, 1000.0):
        r_, _ = run(cfg, q, [63, 63, 63], 50000, 1, sc_on=(q > 0))
        rows.append((q, r_))
        print(f"  Q={q:7.0f} fC  σx={r_['sigma_x_um']:9.3f}  "
              f"σz={r_['sigma_z_um']:9.3f}  εnx={r_['eps_nx_mm_mrad']:.4f}")
    sx = [r_["sigma_x_um"] for _, r_ in rows]
    mon = all(sx[i + 1] > sx[i] for i in range(len(sx) - 1))
    print(f"  σx(Q) monotonic: {mon}")

    # ── 3. convergence scan @ 500 fC ──
    print("\n[convergence] 500 fC, native scheduler")
    print("  A. N (mesh 63, step 1):")
    for n in (10000, 50000, 100000):
        r_, _ = run(cfg, 500.0, [63, 63, 63], n, 1)
        print(f"     N={n:6d}  σx={r_['sigma_x_um']:9.3f}  "
              f"σz={r_['sigma_z_um']:9.3f}  εnx={r_['eps_nx_mm_mrad']:.4f}")
    print("  B. mesh (5e4, step 1):")
    for m in (33, 63, 127):
        r_, _ = run(cfg, 500.0, [m, m, m], 50000, 1)
        print(f"     mesh={m:3d}³  σx={r_['sigma_x_um']:9.3f}  "
              f"σz={r_['sigma_z_um']:9.3f}  εnx={r_['eps_nx_mm_mrad']:.4f}")
    print("  C. SC step (5e4, mesh 63):")
    for s in (1, 5, 10):
        r_, _ = run(cfg, 500.0, [63, 63, 63], 50000, s)
        print(f"     step={s:2d}  σx={r_['sigma_x_um']:9.3f}  "
              f"σz={r_['sigma_z_um']:9.3f}  εnx={r_['eps_nx_mm_mrad']:.4f}")

    # ── 4. full beamline, SC ON, production parameters ──
    print("\n[full beamline] production lattice, SC ON @100 fC (63³, 5e4, "
          "dz=0.001)")
    r_full = run_ocelot(cfg, "full", sc_enabled=True)     # production defaults
    zq = 777.0
    f_on = {}
    for k in ("sigma_x_um", "sigma_y_um", "sigma_z_um", "sigma_delta_e3",
              "eps_nx_mm_mrad", "eps_ny_mm_mrad"):
        f_on[k] = float(np.interp(zq, r_full.z_mm, getattr(r_full, k)))
    r_off = run_ocelot(cfg, "full")                        # SC OFF (no-SC)
    f_off = {}
    for k in ("sigma_x_um", "sigma_y_um", "sigma_z_um", "sigma_delta_e3",
              "eps_nx_mm_mrad", "eps_ny_mm_mrad"):
        f_off[k] = float(np.interp(zq, r_off.z_mm, getattr(r_off, k)))
    print(f"  SC OFF: σx={f_off['sigma_x_um']:9.3f} σz={f_off['sigma_z_um']:9.3f} "
          f"εnx={f_off['eps_nx_mm_mrad']:.4f}  (no-SC baseline)")
    print(f"  SC ON : σx={f_on['sigma_x_um']:9.3f} σz={f_on['sigma_z_um']:9.3f} "
          f"εnx={f_on['eps_nx_mm_mrad']:.4f}  apply="
          f"{r_full.meta['sc_apply_count']} coverage="
          f"[{r_full.meta['sc_coverage_start_m']}, "
          f"{r_full.meta['sc_coverage_stop_m']}]")
    for k in ("sigma_x_um", "sigma_z_um", "sigma_delta_e3", "eps_nx_mm_mrad"):
        d = f_on[k] - f_off[k]
        print(f"       Δ{k} = {d:+.3f} ({(d / abs(f_off[k])) * 100:+.2f}%)")

    # ── report ──
    report = os.path.join(_THIS_DIR, "reports", "SC_native_baseline.md")
    with open(report, "w") as f:
        f.write("# SC Native-Scheduler Baseline (v0.15)\n\n")
        f.write("Date: 2026-08-16 · OCELOT native `get_next_step()` scheduler, "
                "production entry point `validation/backend.run_ocelot`\n\n")
        f.write("## smoke (0.5 m drift, 500 fC)\n\n")
        f.write(f"| | σx [µm] | σz [µm] | εnx |\n|---|---|---|---|\n")
        f.write(f"| SC OFF | {off['sigma_x_um']:.3f} | "
                f"{off['sigma_z_um']:.3f} | {off['eps_nx_mm_mrad']:.4f} |\n")
        f.write(f"| SC ON | {on['sigma_x_um']:.3f} | "
                f"{on['sigma_z_um']:.3f} | {on['eps_nx_mm_mrad']:.4f} |\n")
        f.write(f"| Δ | +{on['sigma_x_um'] - off['sigma_x_um']:.1f} | "
                f"+{on['sigma_z_um'] - off['sigma_z_um']:.1f} | "
                f"+{on['eps_nx_mm_mrad'] - off['eps_nx_mm_mrad']:.4f} |\n")
        f.write("\n(v0.14 manual ref @500 fC: σx 725→2436 µm +236%, "
                "σz→1595 µm +428% — manual applies SC beyond coverage and with "
                "nominal tail zstep; see SC_integration_audit §9-11)\n\n")
        f.write("## charge scan\n\n")
        f.write("| Q [fC] | σx [µm] | σz [µm] | εnx |\n|---|---|---|---|\n")
        for q, r_ in rows:
            f.write(f"| {q:.0f} | {r_['sigma_x_um']:.3f} | "
                    f"{r_['sigma_z_um']:.3f} | "
                    f"{r_['eps_nx_mm_mrad']:.4f} |\n")
        f.write(f"\nσx(Q) monotonic: {mon}\n\n")
        f.write("## convergence (500 fC)\n\n")
        f.write("N (mesh 63, step 1): 1e4/5e4/1e5; mesh 33/63/127; "
                "step 1/5/10 — see terminal log (tables printed above).\n")
        f.write("\n## full beamline (100 fC, 63³, 5e4, dz=0.001)\n\n")
        f.write(f"| | σx [µm] | σz [µm] | σδ [e-3] | εnx |\n|---|---|---|---|---|\n")
        f.write(f"| SC OFF | {f_off['sigma_x_um']:.3f} | "
                f"{f_off['sigma_z_um']:.3f} | {f_off['sigma_delta_e3']:.4f} | "
                f"{f_off['eps_nx_mm_mrad']:.4f} |\n")
        f.write(f"| SC ON | {f_on['sigma_x_um']:.3f} | "
                f"{f_on['sigma_z_um']:.3f} | {f_on['sigma_delta_e3']:.4f} | "
                f"{f_on['eps_nx_mm_mrad']:.4f} |\n")
        f.write(f"\nprovenance: seed={cfg['random']['seed']}, "
                f"scheduler=ocelot_native, coverage="
                f"[{r_full.meta['sc_coverage_start_m']}, "
                f"{r_full.meta['sc_coverage_stop_m']}], "
                f"apply_count={r_full.meta['sc_apply_count']}\n")
    print(f"\nreport -> {report}")
    print(f"total time: {time.time() - t_start:.0f} s")


if __name__ == "__main__":
    main()
