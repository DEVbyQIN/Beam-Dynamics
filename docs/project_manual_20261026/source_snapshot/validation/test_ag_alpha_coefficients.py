#!/usr/bin/env python3
"""
P0-2 alpha coefficient regression (v0.15 Task 2).

Directly tests the α coefficient integrals against the Kelisani 2023
paper definitions (Eq.21-29), independent of the full beamline:

  αx  = ∫ kx²s/√((s²+kx²)³(s²+ky²)(s²+1)) ds            (Eq.21)
  αy  = ∫ ky²s/√((s²+kx²)(s²+ky²)³(s²+1)) ds            (Eq.22)
  αz  = ∫ kxky s/√((s²+kx²)(s²+ky²)(s²+1)³) ds          (Eq.23)
  αxx = ∫ 3kx⁴s/[2√((s²+kx²)⁵(s²+ky²)(s²+1))] ds       (Eq.24, 1/2!)
  αyy = ∫ 3ky⁴s/[2√((s²+kx²)(s²+ky²)⁵(s²+1))] ds       (Eq.25, 1/2!)
  ... αzz (Eq.26), αxy (Eq.27), αxz (Eq.28), αyz (Eq.29)

Checks:
  1. kx=ky=1: αx=αy=αz=1/3 (analytic sphere), αxx=αyy=3/10 (post-fix),
     and αxx_old/αxx_corrected = 2 (guard)
  2. kx=4.371, ky=8.742 and kx=1, ky=3: code vs direct numerical integral
     of the paper equations (relative error ~1e-6)
  3. symmetry: αxx(kx,ky)=αyy(ky,kx), αx(kx,ky)=αy(ky,kx)

Usage: /opt/anaconda3/bin/python3 validation/test_ag_alpha_coefficients.py
"""

import os
import sys

import numpy as np
from scipy.integrate import quad

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
for p in (_THIS_DIR, os.path.dirname(_THIS_DIR), os.path.join(os.path.dirname(_THIS_DIR), "AG")):
    if p not in sys.path:
        sys.path.insert(0, p)

from beam_dynamics_6d import compute_all_alpha  # noqa: E402


def paper_axx(kx, ky):
    """Direct numerical integral of the paper Eq.24 (with 1/2)."""
    f = lambda s: 3.0 * kx**4 * s / (
        2.0 * np.sqrt((s**2 + kx**2)**5 * (s**2 + ky**2) * (s**2 + 1.0)))
    return quad(f, 0.0, np.inf, limit=200)[0]


def paper_ayy(kx, ky):
    f = lambda s: 3.0 * ky**4 * s / (
        2.0 * np.sqrt((s**2 + kx**2) * (s**2 + ky**2)**5 * (s**2 + 1.0)))
    return quad(f, 0.0, np.inf, limit=200)[0]


def main():
    print("=" * 66)
    print("  P0-2 alpha coefficient regression (paper Eq.21-29)")
    print("=" * 66)
    ok = True

    # ── 1. kx = ky = 1: analytic values ──
    a = compute_all_alpha(1.0, 1.0)
    ok1 = (abs(a['x'] - 1/3) < 1e-9 and abs(a['y'] - 1/3) < 1e-9
           and abs(a['z'] - 1/3) < 1e-9)
    ok2 = abs(a['xx'] - 0.3) < 1e-9 and abs(a['yy'] - 0.3) < 1e-9
    # guard: old implementation would give 0.6 = 2 × 0.3
    print(f"  kx=ky=1: αx=αy=αz={a['x']:.9f} (expect 1/3) {'PASS' if ok1 else 'FAIL'}")
    print(f"          αxx=αyy={a['xx']:.9f} (expect 3/10 post-fix; "
          f"old=0.6 → ratio 2) {'PASS' if ok2 else 'FAIL'}")
    ok &= ok1 and ok2

    # ── 2. code vs direct paper integral ──
    for kx, ky in ((4.371, 8.742), (1.0, 3.0), (0.5, 2.0)):
        a = compute_all_alpha(kx, ky)
        pxx, pyy = paper_axx(kx, ky), paper_ayy(kx, ky)
        rxx = abs(a['xx'] - pxx) / pxx
        ryy = abs(a['yy'] - pyy) / pyy
        ok3 = rxx < 1e-5 and ryy < 1e-5
        ok &= ok3
        print(f"  kx={kx:.3f} ky={ky:.3f}: code αxx={a['xx']:.9f} "
              f"paper={pxx:.9f} rel={rxx:.2e}  |  αyy={a['yy']:.9f} "
              f"paper={pyy:.9f} rel={ryy:.2e}  {'PASS' if ok3 else 'FAIL'}")

    # ── 3. symmetry ──
    a_xy = compute_all_alpha(1.0, 3.0)
    a_yx = compute_all_alpha(3.0, 1.0)
    s1 = abs(a_xy['xx'] - a_yx['yy']) < 1e-9     # αxx(kx,ky)=αyy(ky,kx)
    s2 = abs(a_xy['x'] - a_yx['y']) < 1e-9
    s3 = abs(a_xy['xz'] - a_yx['yz']) < 1e-9
    ok &= (s1 and s2 and s3)
    print(f"  symmetry αxx(kx,ky)=αyy(ky,kx): {s1}  αx(kx,ky)=αy(ky,kx): {s2}  "
          f"αxz=αyz: {s3}  {'PASS' if (s1 and s2 and s3) else 'FAIL'}")

    print("\n  P0-2 alpha regression: " + ("ALL PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
