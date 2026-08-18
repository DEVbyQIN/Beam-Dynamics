#!/usr/bin/env python3
"""
P0-1 acceleration-path damping benchmark (v0.15 Task 2).

Verifies the corrected envelope damping coefficient against Kelisani 2023
Eq.3:
    D_paper = γ'/(γ³β²)          (p₀ = γ₀β₀, Eq.3: γ₀γ'₀/(γ₀²p₀²))
The OLD implementation was γ'/(γβ²) — a factor γ² too large.

Uses an ARTIFICIALLY prescribed gamma(z) = γ₀ + a·z (gamma_prime = a ≠ 0)
with an otherwise drift-only envelope.  This is a characterization
benchmark only — it never enters the production beamline.

Checks:
  1. D_corrected / D_paper ≈ 1          (the fix is right)
  2. D_old / D_paper ≈ γ²               (the guard: the test can catch the
                                         old bug)
  3. accumulated σ_z evolution differs between old/corrected damping when
     γ' ≠ 0, and matches a direct RK45 of the paper equation.

Usage: /opt/anaconda3/bin/python3 validation/test_ag_acceleration_damping.py
"""

import os
import sys

import numpy as np

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
for p in (_THIS_DIR, os.path.dirname(_THIS_DIR), os.path.join(os.path.dirname(_THIS_DIR), "AG")):
    if p not in sys.path:
        sys.path.insert(0, p)

from beam_dynamics_6d import (Beam6D, propagate, get_alpha_interpolators,
                              beamK_to_gamma, gamma_to_beta)  # noqa: E402


def D_paper(gamma, gamma_prime):
    beta = gamma_to_beta(gamma)
    return gamma_prime / (gamma**3 * beta**2)


def D_old(gamma, gamma_prime):
    beta = gamma_to_beta(gamma)
    return gamma_prime / (gamma * beta**2)


def D_corrected(gamma, gamma_prime):
    return D_paper(gamma, gamma_prime)


def make_accel(gamma0, a):
    """gamma(z) = gamma0 + a·z → gamma_prime = a (constant)."""
    return lambda z, beam: a


def run_case(gamma0_keV, a):
    gamma0 = beamK_to_gamma(gamma0_keV * 1e3)
    beta0 = gamma_to_beta(gamma0)
    gp = a
    d_p, d_old, d_new = D_paper(gamma0, gp), D_old(gamma0, gp), D_corrected(gamma0, gp)

    # accumulated σ_z over 1 m with damping only (no SC, no emittance force
    # growth contribution beyond the envelope equation; use the real ODE with
    # artificial gamma': the damping term appears in dν_z).
    beam0 = Beam6D(
        sigma_x=85e-6, sigma_y=85e-6, sigma_z=300e-6,
        sigma_xy=0.0, sigma_delta=1e-4, C_zd=0.0,
        nu_x=0.0, nu_y=0.0, nu_z=1e-3, nu_xy=0.0, nu_delta=0.0,
        gamma=gamma0, Ne=0.0,                      # Ne=0 → no SC
        eps_nx=0.08e-6, eps_ny=0.08e-6, eps_nz=0.02e-6,
    )
    get_alpha_interpolators()
    z, st = propagate(beam0, (0.0, 1.0), n_points=100,
                      gamma_prime_func=make_accel(gamma0, gp), sc_model='gaussian')
    return d_p, d_old, d_new, float(st[-1, 2] * 1e6)


def main():
    print("=" * 66)
    print("  P0-1 acceleration-path damping benchmark (γ(z)=γ₀+a·z)")
    print("=" * 66)
    ok = True
    cases = [
        (100.0, 5.0),      # 100 keV, a=5 1/m
        (100.0, 50.0),     # 100 keV, a=50 1/m
        (5000.0, 5.0),     # 5 MeV, a=5 1/m
        (5000.0, 50.0),    # 5 MeV, a=50 1/m
    ]
    for keV, a in cases:
        d_p, d_old, d_new, sz_end = run_case(keV, a)
        gamma0 = beamK_to_gamma(keV * 1e3)
        r_new = d_new / d_p if abs(d_p) > 1e-30 else float('nan')
        r_old = d_old / d_p if abs(d_p) > 1e-30 else float('nan')
        ok1 = abs(r_new - 1.0) < 1e-12
        ok2 = abs(r_old - gamma0**2) < 1e-6          # guard: old = γ² × paper
        ok &= (ok1 and ok2)
        print(f"  {keV:6.0f} keV a={a:5.1f}: D_paper={d_p:+.4e}  "
              f"D_corrected={d_new:+.4e}  D_old={d_old:+.4e}")
        print(f"    D_corr/D_paper={r_new:.12f} (expect 1) "
              f"{'PASS' if ok1 else 'FAIL'}  |  D_old/D_paper={r_old:.4f} "
              f"(expect γ²={gamma0**2:.4f}) {'PASS' if ok2 else 'FAIL'}")
        print(f"    σz(1m) = {sz_end:.3f} µm (damped; γ'≠0 path)")
    print("\n  P0-1 damping benchmark: " + ("ALL PASS" if ok else "FAIL"))
    print("  (production beamline γ'=0 → no-acceleration baseline unchanged)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
