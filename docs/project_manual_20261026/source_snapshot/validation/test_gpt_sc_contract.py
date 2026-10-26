#!/usr/bin/env python3
"""
Task C regression: the GPT main route must execute the full SC runtime state
contract (shared/sc_state.SCState — no second state machine).

Fault injection is done IN-PROCESS and restored afterwards; OCELOT is never
uninstalled or modified on disk.

Scenarios (all through GPT模拟.ued_beamline_v2.run_beamline):
  1. normal SC ON        → available/configured/attached, apply_count>0,
                           effective=True, coverage == [0, sample(lattice)]
  2. import failure      → HARD FAIL (RuntimeError)
  3. construction failure→ HARD FAIL
  4. attach failure      → HARD FAIL
  5. zero applies        → HARD FAIL (apply_count == 0)
  6. wrong coverage      → HARD FAIL (lattice has no sample anchor → the SC
                           interval would be silently shortened)
  7. SC OFF with the SC module unavailable → the no-SC run must still work
                           (lazy import; requested=False ⇒ effective=False)
  8. consistency         → saved sc_enabled == effective, requested recorded

Usage: /opt/anaconda3/bin/python3 validation/test_gpt_sc_contract.py
"""

import contextlib
import copy
import io
import os
import sys
import types

import numpy as np

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_THIS_DIR)
for p in (_THIS_DIR, _REPO, os.path.join(_REPO, "AG")):
    if p not in sys.path:
        sys.path.insert(0, p)

from shared.params import load_config  # noqa: E402


def short_cfg(cfg, length=0.05):
    """cfg copy with a short lattice + small mesh (fast SC characterization)."""
    c = copy.deepcopy(cfg)
    c["lattice"]["elements"] = [
        {"name": "drift1", "type": "drift", "z_start": 0.0,
         "length": length, "parameters": {}},
        {"name": "sample", "type": "sample", "z_start": length,
         "length": 0.0, "parameters": {}},
    ]
    c["space_charge"]["mesh"] = [33, 33, 33]
    c["space_charge"]["step"] = 1
    return c


def make_lat(length, with_sample_marker=True):
    from ocelot.cpbd.elements import Drift
    from ocelot.cpbd.magnetic_lattice import MagneticLattice
    elems = [Drift(l=length, eid="d1")]
    if with_sample_marker:
        elems.append(Drift(l=0.0, eid="sample_MARKER"))
    lat = MagneticLattice(elems, method={"global": "SecondTM"})
    lat.update_transfer_maps()
    return lat


def call_run_beamline(cfg, lat, sc_enabled, **kw):
    from GPT模拟 import ued_beamline_v2 as gpt
    with contextlib.redirect_stdout(io.StringIO()):
        return gpt.run_beamline(lat, [], sc_enabled=sc_enabled,
                                nparticles=1500, cfg_override=cfg, **kw)


def expect_fail(desc, fn):
    try:
        fn()
    except RuntimeError as e:
        ok = "SC runtime state HARD FAIL" in str(e)
        print(f"  {desc}: RuntimeError — {str(e)[:78]} "
              f"{'PASS' if ok else 'FAIL (wrong exception source)'}")
        return ok
    except Exception as e:                       # noqa: BLE001
        print(f"  {desc}: {type(e).__name__} (not the SC contract) — "
              f"{str(e)[:60]} FAIL")
        return False
    print(f"  {desc}: NO ERROR RAISED — FAIL")
    return False


def main():
    cfg = load_config()
    print("=" * 70)
    print("  Task C: GPT main-route SC runtime state contract")
    print("=" * 70)
    ok = True
    c = short_cfg(cfg)

    # ── 1. normal SC ON ──
    lat = make_lat(0.05)
    r = call_run_beamline(c, lat, True)
    normal_ok = (r["sc_requested"] is True and r["sc_available"] is True
                 and r["sc_configured"] is True and r["sc_attached"] is True
                 and r["sc_apply_count"] > 0 and r["sc_effective"] is True
                 and abs(r["sc_coverage_start_m"]) < 1e-12
                 and abs(r["sc_coverage_stop_m"] - 0.05) < 1e-9)
    ok &= normal_ok
    print(f"  1. normal SC ON: requested={r['sc_requested']} available="
          f"{r['sc_available']} configured={r['sc_configured']} attached="
          f"{r['sc_attached']} apply={r['sc_apply_count']} effective="
          f"{r['sc_effective']} coverage=[{r['sc_coverage_start_m']:.3f},"
          f"{r['sc_coverage_stop_m']:.3f}]  {'PASS' if normal_ok else 'FAIL'}")

    # ── 2. import failure → HARD FAIL ──
    saved_mod = sys.modules.get("ocelot.cpbd.sc")
    sys.modules["ocelot.cpbd.sc"] = None
    try:
        ok &= expect_fail("2. import failure", lambda: call_run_beamline(
            c, make_lat(0.05), True))
    finally:
        if saved_mod is not None:
            sys.modules["ocelot.cpbd.sc"] = saved_mod
        else:
            sys.modules.pop("ocelot.cpbd.sc", None)

    # ── 3. construction failure → HARD FAIL ──
    import ocelot.cpbd.sc as scmod
    saved_sc = scmod.SpaceCharge

    class Boom:
        def __init__(self, *a, **k):
            raise RuntimeError("injected construction failure")

    scmod.SpaceCharge = Boom
    try:
        ok &= expect_fail("3. construction failure", lambda: call_run_beamline(
            c, make_lat(0.05), True))
    finally:
        scmod.SpaceCharge = saved_sc

    # ── 4. attach failure → HARD FAIL ──
    from GPT模拟 import ued_beamline_v2 as gpt
    saved_navi = gpt.Navigator

    class BadNavi:
        def __init__(self, *a, **k):
            pass

        def add_physics_proc(self, *a, **k):
            raise RuntimeError("injected attach failure")

    gpt.Navigator = BadNavi
    try:
        ok &= expect_fail("4. attach failure", lambda: call_run_beamline(
            c, make_lat(0.05), True))
    finally:
        gpt.Navigator = saved_navi

    # ── 5. zero applies → HARD FAIL ──
    zero_lat = make_lat(0.0)          # zero-length lattice → no steps
    ok &= expect_fail("5. zero applies", lambda: call_run_beamline(
        c, zero_lat, True))

    # ── 6. wrong coverage → HARD FAIL (no sample anchor) ──
    no_anchor = make_lat(0.05, with_sample_marker=False)
    ok &= expect_fail("6. wrong coverage (no sample anchor)",
                      lambda: call_run_beamline(c, no_anchor, True))

    # ── 7. SC OFF with SC module unavailable → must still run ──
    saved_mod = sys.modules.get("ocelot.cpbd.sc")
    sys.modules["ocelot.cpbd.sc"] = None
    try:
        r_off = call_run_beamline(c, make_lat(0.05), False)
        off_ok = (r_off["sc_requested"] is False
                  and r_off["sc_effective"] is False
                  and r_off["sc_apply_count"] == 0
                  and len(r_off["history"]["z_mm"]) > 0)
    except Exception as e:                       # noqa: BLE001
        off_ok = False
        print(f"  7. SC OFF + SC unavailable raised {type(e).__name__}: {e}")
    finally:
        if saved_mod is not None:
            sys.modules["ocelot.cpbd.sc"] = saved_mod
        else:
            sys.modules.pop("ocelot.cpbd.sc", None)
    ok &= off_ok
    print(f"  7. SC OFF + SC module unavailable: ran to completion, "
          f"requested={r_off['sc_requested']} effective="
          f"{r_off['sc_effective']}  {'PASS' if off_ok else 'FAIL'}")

    # ── 8. saved-state consistency ──
    cons_ok = (r["sc_effective"] == (r["sc_apply_count"] > 0)
               and r["sc_requested"] is True
               and r["sc_effective"] is True)
    ok &= cons_ok
    print(f"  8. consistency: sc_effective == (apply_count>0) == "
          f"{r['sc_effective']}, requested recorded={r['sc_requested']}  "
          f"{'PASS' if cons_ok else 'FAIL'}")

    print(f"\n  Task C SC contract: {'ALL PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
