#!/usr/bin/env python3
"""
GPT main route ↔ validation OCELOT route — lattice single-source equivalence.

A. Geometry: the GPT main route's built lattice (drift+solenoid+rf, step 4
   types) must exactly match lattice.elements (names, types, lengths, order,
   counts, RF kick positions, sample position, total length).
B. Step routing: step1/2 apply no RF kicks and no solenoids as active;
   step3/4 activate all solenoids and all RF instances; every step keeps the
   total length == sample position; SC process only per step-4/config switch.
C. Default-config result regression: GPT route vs validation run_ocelot
   ("full") at the sample plane, all quantities within 2 % (MC-noise aware).
D. Baseline regression (run separately): run_all.py + test_r56_convention.py.

Usage:  python3 validation/test_gpt_route_equivalence.py
"""

import os
import sys

import numpy as np

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_THIS_DIR)
for p in (_REPO, os.path.join(_REPO, "GPT模拟"), _THIS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from shared.params import load_config, _lattice_elements, z_sample, elements_of_type  # noqa: E402
from validation.backend import run_ocelot  # noqa: E402
from validation import common  # noqa: E402
from GPT模拟 import ued_beamline_v2 as gpt  # noqa: E402

TOL_SAMPLE = 2.0   # %


def canonical_expected(cfg, active_types):
    """(name, class, length) sequence that the builder must produce."""
    out = []
    for e in _lattice_elements(cfg):
        L = e["length"]
        if L <= 0:
            continue
        if e["type"] == "solenoid" and "solenoid" in active_types:
            out.append((e["name"], "Solenoid", L))
        elif e["type"] == "rf_cavity" and "rf_cavity" in active_types:
            out.append((e["name"] + "_BODY", "Drift", L))
        else:
            out.append((e["name"], "Drift", L))
    return out


def main():
    cfg = load_config()
    n_sol = len([e for e in elements_of_type(cfg, "solenoid") if e["length"] > 0])
    n_rf = len([e for e in elements_of_type(cfg, "rf_cavity") if e["length"] > 0])
    zs = z_sample(cfg)

    print(f"\n== A. Geometry — GPT main route vs shared lattice ==")
    lat, rf_elems = gpt.build_lattice_from_shared(
        cfg, gpt.STEP_ACTIVE[4])
    exp = canonical_expected(cfg, gpt.STEP_ACTIVE[4])
    built = [(e.id, type(e).__name__, e.l) for e in lat.sequence]
    ok_geo = True
    if len(built) != len(exp):
        ok_geo = False
        print(f"  FAIL: element count {len(built)} != expected {len(exp)}")
    for i, ((bn, bc, bl), (en, ec, el)) in enumerate(zip(built, exp)):
        if (bn, bc, round(bl, 12)) != (en, ec, round(el, 12)):
            ok_geo = False
            print(f"  FAIL at #{i}: built=({bn},{bc},{bl})  "
                  f"expected=({en},{ec},{el})")
    total = sum(e.l for e in lat.sequence)
    ok_tot = abs(total - zs) < 1e-12
    rf_pos = [e["z_start"] for e in rf_elems]
    exp_rf_pos = [e["z_start"] for e in elements_of_type(cfg, "rf_cavity")
                  if e["length"] > 0]
    ok_rf = (rf_pos == exp_rf_pos)
    ok_sample = abs(total - zs) < 1e-12
    print(f"  elements: {len(built)}  total={total*1e3:.3f}mm "
          f"(sample {zs*1e3:.0f}mm) {'PASS' if ok_tot else 'FAIL'}")
    print(f"  solenoid count: {sum(1 for _, c, _ in built if c=='Solenoid')} "
          f"(expected {n_sol})")
    print(f"  RF bodies: {sum(1 for n, _, _ in built if n.endswith('_BODY'))} "
          f"(expected {n_rf})  RF kick z: {[round(z*1e3) for z in rf_pos]}mm "
          f"{'PASS' if ok_rf else 'FAIL'}")
    print(f"  exact sequence match: {'PASS' if ok_geo else 'FAIL'}")

    print(f"\n== B. Step routing ==")
    ok_steps = True
    for step, act in gpt.STEP_ACTIVE.items():
        lat_s, rf_s = gpt.build_lattice_from_shared(cfg, act)
        tot_s = sum(e.l for e in lat_s.sequence)
        sol_s = sum(1 for e in lat_s.sequence
                    if type(e).__name__ == "Solenoid")
        exp_sol = n_sol if step >= 2 else 0
        exp_rf = n_rf if step >= 3 else 0
        ok = (tot_s - zs < 1e-12 and sol_s == exp_sol and len(rf_s) == exp_rf)
        ok_steps &= ok
        print(f"  step{step}: total={tot_s*1e3:.0f}mm sol={sol_s} "
              f"rf_kicks={len(rf_s)}  "
              f"({'PASS' if ok else f'FAIL (exp sol={exp_sol} rf={exp_rf})'})")
    # runtime: no RF kick below step 3 (σ_δ must stay at input), kick at 3/4
    for step, expect_kick in ((1, False), (2, False), (3, True), (4, True)):
        # v0.15 task C: an SC-requested run must carry the cathode→sample
        # anchors, otherwise the runtime state contract HARD FAILS (the
        # coverage would silently shorten to the last non-zero element).
        lat_s, rf_s = gpt.build_lattice_from_shared(
            cfg, gpt.STEP_ACTIVE[step], keep_zero_markers=(step >= 4))
        r = gpt.run_beamline(lat_s, rf_s, sc_enabled=(step >= 4),
                             nparticles=20000)
        sd_end = r["history"]["sigma_delta_e3"][-1]
        kicked = sd_end > 1.0   # history units: ×10⁻³; no-kick ≈ 0.1, kick ≈ 2.9
        ok = (kicked == expect_kick)
        ok_steps &= ok
        print(f"  step{step} runtime σ_δ(end)={sd_end:.2e} -> "
              f"{'kick' if kicked else 'no kick'} "
              f"({'PASS' if ok else 'FAIL'})")
    print(f"  step routing: {'PASS' if ok_steps else 'FAIL'}")

    print(f"\n== C. Default-config result regression (sample plane) ==")
    lat_g, rf_g = gpt.build_lattice_from_shared(cfg, gpt.STEP_ACTIVE[4])
    r_gpt = gpt.run_beamline(lat_g, rf_g, sc_enabled=False)
    r_val = run_ocelot(cfg, "full")
    zq = zs * 1e3
    fields = ["sigma_x_um", "sigma_y_um", "sigma_z_um",
              "sigma_delta_e3", "eps_nx_mm_mrad", "eps_ny_mm_mrad"]

    def sample_checked(z_query, z_arr, y_arr, label):
        """Interpolate ONLY after proving the trajectory covers the query.

        np.interp CLAMPS outside the data range: an out-of-range sample query
        silently returns the last tracked value, so a comparison could "pass"
        while the sample plane was never actually reached (v0.15 repair 4D).
        """
        z_arr = np.asarray(z_arr, dtype=float)
        y_arr = np.asarray(y_arr, dtype=float)
        if z_arr.size == 0 or not (z_arr[0] - 1e-9 <= z_query <= z_arr[-1] + 1e-9):
            raise AssertionError(
                f"{label}: trajectory covers [{z_arr[0]:.9f}, {z_arr[-1]:.9f}] mm "
                f"but the sample plane is {z_query:.9f} mm — OUTSIDE the tracked "
                f"range; np.interp would have clamped to the endpoint")
        return float(np.interp(z_query, z_arr, y_arr))

    devs = {}
    cov_ok = True
    try:
        for f in fields:
            vg = sample_checked(zq, r_gpt["history"]["z_mm"],
                                r_gpt["history"][f], f"GPT.{f}")
            vv = sample_checked(zq, r_val.z_mm, getattr(r_val, f),
                                f"validation.{f}")
            devs[f] = abs(vg - vv) / abs(vv) * 100
    except AssertionError as e:
        cov_ok = False
        print(f"  SAMPLE COVERAGE ASSERTION FAILED: {e}")
    history_equal = all(np.array_equal(np.asarray(r_gpt["history"][f]),
                                      getattr(r_val, f)) for f in ["z_mm"] + fields)
    ok_c = cov_ok and history_equal and all(devs[f] == 0.0 for f in fields)
    print(f"  sample-plane coverage asserted before interpolation "
          f"(GPT z∈[{np.asarray(r_gpt['history']['z_mm'])[0]:.3f}, "
          f"{np.asarray(r_gpt['history']['z_mm'])[-1]:.3f}] mm, "
          f"validation z∈[{np.asarray(r_val.z_mm)[0]:.3f}, "
          f"{np.asarray(r_val.z_mm)[-1]:.3f}] mm, query {zq:.3f} mm)  "
          f"{'PASS' if cov_ok else 'FAIL'}")
    for f in fields:
        if f not in devs:
            continue
        print(f"  {f:18s} GPT={np.interp(zq, np.asarray(r_gpt['history']['z_mm']), np.asarray(r_gpt['history'][f])):.3f}  "
              f"validation={np.interp(zq, r_val.z_mm, getattr(r_val, f)):.3f}  "
              f"dev={devs[f]:.2f}%  {'PASS' if devs[f] < TOL_SAMPLE else 'FAIL'}")
    print(f"  identical config/seed/N/dz: full histories exactly equal={history_equal}")
    print(f"  sample-plane regression: {'PASS' if ok_c else 'FAIL'}")

    ok_all = ok_geo and ok_tot and ok_rf and ok_sample and ok_steps and ok_c
    print(f"\n== OVERALL: {'PASS' if ok_all else 'FAIL'} ==")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
