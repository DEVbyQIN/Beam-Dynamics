"""Constraints for AG's constant-reference, first-order longitudinal state.

Coordinates: zeta [m], delta_p = dp/p0 [1], s [m], head-positive zeta.
This module diagnoses redundant states; it does not project or evolve them.
See longitudinal_state_physics_note.md for the emittance convention.
"""
import math
import warnings


class LongitudinalStateWarning(UserWarning):
    """A realizable covariance disagrees with the saved AG envelope state."""


def inspect_longitudinal_state(beam, *, rtol=1e-8):
    """Return JSON-safe diagnostics without changing the beam.

    Nonfinite/unphysical inputs raise ValueError. Constraint agreement uses
    relative tolerance only, without a unit-dependent absolute floor.
    A negative determinant within 64 float eps of the product variance is
    identified explicitly as roundoff; larger PSD violations are rejected.
    """
    if not math.isfinite(rtol) or rtol < 0:
        raise ValueError("longitudinal rtol must be finite and nonnegative")
    names = ("sigma_z", "sigma_delta", "C_zd", "nu_z", "eps_nz", "gamma")
    values = {name: float(getattr(beam, name)) for name in names}
    for name, value in values.items():
        if not math.isfinite(value):
            raise ValueError(f"AG longitudinal {name} must be finite")
    sigma, delta, C = values["sigma_z"], values["sigma_delta"], values["C_zd"]
    gamma, epsilon = values["gamma"], values["eps_nz"]
    if sigma <= 0:
        raise ValueError("AG longitudinal sigma_z must be positive [m]")
    if delta < 0 or epsilon < 0:
        raise ValueError("AG longitudinal sigma_delta and eps_nz must be nonnegative")
    if gamma <= 1:
        raise ValueError("AG longitudinal gamma must exceed 1")

    product = sigma * delta
    if not math.isfinite(product):
        raise ValueError("AG longitudinal covariance scale overflow")
    if product == 0:
        if C != 0:
            raise ValueError("AG longitudinal covariance is not positive semidefinite: C_zd != 0 at zero spread")
        rho, normalized_det = 0.0, 0.0
    else:
        rho = C / product
        normalized_det = 1.0 - rho * rho
        if not math.isfinite(normalized_det) or normalized_det < -64 * math.ulp(1.0):
            raise ValueError("AG longitudinal covariance is not positive semidefinite: C_zd^2 > sigma_z^2*sigma_delta^2")
    roundoff_limited = normalized_det < 0
    # Only a documented floating-point PSD boundary may use zero here.
    determinant = product * product * normalized_det
    p_normalized = math.sqrt((gamma - 1) * (gamma + 1))
    epsilon_cov = p_normalized * product * math.sqrt(0.0 if roundoff_limited else normalized_det)
    nu_cov = C / (gamma * gamma * sigma)
    C_envelope = gamma * gamma * sigma * values["nu_z"]
    epsilon_scale = max(epsilon, epsilon_cov)
    epsilon_error = abs(epsilon - epsilon_cov) / epsilon_scale if epsilon_scale else 0.0
    C_scale = max(abs(C), abs(C_envelope))
    C_error = abs(C - C_envelope) / C_scale if C_scale else 0.0
    derived = (determinant, epsilon_cov, nu_cov, C_envelope, epsilon_error, C_error)
    if not all(math.isfinite(v) for v in derived):
        raise ValueError("AG longitudinal derived diagnostic overflow")
    return {
        "coordinate": "zeta_head_positive_m, delta_p=dp/p0",
        "scope": "constant_reference_first_order_kinematics",
        "epsilon_definition": "beta*gamma*sqrt(sigma_z^2*sigma_delta^2-C_zd^2)",
        "epsilon_unit": "m (1 mm.mrad = 1e-6 m)",
        "epsilon_input_mm_mrad": epsilon * 1e6,
        "epsilon_from_covariance_mm_mrad": epsilon_cov * 1e6,
        "nu_input": values["nu_z"], "nu_from_covariance": nu_cov,
        "C_input_m": C, "C_from_envelope_m": C_envelope,
        "determinant_m2": determinant, "correlation_coefficient": rho,
        "psd_roundoff_limited": roundoff_limited,
        "epsilon_relative_mismatch": epsilon_error,
        "correlation_relative_mismatch": C_error,
        "rtol": rtol,
        "consistent": epsilon_error <= rtol and C_error <= rtol,
    }


def check_initial_longitudinal_state(beam, *, policy="warn"):
    """Check a formal initial state; warn or fail on redundant-state mismatch.

    Both policies reject impossible input. 'warn' preserves historical input
    while exposing the mismatch; 'error' permits only a consistent initial
    state. Neither policy chooses an authoritative physical input.
    """
    if policy not in ("warn", "error"):
        raise ValueError("longitudinal_check must be 'warn' or 'error'")
    report = inspect_longitudinal_state(beam)
    report["policy"] = policy
    if not report["consistent"]:
        message = (
            "AG longitudinal initial state is inconsistent: "
            f"eps_nz={report['epsilon_input_mm_mrad']:.12g} mm.mrad, "
            f"beta*gamma*sqrt(sigma_z^2*sigma_delta^2-C_zd^2)="
            f"{report['epsilon_from_covariance_mm_mrad']:.12g} mm.mrad; "
            f"nu_z={report['nu_input']:.12g}, "
            f"C_zd/(gamma^2*sigma_z)={report['nu_from_covariance']:.12g}. "
            "Inputs were not changed; choose the physical input priority before correction."
        )
        if policy == "error":
            raise ValueError(message)
        warnings.warn(message, LongitudinalStateWarning, stacklevel=2)
    return report


def history_diagnostics(states):
    """Expose AG-only longitudinal diagnostics, in explicitly named units.

    sigma_delta and C are derived columns of the formal solver history.
    Compute emittance from these moments, not from an input constant.
    """
    import numpy as np
    st = np.asarray(states, dtype=float)
    sigma, delta, C, nu, gamma = st[:, 2], st[:, 4], st[:, 5], st[:, 8], st[:, 11]
    theta = delta / gamma**2
    # A product of sum/difference loses fewer digits than theta²-nu².
    intrinsic = (theta - np.abs(nu)) * (theta + np.abs(nu))
    boundary = intrinsic < 0
    roundoff = 64*np.finfo(float).eps*np.maximum(theta**2, nu**2)
    if np.any(intrinsic < -roundoff) or not np.isfinite(st).all():
        raise ValueError("AG history has an invalid longitudinal covariance")
    # Only the resolved floating-point boundary is treated as zero. Report
    # its count, so this cannot hide a finite negative physical variance.
    intrinsic = np.where(boundary, 0., intrinsic)
    geometric = sigma * np.sqrt(intrinsic)
    eps_np = np.sqrt((gamma - 1)*(gamma + 1)) * gamma**2 * geometric
    C_expected = gamma**2 * sigma * nu
    scale = np.maximum(np.abs(C), np.abs(C_expected))
    residual = np.divide(np.abs(C-C_expected), scale,
                         out=np.zeros_like(scale), where=scale > 0)
    return {
        "C_zdelta_m": C.tolist(), "nu_z": nu.tolist(), "theta_z": theta.tolist(),
        "chirp_per_m": (C / sigma**2).tolist(),
        "epsilon_geometric_z_zprime_m": geometric.tolist(),
        "epsilon_normalized_z_delta_mm_mrad": (eps_np*1e6).tolist(),
        "max_correlation_constraint_relative_error": float(np.max(residual)),
        "psd_roundoff_boundary_samples": int(np.count_nonzero(boundary)),
    }
