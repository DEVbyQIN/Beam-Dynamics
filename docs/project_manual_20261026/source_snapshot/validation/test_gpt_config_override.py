#!/usr/bin/env python3
"""
Repair 1 regression: cfg_override must REALLY take effect on the GPT main
route, with a clear precedence chain and no cross-run state leakage.

Audit counterexample reproduced before the fix: overriding
energy 100→200 keV, charge 100→500 fC, spot 85→170 µm, step 5→10 mm produced
an IDENTICAL history, because run_beamline/build_lattice_from_shared/
apply_rf_kick all read module import-time globals.

Checks:
  1. a cfg_override changes step count, probe list, initial size, sample σx,
     and the SOLENOID strength built from that cfg's energy;
  2. run provenance proves the effective values reached the production call
     (energy, charge, N, spot, divergence, σ_δ, seed, dz, probes);
  3. total particle charge equals the overridden charge (sum of q_array);
  4. precedence: explicit argument > cfg_override (explicit nparticles wins);
  5. NO STATE LEAK: cfg-A → cfg-B → cfg-A gives bit-identical cfg-A results;
  6. sc_enabled precedence: explicit False is NOT overridden by config True.

Usage: /opt/anaconda3/bin/python3 validation/test_gpt_config_override.py
"""

import contextlib
import copy
import io
import os
import sys

import numpy as np

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_THIS_DIR)
for p in (_THIS_DIR, _REPO, os.path.join(_REPO, "AG")):
    if p not in sys.path:
        sys.path.insert(0, p)

from GPT模拟 import ued_beamline_v2 as gpt  # noqa: E402

BASE = gpt.load_config()


def cfg_alt():
    c = copy.deepcopy(BASE)
    c["beam"]["energy_keV"] = 200.0
    c["beam"]["charge_fC"] = 500.0
    c["initial_distribution"]["spot_rms_um"] = 170.0
    c["initial_distribution"]["sigma_delta"] = 2.0e-4
    c["output"]["step_size_m"] = 0.010
    c["output"]["z_diagnostics_mm"] = [0, 100, 400, 777]
    return c


def run(cfg, nparticles=3000, **kw):
    lat, rf = gpt.build_lattice_from_shared(cfg, gpt.STEP_ACTIVE[1])
    with contextlib.redirect_stdout(io.StringIO()):
        return gpt.run_beamline(lat, rf, sc_enabled=False,
                                nparticles=nparticles, cfg_override=cfg, **kw)


def main():
    print("=" * 70)
    print("  Repair 1: cfg_override effectiveness + precedence + no leak")
    print("=" * 70)
    ok = True
    cA, cB = BASE, cfg_alt()

    rA1 = run(cA)
    rB1 = run(cB)
    rA2 = run(cA)                    # A again AFTER B → leak check

    # ── 1. override really reaches the physics ──
    pa, pb = rA1["run_params"], rB1["run_params"]
    n_steps_a = len(rA1["history"]["z_mm"])
    n_steps_b = len(rB1["history"]["z_mm"])
    # Schema v2 also records the genuine initial plane; no extra transport step.
    step_ok = (n_steps_a == 157 and n_steps_b == 79
               and rA1["history"]["z_mm"][0] == 0
               and rB1["history"]["z_mm"][0] == 0)
    probes_ok = (pb["z_probes_mm"] == [0, 100, 400, 777]
                 and len([k for k in rB1 if k.startswith("z")]) == 4)
    params_ok = (abs(pa["energy_keV"] - 100.0) < 1e-12
                 and abs(pb["energy_keV"] - 200.0) < 1e-12
                 and abs(pa["charge_C"] - 100e-15) < 1e-27
                 and abs(pb["charge_C"] - 500e-15) < 1e-27
                 and abs(pa["sigma_x0_m"] - 85e-6) < 1e-15
                 and abs(pb["sigma_x0_m"] - 170e-6) < 1e-15
                 and abs(pa["dz_track_m"] - 0.005) < 1e-15
                 and abs(pb["dz_track_m"] - 0.010) < 1e-15
                 and abs(pb["sigma_delta"] - 2.0e-4) < 1e-18
                 and pa["seed"] == pb["seed"] == 42)
    # divergence follows ε/(βγ·σ): same ε, different βγ and σ
    div_ok = not np.isclose(pa["sigma_xp_rad"], pb["sigma_xp_rad"])
    # reference kinematics follow the overridden energy
    kin_ok = (not np.isclose(pa["gamma"], pb["gamma"])
              and not np.isclose(pa["beta"], pb["beta"]))
    # sample σx must differ (spot + energy + step all changed)
    sx_ok = not np.isclose(rA1["z777mm"]["sigma_x_um"],
                           rB1["z777mm"]["sigma_x_um"])
    ok &= (step_ok and probes_ok and params_ok and div_ok and kin_ok and sx_ok)
    print(f"  1a. step count: A={n_steps_a} B={n_steps_b} "
          f"{'PASS' if step_ok else 'FAIL'}")
    print(f"  1b. probe list from override: {pb['z_probes_mm']} "
          f"{'PASS' if probes_ok else 'FAIL'}")
    print(f"  1c. effective params recorded: energy {pa['energy_keV']}/"
          f"{pb['energy_keV']} keV, Q {pa['charge_C']:.1e}/{pb['charge_C']:.1e} C, "
          f"spot {pa['sigma_x0_m']*1e6:.0f}/{pb['sigma_x0_m']*1e6:.0f} µm, "
          f"dz {pa['dz_track_m']}/{pb['dz_track_m']}  "
          f"{'PASS' if params_ok else 'FAIL'}")
    print(f"  1d. divergence recomputed ({pa['sigma_xp_rad']:.3e} vs "
          f"{pb['sigma_xp_rad']:.3e}), kinematics differ (γ {pa['gamma']:.4f} vs "
          f"{pb['gamma']:.4f})  {'PASS' if (div_ok and kin_ok) else 'FAIL'}")
    print(f"  1e. sample σx differs: {rA1['z777mm']['sigma_x_um']:.3f} vs "
          f"{rB1['z777mm']['sigma_x_um']:.3f} µm  {'PASS' if sx_ok else 'FAIL'}")

    # ── 2. total charge = sum of particle charges ──
    q_ok = (abs(pa["charge_total_C"] - 100e-15) < 1e-24
            and abs(pb["charge_total_C"] - 500e-15) < 1e-24
            and pa["n_particles_actual"] == pb["n_particles_actual"] == 3000)
    ok &= q_ok
    print(f"  2. particle charge sum: A={pa['charge_total_C']:.6e} C, "
          f"B={pb['charge_total_C']:.6e} C, N={pa['n_particles_actual']}  "
          f"{'PASS' if q_ok else 'FAIL'}")

    # ── 3. lattice/RF use THIS run's reference (solenoid k) ──
    latA, _ = gpt.build_lattice_from_shared(cA, gpt.STEP_ACTIVE[4])
    latB, _ = gpt.build_lattice_from_shared(cB, gpt.STEP_ACTIVE[4])
    kA = [e.k for e in latA.sequence if type(e).__name__ == "Solenoid"][0]
    kB = [e.k for e in latB.sequence if type(e).__name__ == "Solenoid"][0]
    k_ok = not np.isclose(kA, kB) and kB < kA        # k ∝ 1/p0, higher E → smaller
    ok &= k_ok
    print(f"  3. solenoid k from this cfg's energy: A={kA:.6f} B={kB:.6f} "
          f"1/m  {'PASS' if k_ok else 'FAIL'}")

    # ── 4. explicit nparticles beats cfg_override ──
    rP = run(cB, nparticles=1234)
    prec_ok = rP["run_params"]["n_particles_actual"] == 1234
    ok &= prec_ok
    print(f"  4. precedence explicit(1234) > cfg_override(N={cB['beam']['n_particles']}): "
          f"actual={rP['run_params']['n_particles_actual']}  "
          f"{'PASS' if prec_ok else 'FAIL'}")

    # ── 5. no state leak (A → B → A) ──
    leak_ok = (np.array_equal(rA1["history"]["z_mm"], rA2["history"]["z_mm"])
               and np.array_equal(rA1["history"]["sigma_x_um"],
                                  rA2["history"]["sigma_x_um"])
               and rA1["z777mm"]["sigma_x_um"] == rA2["z777mm"]["sigma_x_um"])
    ok &= leak_ok
    print(f"  5. no state leak (A→B→A bit-identical): {leak_ok} "
          f"{'PASS' if leak_ok else 'FAIL'}")

    # ── 6. explicit sc_enabled=False beats config enabled=True ──
    c_sc = copy.deepcopy(BASE)
    c_sc["space_charge"]["enabled"] = True
    lat_s, rf_s = gpt.build_lattice_from_shared(c_sc, gpt.STEP_ACTIVE[4],
                                                keep_zero_markers=True)
    with contextlib.redirect_stdout(io.StringIO()):
        r_sc = gpt.run_beamline(lat_s, rf_s, sc_enabled=False,
                                nparticles=2000, cfg_override=c_sc)
    sc_ok = (r_sc["sc_requested"] is False and r_sc["sc_effective"] is False
             and r_sc["sc_apply_count"] == 0)
    # and sc_enabled=None must fall back to the config
    with contextlib.redirect_stdout(io.StringIO()):
        r_auto = gpt.run_beamline(lat_s, rf_s, sc_enabled=None,
                                  nparticles=2000, cfg_override=c_sc,
                                  sc_mesh=[33, 33, 33])
    auto_ok = (r_auto["sc_requested"] is True and r_auto["sc_effective"] is True
               and r_auto["sc_apply_count"] > 0)
    ok &= (sc_ok and auto_ok)
    print(f"  6. sc_enabled precedence: explicit False wins "
          f"(requested={r_sc['sc_requested']}, effective={r_sc['sc_effective']}) "
          f"{'PASS' if sc_ok else 'FAIL'}; None → config "
          f"(requested={r_auto['sc_requested']}, applies={r_auto['sc_apply_count']}) "
          f"{'PASS' if auto_ok else 'FAIL'}")

    print(f"\n  Repair 1 config override: {'ALL PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
