#!/usr/bin/env python3
"""
P0-1 acceleration-path damping benchmark (v0.15 Task 2 / hardened in the
entrypoint-hardening phase).

The damping coefficient is now measured FROM THE PRODUCTION RHS
(`beam_dynamics_6d.envelope_ode`), not from a test-local copy of the formula:

    dν_u/dz = −D·ν_u + (F forces)          (envelope_ode, u = x, y, z)

so the measured D is obtained by differencing the production right-hand side
with and without γ′ at the SAME state:

    Δ(dν_u) = −D_measured · ν_u      →      D_measured = −Δ(dν_u)/ν_u

and compared against the paper reference (Kelisani 2023 Eq.3, p₀=γ₀β₀):

    D_paper = γ′ / (γ³ β²)

Checks:
  1. D_measured / D_paper ≈ 1 for three axes, two energies, two non-zero γ′
     (nu_u ≠ 0 so the test cannot pass vacuously) at TOL_REL = 1e-12.
  2. RECOVERABLE FAULT INJECTION: the PRE-FIX coefficient γ′/(γβ²) is injected
     in-process into the production RHS — built from the live
     `envelope_ode` source text, installed by monkeypatching the module
     attribute, and always removed again in `finally`.  The test then shows
     that its OWN criterion (|ratio − 1| < TOL_REL) FAILS on the injected
     build, i.e. the check really discriminates the old bug instead of merely
     comparing two closed-form expressions.  The production file is never
     modified and the restored production RHS is verified bit-identical.
  3. Accumulated σ_z over an artificial γ(z)=γ₀+a z drift (characterization).

Usage: /opt/anaconda3/bin/python3 validation/test_ag_acceleration_damping.py
"""

import inspect
import os
import sys
import textwrap

import numpy as np

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
for p in (_THIS_DIR, os.path.dirname(_THIS_DIR), os.path.join(os.path.dirname(_THIS_DIR), "AG")):
    if p not in sys.path:
        sys.path.insert(0, p)

import beam_dynamics_6d as bd6  # noqa: E402
from beam_dynamics_6d import (Beam6D, propagate,  # noqa: E402
                              get_alpha_interpolators, beamK_to_gamma,
                              gamma_to_beta)

NU_TEST = 1e-3          # non-zero envelope slope (avoid a vacuous test)
TOL_REL = 1e-12         # production vs paper (pure float arithmetic)


def D_paper(gamma, gamma_prime):
    """Kelisani 2023 Eq.3, with p0 = gamma*beta."""
    beta = gamma_to_beta(gamma)
    return gamma_prime / (gamma**3 * beta**2)


def make_beam(gamma0_keV):
    gamma0 = beamK_to_gamma(gamma0_keV * 1e3)
    beam = Beam6D(
        sigma_x=85e-6, sigma_y=85e-6, sigma_z=300e-6,
        sigma_xy=0.0, sigma_delta=1e-4, C_zd=0.0,
        nu_x=NU_TEST, nu_y=NU_TEST, nu_z=NU_TEST, nu_xy=0.0, nu_delta=0.0,
        gamma=gamma0, Ne=0.0,                      # Ne=0 → no SC
        eps_nx=0.08e-6, eps_ny=0.08e-6, eps_nz=0.02e-6,
    )
    # The nonzero envelope slope used to measure D must describe the same
    # covariance as C and sigma_delta. Keep NU_TEST, D_paper and TOL_REL;
    # repair the formerly inconsistent synthetic fixture, not the criterion.
    beam.C_zd = beam.gamma**2 * beam.sigma_z * beam.nu_z
    beam.sigma_delta = np.sqrt((beam.gamma**2*beam.nu_z)**2
        + (beam.eps_nz/(beam.p0*beam.sigma_z))**2)
    return beam


def production_rhs(beam, gamma_prime_value, rhs=None):
    """Call the PRODUCTION envelope RHS at a fixed state with a chosen γ′.

    The RHS is resolved through the MODULE attribute (`bd6.envelope_ode`) at
    call time, so a monkeypatched fault-injected build is really exercised by
    the same measurement code that measures production.
    """
    y = np.append(beam.state_vector(), beam.gamma)
    return (rhs or bd6.envelope_ode)(
        0.0, y, beam.Ne, beam.eps_nx, beam.eps_ny, beam.eps_nz,
        external_force_func=None,
        gamma_prime_func=(lambda z, b: gamma_prime_value),
        rf_chirp_func=None, sc_model='gaussian')


def measure_D(beam, gamma_prime_value, rhs=None):
    """Isolate the damping contribution from the production RHS.

    dν_u appears at indices 6,7,8 of the RHS vector; all other terms do not
    depend on γ′ (verified: γ′ enters only the damping coefficient and the
    returned γ′ slot).  Δ(dν_u) = −D·ν_u.
    """
    d_with = production_rhs(beam, gamma_prime_value, rhs)
    d_without = production_rhs(beam, 0.0, rhs)
    delta = d_with - d_without
    return np.array([-delta[6] / NU_TEST,
                     -delta[7] / NU_TEST,
                     -delta[8] / NU_TEST])


# ── recoverable fault injection ──────────────────────────────────────────
FIXED_COEFF_SRC = "damping_coeff = gamma_prime / (gamma**3 * beta**2)"
OLD_COEFF_SRC = "damping_coeff = gamma_prime / (gamma * beta**2)"


def make_old_damping_rhs():
    """Derive the PRE-FIX RHS from the LIVE production source text.

    Returns (faulty_rhs, n_anchors).  The production file is not touched: the
    source of the current `envelope_ode` is read, the single damping
    coefficient line is replaced by the pre-fix one, and the result is exec'd
    in a namespace that SHARES the production module globals (so every helper
    is the production one).  n_anchors != 1 means the production source no
    longer matches the documented formula → the injection is invalid and the
    guard must FAIL loudly instead of testing nothing.
    """
    src = textwrap.dedent(inspect.getsource(bd6.envelope_ode))
    n_anchors = src.count(FIXED_COEFF_SRC)
    ns = dict(bd6.__dict__)
    exec(compile(src.replace(FIXED_COEFF_SRC, OLD_COEFF_SRC),
                 "<fault_injection:old_damping>", "exec"), ns)
    return ns["envelope_ode"], n_anchors


def main():
    print("=" * 66)
    print("  P0-1 damping benchmark — measured from PRODUCTION envelope_ode")
    print("=" * 66)
    get_alpha_interpolators()
    ok = True
    cases = [
        (100.0, 5.0),      # 100 keV, γ′=5 1/m
        (100.0, 50.0),     # 100 keV, γ′=50 1/m
        (5000.0, 5.0),     # 5 MeV, γ′=5 1/m
        (5000.0, 50.0),    # 5 MeV, γ′=50 1/m
    ]
    for keV, gp in cases:
        beam = make_beam(keV)
        gamma0 = beam.gamma
        d_p = D_paper(gamma0, gp)
        d_meas = measure_D(beam, gp)                 # (Dx, Dy, Dz) from production
        ratios = d_meas / d_p
        ok1 = np.all(np.abs(ratios - 1.0) < TOL_REL)
        ok &= ok1
        print(f"  {keV:6.0f} keV γ′={gp:5.1f}: D_paper={d_p:+.6e}  "
              f"D_meas(x,y,z)=({d_meas[0]:+.6e},{d_meas[1]:+.6e},{d_meas[2]:+.6e})")
        print(f"      D_meas/D_paper = ({ratios[0]:.12f},{ratios[1]:.12f},"
              f"{ratios[2]:.12f}) (expect 1, tol {TOL_REL:g}) "
              f"{'PASS' if ok1 else 'FAIL'}  "
              f"max|ratio-1|={np.max(np.abs(ratios - 1.0)):.2e}")

    # ── GUARD: recoverable in-process fault injection ──
    # The pre-fix coefficient is injected into the PRODUCTION RHS (see
    # make_old_damping_rhs) and the test's OWN criterion is re-evaluated on the
    # injected build.  It must FAIL, otherwise this test cannot discriminate
    # the old bug.  The injection is removed in `finally`.
    print("\n  GUARD — recoverable fault injection of the pre-fix coefficient "
          "γ′/(γβ²):")
    beam = make_beam(100.0)
    gp_inj = 5.0
    gamma0 = beam.gamma
    d_p = D_paper(gamma0, gp_inj)
    ratios_ref = measure_D(beam, gp_inj) / d_p          # production, before
    faulty_rhs, n_anchors = make_old_damping_rhs()
    produced = bd6.envelope_ode
    try:
        bd6.envelope_ode = faulty_rhs
        ratios_fault = measure_D(beam, gp_inj) / d_p
    finally:
        bd6.envelope_ode = produced                     # ALWAYS restored
    ratios_after = measure_D(beam, gp_inj) / d_p        # production, after

    anchor_ok = (n_anchors == 1)
    injected_ok = anchor_ok and np.all(
        np.abs(ratios_fault - gamma0**2) < 1e-9 * gamma0**2)   # ratio = γ²
    detected = anchor_ok and np.any(np.abs(ratios_fault - 1.0) >= TOL_REL)
    recovered = np.array_equal(ratios_after, ratios_ref)
    guard_ok = anchor_ok and injected_ok and detected and recovered
    ok &= guard_ok
    print(f"      injection anchor found exactly once: {anchor_ok} "
          f"(n={n_anchors})")
    print(f"      injected D_meas/D_paper = ({ratios_fault[0]:.9f},"
          f"{ratios_fault[1]:.9f},{ratios_fault[2]:.9f})  "
          f"expect γ₀²={gamma0**2:.9f}  {'PASS' if injected_ok else 'FAIL'}")
    print(f"      this test's criterion on the injected build: "
          f"max|ratio-1|={np.max(np.abs(ratios_fault - 1.0)):.3e} vs tol "
          f"{TOL_REL:g} → would-be "
          f"{'FAIL (bug IS caught)' if detected else 'PASS (bug NOT caught!)'} "
          f"{'PASS' if detected else 'FAIL'}")
    print(f"      production RHS restored bit-identically after injection: "
          f"{recovered} {'PASS' if recovered else 'FAIL'}")

    # ── characterization: accumulated σ_z under γ(z)=γ₀+a z ──
    print("\n  characterization (σ_z over 1 m, artificial γ′≠0):")
    for keV, a in ((100.0, 5.0), (5000.0, 5.0)):
        beam0 = make_beam(keV)
        z, st = propagate(beam0, (0.0, 1.0), n_points=100,
                          gamma_prime_func=(lambda zz, b, _a=a: _a),
                          sc_model='gaussian')
        print(f"    {keV:6.0f} keV γ′={a}: σz(1m)={st[-1, 2] * 1e6:.3f} µm")

    print("\n  P0-1 damping benchmark: " + ("ALL PASS" if ok else "FAIL"))
    print("  (formal beamline has γ′=0; this check isolates D, not full accelerating-coordinate validity)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
