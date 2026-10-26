#!/usr/bin/env python3
"""
Task D regression: GPT main-route tracking must reach the SAMPLE plane and the
probe diagnostics must not mislabel positions.

Bug reproduced before the fix: the SC-OFF loop used
    n_steps = int(total_length / dz_track)
with total_length = 0.777 m and dz_track = 0.005 m → 155 steps → 775 mm,
so the sample plane (777 mm) was never reached (the z777mm probe was absent).

Checks:
  1. default config (777 mm, 5 mm step): final tracked position == shared
     sample position; the z777mm probe EXISTS and is exact.
  2. non-integer total length (0.503 m): the tail is completed to 0.503 m.
  3. integer total length (0.500 m): no extra step beyond the full steps and
     the end position is still exact.
  4. boundary probes: z=0 start probe exact; a NON-step-aligned mid probe
     (422 mm with a 5 mm step) is flagged z_exact=False with its ACTUAL
     sampled position recorded (no step-end state passed off as an exact
     in-step diagnostic).
  5. the OLD 775 mm end point and the NEW 777 mm sample plane are recorded
     separately (they are different locations and must not be compared as
     "same-position error").

Usage: /opt/anaconda3/bin/python3 validation/test_gpt_tail_sample.py
"""

import contextlib
import io
import os
import sys

import numpy as np

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_THIS_DIR)
for p in (_THIS_DIR, _REPO, os.path.join(_REPO, "AG")):
    if p not in sys.path:
        sys.path.insert(0, p)

from shared.params import load_config, z_sample  # noqa: E402


def make_lattice(lengths):
    from ocelot.cpbd.elements import Drift
    from ocelot.cpbd.magnetic_lattice import MagneticLattice
    elems = [Drift(l=L, eid=f"d{i}") for i, L in enumerate(lengths)]
    lat = MagneticLattice(elems, method={"global": "SecondTM"})
    lat.update_transfer_maps()
    return lat


def run_gpt(lat, sc_enabled=False, nparticles=2000):
    from GPT模拟 import ued_beamline_v2 as gpt
    with contextlib.redirect_stdout(io.StringIO()):
        return gpt.run_beamline(lat, [], sc_enabled=sc_enabled,
                                nparticles=nparticles)


def main():
    cfg = load_config()
    z_smp = z_sample(cfg)
    dz = cfg["output"]["step_size_m"]
    print("=" * 70)
    print("  Task D: GPT main-route tail completion + sample-plane diagnostics")
    print("=" * 70)
    print(f"  shared sample z = {z_smp:.3f} m, configured step = {dz:.3f} m "
          f"(ratio {z_smp / dz:.3f} → int() drops "
          f"{(z_smp / dz - int(z_smp / dz)) * dz * 1e3:.1f} mm)")
    ok = True

    # ── 1. default config: sample reached + probe exists & exact ──
    lat = make_lattice([z_smp])
    r = run_gpt(lat)
    z_end = r["history"]["z_mm"][-1] / 1e3
    end_ok = abs(z_end - z_smp) < 1e-9
    probe = r.get(f"z{z_smp * 1e3:.0f}mm")
    probe_ok = probe is not None and probe["z_exact"] is True
    ok &= (end_ok and probe_ok)
    print(f"\n  1. default: final z = {z_end:.4f} m (expect {z_smp:.4f}) "
          f"{'PASS' if end_ok else 'FAIL'}; sample probe present={probe is not None}"
          f" exact={probe['z_exact'] if probe else None} "
          f"{'PASS' if probe_ok else 'FAIL'}")
    # old (buggy) end point = last full step
    n_full = int(z_smp / dz)
    z_old = n_full * dz
    print(f"     OLD int() end point = {z_old * 1e3:.1f} mm (kept in history as "
          f"step #{n_full}); NEW sample plane = {z_end * 1e3:.1f} mm — "
          f"recorded separately, not compared as same-position error")
    old_in_hist = any(abs(z / 1e3 - z_old) < 1e-9 for z in r["history"]["z_mm"])
    print(f"     old end point still present in history: {old_in_hist}")

    # ── 2. non-integer total length (0.503 m) ──
    lat2 = make_lattice([0.503])
    r2 = run_gpt(lat2)
    z2 = r2["history"]["z_mm"][-1] / 1e3
    ok2 = abs(z2 - 0.503) < 1e-9
    ok &= ok2
    print(f"\n  2. non-integer total 0.503 m: final z = {z2:.6f} "
          f"{'PASS' if ok2 else 'FAIL'}")

    # ── 3. integer total length (0.500 m) — no spurious tail step ──
    lat3 = make_lattice([0.500])
    r3 = run_gpt(lat3)
    z3 = r3["history"]["z_mm"][-1] / 1e3
    n3 = len(r3["history"]["z_mm"])
    # History v2 includes s=0 as well as each completed transport step.
    expected_rows = 1 + int(0.500 / dz)
    ok3 = (abs(z3 - 0.500) < 1e-9 and n3 == expected_rows
           and r3["history"]["z_mm"][0] == 0.)
    ok &= ok3
    print(f"  3. integer total 0.500 m: final z = {z3:.6f}, samples = {n3} "
          f"(expect {expected_rows}) {'PASS' if ok3 else 'FAIL'}")

    # ── 4. boundary probes: start exact; non-aligned mid probe flagged ──
    p0 = r.get("z0mm")
    start_ok = p0 is not None and p0["z_exact"] is True
    mid = r.get("z422mm")       # 422 mm is NOT a multiple of the 5 mm step
    if mid is not None:
        # UNIT FIX (repair 4C): z_actual_mm is in MILLIMETRES while dz is in
        # METRES — the previous `z_actual_mm % dz * 1e3` compared mm against m
        # (425 mm % 0.005 m = 0.005 → "4.999 > 1e-6"), so this check could only
        # ever fail for the wrong reason.  Compare in ONE unit (mm).
        step_mm = dz * 1e3
        residual_mm = mid["z_actual_mm"] % step_mm
        residual_mm = min(residual_mm, step_mm - residual_mm)   # round-off safe
        mid_ok = (mid["z_exact"] is False
                  and abs(mid["z_actual_mm"] - mid["z_mm"]) > 1e-9
                  and residual_mm < 1e-6)              # actual = a step end (mm)
        mid_txt = (f"z422 not aligned → exact={mid['z_exact']}, "
                   f"actual={mid['z_actual_mm']:.1f} mm "
                   f"(nominal {mid['z_mm']:.0f} mm, step {step_mm:.0f} mm, "
                   f"residual {residual_mm:.3e} mm)")
    else:
        mid_ok, mid_txt = False, "z422mm probe MISSING"
    ok &= (start_ok and mid_ok)
    print(f"\n  4. boundary probes: z0 exact={p0['z_exact'] if p0 else None} "
          f"{'PASS' if start_ok else 'FAIL'}")
    print(f"     {mid_txt} {'PASS' if mid_ok else 'FAIL'}")
    # aligned mid probes must be exact
    aligned = [n for n in ("z100mm", "z500mm") if n in r]
    aligned_ok = all(r[n]["z_exact"] is True for n in aligned)
    ok &= aligned_ok
    print(f"     aligned probes {aligned} all exact: {aligned_ok} "
          f"{'PASS' if aligned_ok else 'FAIL'}")

    print(f"\n  5. (see check 1) old 775 mm vs new 777 mm recorded separately")
    print(f"\n  Task D tail/sample diagnostics: {'ALL PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
