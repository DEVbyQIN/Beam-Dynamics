"""The single AG execution driver used by the CLI and validation adapters.

Assembly and diagnostics live here; existing envelope/force kernels are reused.
See runner_physics_note.md for coordinates, sampling and known physics limits.
"""
import sys
from pathlib import Path
import numpy as np

# The existing kernels use flat sibling imports. Keep one module identity.
_CORE_DIR = str(Path(__file__).resolve().parent)
if _CORE_DIR not in sys.path:
    sys.path.insert(0, _CORE_DIR)
from shared.params import parse, config_sha, _lattice_elements, z_sample
from shared.constants import C_SI, M_E_SI, E_SI
from shared.beam_physics import BeamReference
from shared.beam_result import BeamResult
from shared.run_contract import section_active_types, resolve_switches, provenance, rf_description
from beam_dynamics_6d import ExtFieldRegion
from AG.longitudinal_state import check_initial_longitudinal_state, inspect_longitudinal_state, history_diagnostics

def rf_thin_lens_H(cfg, rf_elem):
    from shared.rf_model import coefficients
    br = BeamReference.from_energy_keV(cfg["beam"]["energy_keV"])
    return coefficients(rf_elem,br.beta,br.gamma,br.gamma*M_E_SI*C_SI**2/E_SI)[0]


def build_regions(cfg):
    """Translate lattice.elements -> ExtFieldRegion list (lattice only).

    Only solenoids produce continuous Bz regions. RF roles are entrance
    events, not a second distributed force. Drift / markers need no region.
    """
    regions = []
    for e in cfg["lattice"]["elements"]:
        etype, z0, L = e["type"], e["z_start"], e["length"]
        if L <= 0:
            continue
        if etype == "solenoid":
            regions.append(ExtFieldRegion(z0, z0 + L, "solenoid",
                                          {"Bz": e["parameters"]["B_field_T"],
                                           "dBz_dz": 0.0}))
    return regions


def run_from_config(cfg, section="full", n_points=2000, sc_enabled=None,
                    solenoid_coupling=False, switches=None, sc_model=None,
                    longitudinal_check="warn"):
    """Drive the AG 6D envelope ODE through the section.

    RF is handled by the existing thin-lens model (see rf_thin_lens_H):
    the continuous cavity chirp is replaced by apply_rf_thin_lens(H) at the
    cavity entrance; the RF TRANSVERSE entrance kick follows the shared
    physics_switches (default OFF).

    sc_model : 'gaussian' (existing production default) or 'ellipsoid'.
    The Gx/Gy/Gz equations and state constraints are checked in the related
    Physics Notes; Gaussian closure is still an approximation to particle SC.
    longitudinal_check : 'warn' (preserve legacy inputs with a visible warning)
        or 'error' (reject inconsistent initial envelope/moment inputs).
    """
    from shared.geometry import validate_geometry
    geometry = validate_geometry(cfg)
    from beam_dynamics_6d import (make_beam_100keV, ExtFieldRegion,
                                  get_alpha_interpolators, record_evaluations, propagate,
                                  apply_rf_thin_lens, Beam6D)
    from external_forces import build_all_external

    if not isinstance(n_points, int) or n_points < 2:
        raise ValueError("AG n_points must be an integer >= 2")
    P = parse(cfg)
    ib = cfg["initial_distribution"]
    sc_enabled = cfg["space_charge"]["enabled"] if sc_enabled is None else sc_enabled
    sw = resolve_switches(cfg, switches)

    # v0.14.1 task 2 (AG charge semantics): the AG SC force is ∝ Ne·e
    # (beam_dynamics_6d.py:379 fb = η·Ne·e/(8π√π·ε₀)).  Ne must be the
    # PHYSICAL bunch charge Q/e — beam.n_particles is only the OCELOT
    # macroparticle numerical resolution.  (Previously Ne=n_particles=5e4
    # → 8 fC equivalent charge instead of the configured 100 fC: 12.5× too
    # weak.  SC OFF is unaffected: Ne is forced to 0.0 below.)
    ne_phys = abs(P.beam.Q_C) / E_SI

    beam0 = make_beam_100keV(
        Ne=ne_phys,
        beamK_eV=P.beam.energy_keV * 1e3,
        sigma_x0_um=ib["spot_rms_um"], sigma_y0_um=ib["spot_rms_um"],
        sigma_z0_um=ib["bunch_length_um"],
        sigma_delta=ib["sigma_delta"],
        eps_nx_um=ib["epsilon_n_mm_mrad"], eps_ny_um=ib["epsilon_n_mm_mrad"],
        eps_nz_um=P.beam.epsilon_nz_mm_mrad,
    )
    # User-selected authority (2026-10-16): shared size and momentum spread.
    # Keep the old YAML value as provenance, not a second physics input.
    epsilon_configured = ib.get("epsilon_nz_mm_mrad")
    beam0.eps_nz = inspect_longitudinal_state(beam0)[
        "epsilon_from_covariance_mm_mrad"] * 1e-6
    initial_longitudinal = check_initial_longitudinal_state(
        beam0, policy=longitudinal_check)
    initial_longitudinal.update(
        input_authority="shared_sigma_z_and_sigma_delta",
        epsilon_configured_mm_mrad=epsilon_configured,
        epsilon_configured_used=False)
    get_alpha_interpolators()

    active_types = section_active_types(section)
    active_cfg = dict(cfg, lattice=dict(cfg["lattice"], elements=[
        e for e in _lattice_elements(cfg) if e["type"] in active_types]))
    regions = build_regions(active_cfg)

    # Continuous solenoid fields; RF roles are both entrance events.
    regions_core = regions
    ef_core, gp_core, ch_core = build_all_external(regions_core)

    ef = ef_core

    if not solenoid_coupling and any(r.ftype == "solenoid" for r in regions_core):
        base = ef
        ef = (lambda z, beam, _base=base:
              _base(z, beam)[:3] + (0.0, 0.0, 0.0))

    # Preserve the frozen backend endpoint arithmetic (the sample marker may
    # differ by ~1e-16 m from z_start+length). Extend genuine trailing gaps.
    z_max = max(e["z_start"] + e["length"] for e in _lattice_elements(cfg)
                if e["length"] > 0)
    if z_sample(cfg) > z_max + 1e-12:
        z_max = z_sample(cfg)
    beam_k = beam0.copy()
    if not sc_enabled:
        beam_k.Ne = 0.0
    # v0.15 D-2: default SC model is GAUSSIAN (consistent with Gaussian
    # initial beam; not an assertion of universal PIC agreement). sc_model param
    # overrides (e.g. 'ellipsoid' for K-V / ellipsoid-bunch studies).
    sc_model = sc_model or "gaussian"

    rf_elems = ([e for e in _lattice_elements(cfg)
                 if e["type"] == "rf_cavity" and e["length"] > 0
                 and "rf_cavity" in active_types]
                if (sw["rf_longitudinal_kick"] or sw["rf_transverse_kick"]) else [])
    with record_evaluations() as alpha_usage:
        if rf_elems:
            # thin-lens RF (multi-instance): propagate to each cavity entrance,
            # apply H·z chirp, continue to the next one.
            z_parts, st_parts = [], []
            z_cur = 0.0
            beam_cur = beam_k
            n_per = max(200, n_points // (len(rf_elems) + 1))
            for e in rf_elems:
                z_rf = e["z_start"]
                if z_rf > z_cur:
                    z1, st1 = propagate(beam_cur, (z_cur, z_rf), n_points=n_per,
                                        external_force_func=ef, gamma_prime_func=gp_core,
                                        rf_chirp_func=ch_core, sc_model=sc_model)
                    z_parts.append(z1); st_parts.append(st1)
                    beam_cur = Beam6D.from_state(st1[-1], st1[-1, 11], beam_k.Ne,
                                                 beam_k.eps_nx, beam_k.eps_ny, beam_k.eps_nz)
                H = rf_thin_lens_H(cfg, e)
                if sw["rf_longitudinal_kick"]:
                    beam_cur = apply_rf_thin_lens(beam_cur, H)
                if sw["rf_transverse_kick"]:
                    K = -H/(2*beam_cur.gamma**2)
                    beam_cur.nu_x += K*beam_cur.sigma_x
                    beam_cur.nu_y += K*beam_cur.sigma_y
                z_cur = z_rf
            if z_cur < z_max:
                z2, st2 = propagate(beam_cur, (z_cur, z_max), n_points=n_per,
                                    external_force_func=ef, gamma_prime_func=gp_core,
                                    rf_chirp_func=ch_core, sc_model=sc_model)
                z_parts.append(z2); st_parts.append(st2)
            z_arr = np.concatenate([zz if i == 0 else zz[1:]
                                    for i, zz in enumerate(z_parts)])
            st = np.concatenate([ss if i == 0 else ss[1:]
                                 for i, ss in enumerate(st_parts)])
        else:
            z_arr, st = propagate(beam_k, (0.0, z_max), n_points=n_points,
                                  external_force_func=ef, gamma_prime_func=gp_core,
                                  rf_chirp_func=ch_core, sc_model=sc_model)

    from beamline_sim import compute_emittance
    em = compute_emittance(st, beam0.eps_nx, beam0.eps_ny, beam0.eps_nz)

    # Retain legacy-domain diagnostics, explicitly mark that no table is used.
    aspect = st[:, :2] / (st[:, 11, None] * st[:, 2, None])
    outside = np.any((aspect < 1e-2) | (aspect > 1e2), axis=1)
    alpha_domain = {
        "table_range": [1e-2, 1e2], "legacy_table_no_longer_used": True,
        "sampled_aspect_min": float(aspect.min()), "sampled_aspect_max": float(aspect.max()),
        "sampled_rows_outside": int(outside.sum()), "sampled_rows": len(st),
        "sampled_history_only": True, "gaussian_sc_uses_clipped_coefficients": False,
    }

    result = BeamResult(
        route="AG",
        z_mm=z_arr * 1e3,
        sigma_x_um=st[:, 0] * 1e6,
        sigma_y_um=st[:, 1] * 1e6,
        sigma_z_um=st[:, 2] * 1e6,
        eps_nx_mm_mrad=em["eps_n_x"] * 1e6,
        eps_ny_mm_mrad=em["eps_n_y"] * 1e6,
        energy_keV=np.full_like(z_arr, P.beam.energy_keV),
        sigma_delta_e3=st[:, 4] * 1e3,
        C_zdelta_m=st[:, 5],
        gamma_ref=st[:,11],
        beta_ref=np.sqrt(1.-1./st[:,11]**2),
        meta={"section": section, "solenoid_coupling": solenoid_coupling,
              "sc_enabled": sc_enabled, "switches": sw, "config_sha": config_sha(cfg),
              "provenance": provenance(cfg),
              # v0.14.1 task 3 AG state metadata (formal contract):
              "sc_requested": bool(sc_enabled),
              "sc_effective": bool(sc_enabled),   # AG: requested==effective
                                                   # (adapter injects Ne=Q/e)
              "physical_charge_C": float(P.beam.Q_C),
              "physical_electron_number": float(ne_phys),
              "sc_model": sc_model,               # v0.15 D-2 traceability
              "sc_alpha_table_domain": alpha_domain,
              "sc_alpha_evaluation": alpha_usage.as_dict(),
              "ag_ne_phys": float(ne_phys),       # alias (task 2 compat, NOT
                                                   # the formal contract)
              "model": "AG envelope + Kelisani SC Gx/Gy/Gz; fixed reference; Gaussian closure",
              "ag_history_columns": 14,
              "diagnostic_convention": "centered_population_moments; zeta=-beta*tau; delta_p=p_oc/beta (first order)",
              "rf": rf_description(sw, "thin-lens (H)"),
              "rf_model": "effective_voltage; reference_subtracted; axisymmetric_linear_transverse; fixed_reference",
              "runner": "AG.runner.run_from_config",
              "geometry": geometry,
              "longitudinal_initial_state": initial_longitudinal,
              "longitudinal_evolution": {
                  "independent_state": "sigma_z, nu_z, M=sigma_z^2*(theta_z^2-nu_z^2)",
                  "dispersion_model": "Kelisani Eq.(7),(17),(20) paired",
                  "transverse_G_evolved": True,
                  "history": history_diagnostics(st)},
              "n_points_requested": n_points,
              "solenoid_coupling_note": "round-beam default; explicit override retained",
              "lattice_regions": [(r.z_start, r.z_end, r.ftype) for r in regions],
              "rf_kicks_applied": len(rf_elems),
              "rf_events": [{"instance": e["name"], "z_nominal_m": e["z_start"],
                             "z_actual_m": e["z_start"]} for e in rf_elems]},
    )
    return result
