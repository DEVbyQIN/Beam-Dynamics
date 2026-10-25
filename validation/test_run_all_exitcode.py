#!/usr/bin/env python3
"""
A1 regression: run_all.py must return a reliable exit status.

Proves WITHOUT running expensive simulations (sub-tests are stubbed in
process):
  * all sub-tests succeed            → run_all.main() == 0
  * any single sub-test fails        → run_all.main() != 0
  * a sub-test raising an exception  → run_all.main() != 0 (never PASS)

Usage: /opt/anaconda3/bin/python3 validation/test_run_all_exitcode.py
"""

import io
import os
import sys
import contextlib

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
for p in (_THIS_DIR, os.path.dirname(_THIS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import validation.run_all as ra  # noqa: E402

# (module attribute name in validation/run_all.py, display label)
SUBTESTS = (("test_config_consistency", "config_schema"),
            ("test_drift", "drift"),
            ("test_solenoid", "solenoid"),
            ("test_rf", "rf"),
            ("test_full_beamline", "full_beamline"),
            ("test_gpt_route_equivalence", "gpt_route"),
            ("test_runner_contract", "runner_contract"),
            ("test_ag_longitudinal_state", "ag_longitudinal"),
            ("test_ag_transverse_g","ag_transverse_g"),
            ("test_shared_diagnostics_rf","diagnostics_rf"),
            ("test_ag_alpha_numerics","alpha_numerics"),
            ("test_ocelot_transport","ocelot_transport"))


class Stub:
    """Minimal stand-in for a sub-test module (has .main())."""

    def __init__(self, rc=0, exc=None):
        self.rc = rc
        self.exc = exc

    def main(self):
        if self.exc is not None:
            raise self.exc
        return self.rc


def run_with(stubs):
    """Inject stubs into run_all's namespace, call main(), restore."""
    saved = {}
    for name, stub in stubs.items():
        saved[name] = getattr(ra, name)
        setattr(ra, name, stub)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rc = ra.main()
    finally:
        for name, obj in saved.items():
            setattr(ra, name, obj)
    return rc


def main():
    print("=" * 66)
    print("  A1 regression: run_all exit-status reliability")
    print("=" * 66)
    ok = True

    # 1. all success → 0
    rc = run_with({n: Stub(0) for n, _ in SUBTESTS})
    good = (rc == 0)
    print(f"  all sub-tests success        → rc={rc} (expect 0) "
          f"{'PASS' if good else 'FAIL'}")
    ok &= good

    # 2. each single failure → non-zero
    for fail_name, label in SUBTESTS:
        stubs = {n: Stub(0) for n, _ in SUBTESTS}
        stubs[fail_name] = Stub(1)
        rc = run_with(stubs)
        good = (rc != 0)
        print(f"  {label:<13s} fails        → rc={rc} (expect !=0) "
              f"{'PASS' if good else 'FAIL'}")
        ok &= good

    # 3. exception must NOT become PASS
    stubs = {n: Stub(0) for n, _ in SUBTESTS}
    stubs["test_drift"] = Stub(exc=RuntimeError("injected failure"))
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        rc = run_with(stubs)
    good = (rc != 0)
    print(f"  drift raises exception       → rc={rc} (expect !=0) "
          f"{'PASS' if good else 'FAIL'}")
    ok &= good

    # 4. sanity: run_all module really exposes the stubs' names
    names_ok = all(hasattr(ra, n) for n, _ in SUBTESTS)
    print(f"  run_all exposes all sub-test names: {names_ok} "
          f"{'PASS' if names_ok else 'FAIL'}")
    ok &= names_ok

    print(f"\n  A1 exit-status regression: "
          f"{'ALL PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
