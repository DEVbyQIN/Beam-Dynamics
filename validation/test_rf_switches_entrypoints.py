#!/usr/bin/env python3
"""
Task B regression: the FOUR production entrypoints must obey the SAME RF
switches (physics_switches.rf_longitudinal_kick / rf_transverse_kick),
independently, with real state changes (not just printed labels):

  entrypoint 1: validation.backend.run_ag
  entrypoint 2: AG.run_shared.main()      (config injected in-process)
  entrypoint 3: GPT模拟.ued_beamline_v2.run_beamline
  entrypoint 4: validation.backend.run_ocelot   (OCELOT macroparticle route)

For each of the four switch combinations the test measures PHYSICS:
  * longitudinal ON  → σ_δ grows (RF chirp kick applied)
  * longitudinal OFF → σ_δ unchanged from the initial value
  * transverse ON vs OFF → σ_x at the sample differs measurably
(the four combinations are compared pairwise to prove independence).

Every entrypoint is driven through its OWN switch plumbing: entrypoints 1/4
read `cfg["physics_switches"]` inside the backend (no explicit `switches=`
argument is passed, so the config path itself is under test), entrypoint 2
goes through AG.run_shared's config parsing, entrypoint 3 through the GPT
main route's `switches` argument.  The four rows must therefore agree on the
SEMANTICS of the switches (which role is on), not on model-approximation
details — σ_δ/σ_x values legitimately differ between envelope and
macroparticle models.

No production file is modified; entrypoint 2 is driven through in-process
injection of load_config/write_results (no real config/JSON touched).

Usage: /opt/anaconda3/bin/python3 validation/test_rf_switches_entrypoints.py
"""

import copy
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

from shared.params import load_config  # noqa: E402

COMBOS = [(True, True), (True, False), (False, True), (False, False)]
ZQ = 777.0


def cfg_with(cfg, long_on, trans_on):
    c = copy.deepcopy(cfg)
    c["physics_switches"] = {"rf_longitudinal_kick": bool(long_on),
                             "rf_transverse_kick": bool(trans_on)}
    return c


def sample(r, key, zq=ZQ):
    return float(np.interp(zq, np.asarray(r.z_mm), np.asarray(getattr(r, key))))


# ── entrypoint 1: validation backend.run_ag ──────────────────────────────
def run_ag_entry(cfg, long_on, trans_on):
    from validation.backend import run_ag
    r = run_ag(cfg_with(cfg, long_on, trans_on), "full",
               sc_enabled=False, solenoid_coupling=False)
    return {"sd": sample(r, "sigma_delta_e3"), "sx": sample(r, "sigma_x_um")}


# ── entrypoint 2: AG/run_shared.main() with in-process injection ─────────
def run_shared_entry(cfg, long_on, trans_on):
    import AG.run_shared as rs
    captured = {}

    def fake_write(route, probes, history, sha, sc_flag, meta=None):
        captured["meta"] = meta
        captured["probes"] = probes
        return "/dev/null"

    saved_lc, saved_wr = rs.load_config, rs.write_results
    rs.load_config = lambda *a, **k: cfg_with(cfg, long_on, trans_on)
    rs.write_results = fake_write
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rs.main()
    finally:
        rs.load_config, rs.write_results = saved_lc, saved_wr
    probes = captured["probes"]
    p = [q for q in probes if abs(q["z_mm"] - ZQ) < 1e-9][0]
    return {"sd": float(p["sigma_delta_e3"]), "sx": float(p["sigma_x_um"]),
            "meta": captured["meta"]}


# ── entrypoint 3: GPT main-route run_beamline ────────────────────────────
def run_gpt_entry(cfg, long_on, trans_on):
    from GPT模拟 import ued_beamline_v2 as gpt
    c = cfg_with(cfg, long_on, trans_on)
    sw = dict(c["physics_switches"])
    lat, rf_elems = gpt.build_lattice_from_shared(
        c, gpt.STEP_ACTIVE[4], keep_zero_markers=False)
    with contextlib.redirect_stdout(io.StringIO()):
        r = gpt.run_beamline(lat, rf_elems, sc_enabled=False,
                             nparticles=3000, switches=sw)
    p = r[f"z{ZQ:.0f}mm"]
    return {"sd": float(p["sigma_delta_e3"]), "sx": float(p["sigma_x_um"]),
            "rf_kicks": int(r["rf_kicks_applied"])}


# ── entrypoint 4: validation backend.run_ocelot (macroparticle route) ──
def run_ocelot_entry(cfg, long_on, trans_on):
    from validation.backend import run_ocelot
    # switches come from the CONFIG (no explicit switches= argument), so this
    # row exercises the backend's own config → switch plumbing.
    r = run_ocelot(cfg_with(cfg, long_on, trans_on), "full",
                   n_particles=3000, dz=0.001, sc_enabled=False)
    return {"sd": sample(r, "sigma_delta_e3"), "sx": sample(r, "sigma_x_um")}


def main():
    cfg = load_config()
    sd0 = cfg["initial_distribution"]["sigma_delta"] * 1e3   # e-3
    print("=" * 70)
    print("  Task B: RF switch consistency across the FOUR entrypoints")
    print("=" * 70)
    print(f"  initial σ_δ = {sd0:.4f} e-3 (longitudinal OFF must preserve it)")
    ok = True
    table = {}
    for name, fn in (("backend.run_ag", run_ag_entry),
                     ("AG.run_shared", run_shared_entry),
                     ("GPT.run_beamline", run_gpt_entry),
                     ("backend.run_ocelot", run_ocelot_entry)):
        table[name] = {}
        for long_on, trans_on in COMBOS:
            r = fn(cfg, long_on, trans_on)
            table[name][(long_on, trans_on)] = r
            sd_txt = f"{r['sd']:.4f}"
            print(f"  {name:<17s} L={int(long_on)} T={int(trans_on)}: "
                  f"σ_δ(end)={sd_txt:>9s}  σ_x(end)={r['sx']:9.1f} µm"
                  + (f"  rf_kicks={r['rf_kicks']}" if "rf_kicks" in r else ""))

    print("\n  --- checks ---")
    for name in table:
        t = table[name]
        # Reference for "longitudinal kick NOT applied": the same entrypoint
        # with BOTH switches off (the OCELOT statistics' initial σ_δ is a
        # sampled value, not exactly the config nominal).
        sd_ref = t[(False, False)]["sd"]
        # longitudinal ON → chirp (σ_δ grows well above the no-kick reference)
        on_ok = (t[(True, False)]["sd"] > 3 * sd_ref
                 and t[(True, True)]["sd"] > 3 * sd_ref)
        # longitudinal OFF → σ_δ identical to the no-kick reference
        off_ok = (abs(t[(False, True)]["sd"] - sd_ref) < 1e-9
                  and abs(t[(False, False)]["sd"] - sd_ref) < 1e-9)
        # transverse switch must change σ_x measurably, independent of L
        d_sx_L_on = abs(t[(True, True)]["sx"] - t[(True, False)]["sx"])
        d_sx_L_off = abs(t[(False, True)]["sx"] - t[(False, False)]["sx"])
        trans_ok = d_sx_L_on > 1.0 and d_sx_L_off > 1.0   # >1 µm
        # longitudinal effect must exist while T is OFF (independence)
        indep_ok = abs(t[(True, False)]["sd"] - t[(False, False)]["sd"]) > 3 * sd0
        row_ok = on_ok and off_ok and trans_ok and indep_ok
        ok &= row_ok
        print(f"  {name:<17s} L-on chirp={on_ok}  L-off preserved(vs {sd_ref:.4f})={off_ok}  "
              f"T effect (Δσx: {d_sx_L_on:.2f}/{d_sx_L_off:.2f} µm)={trans_ok}  "
              f"independent={indep_ok}  {'PASS' if row_ok else 'FAIL'}")

    # entrypoint 2 metadata must record the effective switches
    m = table["AG.run_shared"][(True, True)].get("meta", {})
    sw_ok = (m.get("switches") == {"rf_longitudinal_kick": True,
                                   "rf_transverse_kick": True}
             and "transverse kick" in m.get("rf", ""))
    ok &= sw_ok
    print(f"  AG.run_shared meta switches/rf descriptor consistent: {sw_ok} "
          f"{'PASS' if sw_ok else 'FAIL'}")

    print(f"\n  Task B RF-switch consistency: {'ALL PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
