#!/usr/bin/env python3
"""
Repair 3 regression: the GPT main route's FINAL SAVED OUTPUT must carry the
probe position markers and the runtime SC state contract.

Audit finding before the fix: run_beamline recorded
    z_mm=422, z_actual_mm=425, z_exact=False
but main() dropped the last two when calling make_probe, so the saved file
presented the 425 mm state as "422 mm" with no warning.

This test exercises the COMPLETE chain — main() → real make_probe → real
shared.output_schema.write_results → JSON read back from disk.  Nothing is
mocked: only the config (in-process), the particle count and the output
directory are injected.

Checks:
  * z=0 probe exact; sample probe exact and the trajectory really reaches the
    shared sample position;
  * a NON-step-aligned mid probe keeps a different z_actual_mm and z_exact=False;
  * saved top-level sc_enabled == runtime sc_effective;
  * requested / available / configured / attached / apply_count / coverage are
    persisted (not just the scheduler name);
  * rf_kicks_applied equals the ACTUAL executed kick count.

Usage: /opt/anaconda3/bin/python3 validation/test_gpt_saved_output.py
"""

import contextlib
import copy
import io
import json
import os
import sys
import tempfile

import numpy as np

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_THIS_DIR)
for p in (_THIS_DIR, _REPO, os.path.join(_REPO, "AG")):
    if p not in sys.path:
        sys.path.insert(0, p)

from shared.output_schema import load_results  # noqa: E402
from GPT模拟 import ued_beamline_v2 as gpt  # noqa: E402

# short lattice with an RF cavity, a non-aligned mid probe and the sample plane
LEN_DRIFT1, LEN_RF, LEN_DRIFT3 = 0.020, 0.022, 0.008
Z_SAMPLE = LEN_DRIFT1 + LEN_RF + LEN_DRIFT3          # 0.050 m
# The probe LABEL comes from the config's nominal mm value, so compare against
# the rounded nominal (0.020+0.022+0.008 = 0.05000000000000001 m in binary
# floating point — a raw *1e3 lookup would miss the saved 50.0 mm record).
Z_SAMPLE_MM = round(Z_SAMPLE * 1e3, 6)
PROBES = [0, 20, 22, 50]                              # 22 mm is NOT a 5 mm multiple


def test_cfg():
    c = copy.deepcopy(gpt.load_config())
    c["lattice"]["elements"] = [
        {"name": "drift1", "type": "drift", "z_start": 0.0,
         "length": LEN_DRIFT1, "parameters": {}},
        {"name": "rf1", "type": "rf_cavity", "z_start": LEN_DRIFT1,
         "length": LEN_RF,
         "parameters": {"frequency_GHz": 2.856, "voltage_kV": 30.0,
                        "phase_rad": 3.1416}},
        {"name": "drift3", "type": "drift", "z_start": LEN_DRIFT1 + LEN_RF,
         "length": LEN_DRIFT3, "parameters": {}},
        {"name": "sample", "type": "sample", "z_start": Z_SAMPLE,
         "length": 0.0, "parameters": {}},
    ]
    c["beam"]["n_particles"] = 2000
    c["space_charge"]["enabled"] = True
    c["space_charge"]["mesh"] = [33, 33, 33]
    c["space_charge"]["step"] = 1
    c["output"]["step_size_m"] = 0.005
    c["output"]["z_diagnostics_mm"] = list(PROBES)
    return c


def main():
    print("=" * 70)
    print("  Repair 3: saved output carries probe positions + SC state")
    print("=" * 70)
    ok = True
    c = test_cfg()

    saved_cfg, saved_sw = gpt.cfg, gpt.switches
    saved_argv = sys.argv
    gpt.cfg = c
    gpt.switches = c["physics_switches"]
    sys.argv = ["ued_beamline_v2.py"]
    tmpdir = tempfile.mkdtemp(prefix="gpt_out_")
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            path = gpt.main(out_dir=tmpdir)
        data = load_results(path)
    finally:
        gpt.cfg, gpt.switches = saved_cfg, saved_sw
        sys.argv = saved_argv

    print(f"  saved -> {path}")
    probes = {float(p["z_mm"]): p for p in data["probes"]}
    meta = data.get("meta", {})

    # ── 1. probe position markers survive serialization ──
    z0 = probes.get(0.0)
    zp = probes.get(20.0)
    mid = probes.get(22.0)
    smp = probes.get(Z_SAMPLE_MM)
    struct_ok = all(x is not None for x in (z0, zp, mid, smp))
    fields_ok = struct_ok and all("z_actual_mm" in x and "z_exact" in x
                                  for x in (z0, zp, mid, smp))
    ok &= fields_ok
    print(f"  1. probe records present with z_actual_mm/z_exact: "
          f"{fields_ok} {'PASS' if fields_ok else 'FAIL'}")

    # ── 2. z0 exact, sample exact, mid probe flagged ──
    z0_ok = struct_ok and z0["z_exact"] is True \
        and abs(z0["z_actual_mm"] - 0.0) < 1e-9
    smp_ok = (struct_ok and smp["z_exact"] is True
              and abs(smp["z_actual_mm"] - Z_SAMPLE_MM) < 1e-9)
    mid_ok = (struct_ok and mid["z_exact"] is False
              and abs(mid["z_actual_mm"] - 25.0) < 1e-9      # step end
              and abs(mid["z_mm"] - 22.0) < 1e-9)            # nominal kept
    ok &= (z0_ok and smp_ok and mid_ok)
    print(f"  2a. z0 exact={z0['z_exact'] if z0 else None} "
          f"actual={z0['z_actual_mm'] if z0 else None}  "
          f"{'PASS' if z0_ok else 'FAIL'}")
    print(f"  2b. sample ({Z_SAMPLE_MM:.0f} mm) exact="
          f"{smp['z_exact'] if smp else None} actual="
          f"{smp['z_actual_mm'] if smp else None}  "
          f"{'PASS' if smp_ok else 'FAIL'}")
    print(f"  2c. non-aligned 22 mm probe: z_exact={mid['z_exact'] if mid else None} "
          f"z_actual_mm={mid['z_actual_mm'] if mid else None} "
          f"(nominal {mid['z_mm'] if mid else None})  "
          f"{'PASS' if mid_ok else 'FAIL'}")

    # ── 3. trajectory really reaches the sample plane ──
    hist_z = data["history"]["z_mm"]
    reach_ok = abs(hist_z[-1] - Z_SAMPLE_MM) < 1e-9
    ok &= reach_ok
    print(f"  3. history final z = {hist_z[-1]:.6f} mm (sample "
          f"{Z_SAMPLE_MM:.6f}) — coverage asserted BEFORE using the sample "
          f"value  {'PASS' if reach_ok else 'FAIL'}")

    # ── 4. saved sc_enabled == runtime effective, SC state persisted ──
    cons_ok = (data.get("sc_enabled") is True
               and meta.get("sc_effective") is True
               and meta.get("sc_requested") is True)
    sc_fields = ("sc_scheduler", "sc_apply_count", "sc_coverage_start_m",
                 "sc_coverage_stop_m", "sc_available", "sc_configured",
                 "sc_attached")
    sc_ok = all(k in meta for k in sc_fields)
    cov_ok = (sc_ok and abs(meta["sc_coverage_start_m"]) < 1e-9
              and abs(meta["sc_coverage_stop_m"] - Z_SAMPLE) < 1e-9
              and meta["sc_apply_count"] > 0)
    ok &= (cons_ok and cov_ok)
    print(f"  4a. saved sc_enabled={data.get('sc_enabled')} == effective="
          f"{meta.get('sc_effective')}, requested={meta.get('sc_requested')}  "
          f"{'PASS' if cons_ok else 'FAIL'}")
    print(f"  4b. persisted SC state: " +
          ", ".join(f"{k}={meta.get(k)}" for k in sc_fields) +
          f"  {'PASS' if cov_ok else 'FAIL'}")

    # ── 5. rf_kicks_applied from actual execution ──
    rf_ok = meta.get("rf_kicks_applied") == 1
    ok &= rf_ok
    print(f"  5. rf_kicks_applied={meta.get('rf_kicks_applied')} "
          f"(instances scheduled={meta.get('rf_instances_scheduled')})  "
          f"{'PASS' if rf_ok else 'FAIL'}")

    # cleanup temp dir
    for f in os.listdir(tmpdir):
        os.remove(os.path.join(tmpdir, f))
    os.rmdir(tmpdir)

    print(f"\n  Repair 3 saved output: {'ALL PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
