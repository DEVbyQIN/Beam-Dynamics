#!/usr/bin/env python3
"""
Run the full validation suite (drift, solenoid, rf) and print a summary.

Usage:  python3 validation/run_all.py

Exit status (v0.15 hardening):
  0  — every sub-test returned success
  1  — at least one sub-test failed OR raised an exception
       (an exception is NEVER converted into a PASS)

The per-test summary is always printed.
"""

import os
import sys
import traceback

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
for p in (_THIS_DIR, os.path.dirname(_THIS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from validation import (test_config_consistency, test_drift, test_solenoid,  # noqa: E402
                        test_rf, test_full_beamline, test_gpt_route_equivalence,
                        test_runner_contract, test_ag_longitudinal_state,
                        test_ag_transverse_g,test_shared_diagnostics_rf,
                        test_ag_alpha_numerics,test_ocelot_transport)


def main():
    print("=" * 66)
    print("  UED framework validation suite  (AG vs OCELOT)")
    print("=" * 66)

    results = {}
    for name, mod in (("config_schema", test_config_consistency),
                      ("drift", test_drift), ("solenoid", test_solenoid),
                      ("rf", test_rf), ("full_beamline", test_full_beamline),
                      ("gpt_route", test_gpt_route_equivalence),
                      ("runner_contract", test_runner_contract),
                      ("ag_longitudinal", test_ag_longitudinal_state),
                      ("ag_transverse_g",test_ag_transverse_g),
                      ("diagnostics_rf",test_shared_diagnostics_rf),
                      ("alpha_numerics",test_ag_alpha_numerics),
                      ("ocelot_transport",test_ocelot_transport)):
        print("\n" + "#" * 66)
        print(f"  TEST: {name}")
        print("#" * 66)
        try:
            rc = mod.main()
        except SystemExit as e:              # a sub-test may sys.exit()
            rc = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
            print(f"  [{name}] SystemExit({e.code!r})", file=sys.stderr)
        except Exception:
            # An exception is a FAILURE — never silently turned into PASS.
            traceback.print_exc()
            rc = 1
        results[name] = 0 if rc == 0 else 1

    print("\n" + "=" * 66)
    print("  SUMMARY")
    print("=" * 66)
    labels = {"config_schema": "Level-1 config consistency",
              "drift": "transverse+σ_z",
              "solenoid": "coupling resolved",
              "rf": "thin-lens; σ_z R56 resolved",
              "full_beamline": "registered beamline comparisons; not full SC physical certification",
              "gpt_route": "lattice single-source equivalence",
              "runner_contract": "CLI/backend use identical execution",
              "ag_longitudinal": "paper Gz, covariance, SC-to-RF invariants",
              "ag_transverse_g":"paper Gx/Gy, state transfer and linear invariants",
              "diagnostics_rf":"formal diagnostics, independent time/field RF references",
              "alpha_numerics":"direct SC coefficients, independent references and domain failure",
              "ocelot_transport":"active methods, independent drift/linear solenoid references and saved metadata"}
    for name, rc in results.items():
        verdict = "PASS" if rc == 0 else "FAIL"
        print(f"  {name:<13s} {verdict}  ({labels.get(name, '')})")
    all_ok = all(rc == 0 for rc in results.values())
    print(f"\n  OVERALL: {'PASS' if all_ok else 'FAIL'}")
    print(f"\n  reports -> {os.path.join(_THIS_DIR, 'reports')}")
    print(f"  checkpoints -> {os.path.join(_THIS_DIR, 'CHECKPOINTS.md')}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
