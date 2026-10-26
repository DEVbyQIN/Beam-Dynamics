#!/usr/bin/env python3
"""
UED Beamline Integration — GPT main route (single-source lattice).

The ONLY geometry/parameter source is shared/beamline_config.yaml →
lattice.elements (same as the validation OCELOT route).  Step semantics:

  step 1: only drifts active; all other length-bearing elements are kept as
          plain Drifts so the total length and sample position are unchanged
  step 2: drift + ALL solenoids
  step 3: drift + ALL solenoids + ALL RF cavities
  step 4: same lattice as step 3 + SpaceCharge process (per CLI/SC flags)

RF kicks: one per rf_cavity instance, at the first eligible step start in
lattice order; nominal and actual positions are recorded in meta.rf_events.
the shared physics_switches.rf_transverse_kick gates the transverse part.
OCELOT native tau/R56 unmodified; p_oc = β0·δ_p conversion retained.

Usage:
  python3 ued_beamline_v2.py --step 1    # drift only (inactive as drifts)
  python3 ued_beamline_v2.py --step 2    # + solenoids
  python3 ued_beamline_v2.py --step 3    # + RF
  python3 ued_beamline_v2.py --step 4    # + space charge (full)
"""

import sys
import os

import numpy as np

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_THIS_DIR)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)
from shared.params import load_config, config_sha, _lattice_elements  # noqa: E402
from shared.constants import MEC2_KEV, E_SI, M_E_SI, C_SI  # noqa: E402
from shared.beam_physics import BeamReference  # noqa: E402
from shared.ocelot_coords import (add_p_oc, add_px, add_py,  # noqa: E402
                                  set_px, set_py, set_p_oc)
from shared.output_schema import write_results, make_probe  # noqa: E402
from shared.run_contract import (resolve_switches, section_active_types,
                                 provenance, rf_description)  # noqa: E402

print("加载 OCELOT …", flush=True)
import ocelot  # noqa: E402
from ocelot.cpbd.elements import Drift, Solenoid  # noqa: E402
from ocelot.cpbd.magnetic_lattice import MagneticLattice  # noqa: E402
from ocelot.cpbd.beam import generate_parray  # noqa: E402
from ocelot.cpbd.navi import Navigator  # noqa: E402
from ocelot.cpbd.track import tracking_step  # noqa: E402
from ocelot.cpbd.transformations.second_order import SecondTM  # noqa: E402
from ocelot.cpbd.transformations.transfer_map import TransferMap  # noqa: E402
# v0.15 entrypoint hardening: SpaceCharge is imported LAZILY (only when SC is
# actually requested) so that an unavailable optional SC module can never
# block a no-SC run.  When SC IS requested, an import failure is a HARD FAIL
# inside run_beamline (see the SC runtime state contract) — never a silent
# fallback to no-SC.

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# ═══════════════════════════════════════════════════════════
#  load ALL parameters from SHARED YAML (single source of truth)
# ═══════════════════════════════════════════════════════════

cfg = load_config()

b   = cfg["beam"]
ib  = cfg["initial_distribution"]
sc  = cfg["space_charge"]
out = cfg["output"]
switches = cfg.get("physics_switches", {})

# beam
E_keV       = b["energy_keV"]
Q_C         = b["charge_fC"] * 1e-15
N_part      = b["n_particles"]

# initial distribution
spot_rms    = ib["spot_rms_um"] * 1e-6
sig_z0      = ib["bunch_length_um"] * 1e-6
epsilon_n   = ib["epsilon_n_mm_mrad"] * 1e-6
sigma_delta = ib["sigma_delta"]

# output
z_probes_mm = out["z_diagnostics_mm"]
dz_track    = out["step_size_m"]

# ═══════════════════════════════════════════════════════════
#  relativistic (from config energies only)
# ═══════════════════════════════════════════════════════════

_br = BeamReference.from_energy_keV(E_keV)   # single γ/β/p0 source (v0.13)
gamma      = _br.gamma
beta       = _br.beta
beta_gamma = _br.beta_gamma
p_SI       = _br.p0

epsilon_geom = epsilon_n / beta_gamma
sigma_xp     = epsilon_geom / spot_rms
sigma_yp     = epsilon_geom / spot_rms

E_total_eV = gamma * MEC2_KEV * 1e3


def run_params(c):
    """Derive EVERY per-run quantity from ONE effective config dict.

    v0.15 repair: run_beamline/build_lattice_from_shared/apply_rf_kick used the
    module-level globals loaded at import time, so a caller-supplied
    `cfg_override` changed nothing (audit counterexample: 100→200 keV,
    100→500 fC, 85→170 µm, 5→10 mm gave an identical history).

    Precedence is resolved by the CALLER: explicit argument > cfg_override >
    module config.  This helper only turns the winner into run quantities and
    reuses the shared single source for kinematics (shared/beam_physics.py) —
    no physics formula is duplicated here.
    """
    _b, _ib, _o = c["beam"], c["initial_distribution"], c["output"]
    br = BeamReference.from_energy_keV(_b["energy_keV"])
    eps_n = _ib["epsilon_n_mm_mrad"] * 1e-6          # geometric [m·rad] input
    spot = _ib["spot_rms_um"] * 1e-6                 # [m]
    sig_z0 = _ib["bunch_length_um"] * 1e-6           # [m]
    sig_xp = (eps_n / br.beta_gamma) / spot          # [rad]
    return {
        "E_keV": _b["energy_keV"],
        "Q_C": _b["charge_fC"] * 1e-15,
        "N_part": _b["n_particles"],
        "spot_rms": spot,
        "sig_z0": sig_z0,
        "epsilon_n": eps_n,
        "sigma_delta": _ib["sigma_delta"],
        "gamma": br.gamma, "beta": br.beta,
        "beta_gamma": br.beta_gamma, "p_SI": br.p0,
        "sigma_xp": sig_xp, "sigma_yp": sig_xp,
        "E_total_eV": br.gamma * MEC2_KEV * 1e3,
        "z_probes_mm": list(_o["z_diagnostics_mm"]),
        "dz_track": _o["step_size_m"],
        "seed": int(c["random"]["seed"]),
    }

# ═══════════════════════════════════════════════════════════
#  generic lattice builder — lattice.elements is the ONLY geometry source
# ═══════════════════════════════════════════════════════════

def build_lattice_from_shared(cfg, active_types, keep_zero_markers=False):
    """Build an OCELOT lattice from lattice.elements (single source).

    active_types : set of element types that keep their real physics
      ({"drift"}, {"drift","solenoid"}, {"drift","solenoid","rf_cavity"}).
      Every other length-bearing element is kept as a plain Drift of the
      SAME length, so the total length and sample position are preserved.

    keep_zero_markers : with SC ON (v0.14.1 task 1) the zero-length
      cathode/sample markers are kept in the runtime sequence so the
      SpaceCharge PhysProc can be attached as cathode → sample (coverage
      ends at the sample position, not at the start of the last non-zero
      element).  SC OFF keeps the previous sequence (markers skipped).

    RF handling (v0.15 repair 2): the returned `rf_elems` lists every
    STAGE-ELIGIBLE rf_cavity instance (i.e. whenever "rf_cavity" is in
    active_types).  Whether each RF ROLE is executed is decided at run time by
    resolve_switches() inside run_beamline — the builder no longer removes
    entries based on config switches, so an explicit switch override can
    always take effect.  The RF body stays a Drift, so the geometry/length is
    preserved when a role is OFF.

    Solenoid strength is derived from THIS cfg's beam energy (not the module
    global), so a cfg_override with a different energy builds the correct k.

    Returns (lattice, rf_elems).
    """
    from shared.geometry import validate_geometry
    validate_geometry(cfg)
    elems = []
    rf_elems = []
    _p_SI = BeamReference.from_energy_keV(cfg["beam"]["energy_keV"]).p0
    for e in _lattice_elements(cfg):
        etype, L = e["type"], e["length"]
        if L <= 0:
            if keep_zero_markers and etype in ("cathode", "sample"):
                elems.append(Drift(l=0.0, eid=e["name"] + "_MARKER"))
            continue                       # cathode / sample markers
        if etype == "solenoid" and "solenoid" in active_types:
            B = e["parameters"]["B_field_T"]
            k = E_SI * B / (2.0 * _p_SI)
            elems.append(Solenoid(l=L, k=k, eid=e["name"]))
        elif etype == "rf_cavity" and "rf_cavity" in active_types:
            elems.append(Drift(l=L, eid=e["name"] + "_BODY"))
            rf_elems.append(e)             # kick scheduling entry (stage-eligible)
        else:
            elems.append(Drift(l=L, eid=e["name"]))   # drift or inactive
    # Use class objects and strict family requests.  The installed Solenoid
    # inherits a drift-like T tensor: selecting SecondTM there would not add
    # the actual solenoid chromatic terms.  Retain its audited linear map.
    lat = MagneticLattice(elems, method={"global": TransferMap,
                                        Drift: SecondTM, Solenoid: TransferMap})
    lat.update_transfer_maps()
    for element in lat.sequence:
        expected = SecondTM if isinstance(element, Drift) else TransferMap
        actual = [type(tm) for tm in element.tms]
        if not actual or any(tm is not expected for tm in actual):
            raise RuntimeError(
                f"OCELOT tracking method mismatch for {element.id}: "
                f"expected {expected.__name__}, got "
                f"{[tm.__name__ for tm in actual]}")
    lat.ued_transport_policy = "drift_second_order_solenoid_linear_v1"
    return lat, rf_elems


def tracking_method_metadata(lat):
    """Read active particle maps, rather than the separate linear-optics path."""
    return [{"name": e.id, "type": type(e).__name__, "length_m": float(e.l),
             "tracking_methods": [type(tm).__name__ for tm in e.tms]}
            for e in lat.sequence]


STEP_ACTIVE = {
    1: {"drift"},
    2: {"drift", "solenoid"},
    3: {"drift", "solenoid", "rf_cavity"},
    4: {"drift", "solenoid", "rf_cavity"},
}


def sc_requested_from(cfg, step):
    """v0.14.1 task 3 — single source of the requested SC state.

    - `step` defines only ROUTE CAPABILITY / stage: steps 1-3 have NO SC
      capability; only step 4 may run SC.
    - config `space_charge.enabled` (or an explicit function argument)
      defines the REQUESTED physics state.
    - the runtime state contract (shared/sc_state.py) decides the final
      EFFECTIVE state.

    Returns the effective requested flag = config.enabled AND step >= 4.
    Step 1-3 never auto-enables SC even if config requests it.
    """
    return bool(cfg["space_charge"]["enabled"]) and step >= 4


def apply_rf_kick(parray, rf_elem, rf_transverse=False, rf_longitudinal=True,
                  ref=None):
    """Standardized thin-lens RF kick for ONE rf_cavity instance.

    Longitudinal: relative energy modulation using phase phi-omega*Delta_t,
    normalized directly into p_oc=DeltaE/(c*p0). Transverse: the common
    axisymmetric entrance thin lens K=-H/(2*gamma^2). Fixed reference;
    voltage is effective integrated voltage. See shared RF Physics Note.

    v0.15 hardening: the two roles are gated INDEPENDENTLY by the shared
    physics_switches (rf_longitudinal_kick / rf_transverse_kick) — turning the
    longitudinal kick OFF must not disable the transverse kick.

    ref : optional {"beta","gamma","E_total_eV"} bundle from the effective
    config (run_params).  When omitted the module-level reference is used, so
    existing callers keep working unchanged.
    """
    pv = rf_elem["parameters"]
    V = pv["voltage_kV"] * 1e3
    phi = pv["phase_rad"]
    k = 2.0 * np.pi * pv["frequency_GHz"] * 1e9 / C_SI
    # Reference kinematics come from THIS run's effective config (repair 1) —
    # a cfg_override with another energy must use its own β/γ/E_total.
    if ref is None:
        ref = {"beta": beta, "gamma": gamma, "E_total_eV": E_total_eV}
    _beta, _gamma = ref["beta"], ref["gamma"]
    _E_total_eV = ref["E_total_eV"]
    if rf_longitudinal:
        from shared.rf_model import relative_energy_gain_eV
        add_p_oc(parray,relative_energy_gain_eV(parray.tau(),rf_elem)/(_beta*_E_total_eV))
    if rf_transverse:
        from shared.rf_model import coefficients
        K_trans = coefficients(rf_elem,_beta,_gamma,_E_total_eV)[1]
        x = parray.x(); y = parray.y()
        add_px(parray, K_trans * x)
        add_py(parray, K_trans * y)


# ═══════════════════════════════════════════════════════════
#  diagnostics
# ═══════════════════════════════════════════════════════════

def emit(x, xp):
    from shared.diagnostics import pair_moments, covariance_area
    return covariance_area(*pair_moments(x,xp))


# ═══════════════════════════════════════════════════════════
#  tracking (no manual tau/z override — trust OCELOT)
# ═══════════════════════════════════════════════════════════

def probe_name(z_mm):
    """Preserve fractional diagnostic positions in the existing lookup API."""
    return f"z{z_mm:g}mm"


def run_from_config(cfg, section="full", n_particles=None, dz=None,
                    sc_enabled=None, switches=None, sc_step=None, sc_mesh=None):
    """The formal config-to-result route shared by CLI and validation.

    Validation sections and CLI stages select the same active element types.
    Inactive bodies retain their geometry as drifts.
    """
    from shared.geometry import validate_geometry
    geometry = validate_geometry(cfg)
    active = section_active_types(section)
    sc_requested = bool(cfg["space_charge"]["enabled"] if sc_enabled is None
                        else sc_enabled)
    lat, rf_elems = build_lattice_from_shared(cfg, active,
                                             keep_zero_markers=sc_requested)
    result = run_beamline(lat, rf_elems, sc_enabled=sc_requested,
                          nparticles=n_particles, switches=switches,
                          cfg_override=cfg, sc_step=sc_step, sc_mesh=sc_mesh, dz=dz)
    result["meta"]["section"] = section
    result["meta"]["geometry"] = geometry
    result["meta"]["active_types"] = sorted(active)
    return result


def run_beamline(lat, rf_elems, sc_enabled=None, nparticles=None,
                 switches=None, cfg_override=None, sc_step=None, sc_mesh=None,
                 dz=None):
    """Track the beam through the given lattice, kicking every rf instance.

    Parameter precedence (v0.15 entrypoint hardening): explicit arguments
    > cfg_override > module-level config.  No module-cached value may
    silently override a caller-supplied configuration.

    SC runtime state contract (shared/sc_state.py — the single state machine;
    no second implementation is maintained here):
      requested=True  → import / construction / attach failure, final
                        apply_count == 0, or a coverage that is not
                        cathode→sample is a HARD FAIL (RuntimeError).
      requested=False → an unavailable optional SC module must NOT block the
                        no-SC run (SpaceCharge is imported lazily).
      effective       → apply_count > 0 (never "the object exists").
    """
    c = cfg_override if cfg_override is not None else cfg
    # Also report honestly for caller-supplied low-level lattices; do not
    # relabel their chosen maps as the formal builder's policy.
    tracking_maps = tracking_method_metadata(lat)
    P = run_params(c)                      # ALL per-run quantities (repair 1)
    if dz is not None:
        P["dz_track"] = dz
    if not np.isfinite(P["dz_track"]) or P["dz_track"] <= 0:
        raise ValueError("OCELOT tracking step must be finite and > 0")
    # sc_enabled precedence (repair 1): an explicit boolean always wins; only
    # `None` falls back to the effective config's space_charge.enabled.
    if sc_enabled is None:
        sc_enabled = bool(c.get("space_charge", {}).get("enabled", False))
    sc_enabled = bool(sc_enabled)
    nparticles = nparticles if nparticles is not None else P["N_part"]
    if not isinstance(nparticles, (int, np.integer)) or nparticles < 2:
        raise ValueError("OCELOT n_particles must be an integer >= 2")
    # Resolve the RF switches ONCE here; the same resolution drives execution
    # (repair 2: the builder no longer pre-deletes entries).
    sw = resolve_switches(c, switches)
    sc_cfg = c.get("space_charge", {})
    # Random policy (v0.13): configured seed → x/y/tau; seed+1 → px/py/δ_p.
    rng_seed = P["seed"]
    np.random.seed(rng_seed)
    p = generate_parray(
        sigma_x=P["spot_rms"], sigma_y=P["spot_rms"],
        sigma_tau=P["sig_z0"] / P["beta"],   # OCELOT tau = c·t [m]; σ_tau = σ_z/β
        energy=(P["E_keV"] + 511.0) * 1e-6,  # TOTAL energy in GeV (E_kin+mc²)
        charge=P["Q_C"],
        nparticles=nparticles,
    )
    np.random.seed(rng_seed + 1)
    N = p.rparticles.shape[1]
    set_px(p, np.random.normal(0.0, P["sigma_xp"], N))
    set_py(p, np.random.normal(0.0, P["sigma_yp"], N))
    # OCELOT p() = ΔE/(c·p0), NOT Δp/p0 → p_oc = β0·δ_p  (R56 audit: B)
    set_p_oc(p, P["beta"] * np.random.normal(0.0, P["sigma_delta"], N))

    # ── SC runtime state contract ──
    from shared.sc_state import SCState
    sc_state = SCState(requested=bool(sc_enabled))
    sc_proc = None
    if sc_enabled:
        # HARD FAIL on import: no silent fallback to no-SC.
        try:
            from ocelot.cpbd.sc import SpaceCharge
            sc_state.available = True
        except ImportError as e:
            sc_state.fail(f"SpaceCharge import failed: {e!r}")
        try:
            sc_proc = SpaceCharge(
                step=(sc_step if sc_step is not None
                      else sc_cfg.get("step", 1)),
                nmesh_xyz=list(sc_mesh if sc_mesh is not None
                               else sc_cfg.get("mesh", [63, 63, 63])))
        except Exception as e:
            sc_state.fail(f"SpaceCharge construction failed: {e!r}")
        sc_state.configured = True

    navi = Navigator(lat, unit_step=P["dz_track"])
    if sc_proc is not None:
        # attach must succeed explicitly — no silent "sequence too short"
        # shortening of the coverage.
        try:
            navi.add_physics_proc(sc_proc, lat.sequence[0], lat.sequence[-1])
        except Exception as e:
            sc_state.fail(f"add_physics_proc failed: {e!r}")
        sc_state.attached = True
        sc_state.coverage_start_m = float(sc_proc.s_start)
        sc_state.coverage_stop_m = float(sc_proc.s_stop)

    total_length = sum(e.l for e in lat.sequence)

    probes_rem = {probe_name(z): z * 1e-3 for z in P["z_probes_mm"]}
    probe_nominal = dict(probes_rem)          # nominal planes (never mutated)
    # Pure floating-point round-off tolerance for "the plane was reached",
    # in METRES: 1e-12 m = 1e-9 mm.  Accumulating a 50 mm path from 5 mm
    # steps can land ~1e-17 m short of the nominal plane, which must not be
    # reported as "plane never reached" (the sample plane would be silently
    # dropped from the output).  This is ~12 orders of magnitude below the
    # smallest physical length in the lattice, and it does NOT change the
    # tracking step size or the beam path.
    PROBE_TOL_M = 1e-12
    results = {}
    from shared.output_schema import BASE_FIELDS, DIAGNOSTIC_FIELDS
    from shared.diagnostics import particle_diagnostics
    hist = {k:[] for k in BASE_FIELDS+DIAGNOSTIC_FIELDS}
    rf_done = set()
    rf_events = []
    rf_transverse = sw["rf_transverse_kick"]
    rf_longitudinal = sw["rf_longitudinal_kick"]
    if sc_proc is not None and (rf_transverse or rf_longitudinal):
        # Native zero-length PhysProc boundaries force the Navigator to stop
        # at RF entrances; SC interval/counter logic remains entirely native.
        from ocelot.cpbd.physics_proc import PhysProc
        for e in rf_elems:
            if e['z_start'] > 1e-12:
                body=next(el for el in lat.sequence if el.id==e['name']+'_BODY')
                navi.add_physics_proc(PhysProc(),body,body)

    def _kick_rf_if_due(z_start):
        # Both tracking loops stop exactly at each entrance.
        # (both RF roles gated independently inside apply_rf_kick)
        if not (rf_longitudinal or rf_transverse):
            return
        for instance, rf_elem in enumerate(rf_elems):
            z_rf = rf_elem["z_start"]
            if instance not in rf_done and z_start >= z_rf - 1e-12:
                apply_rf_kick(p, rf_elem, rf_transverse, rf_longitudinal,
                              ref=P)
                rf_done.add(instance)
                rf_events.append({"instance": rf_elem["name"],
                                  "z_nominal_m": float(z_rf),
                                  "z_actual_m": float(z_start)})

    def _record(name, xa, xpa, ya, ypa, z_actual):
        """Fill one probe record from the CURRENT particle state."""
        diag=particle_diagnostics(p,P)
        results[name] = {
            "z_mm": probe_nominal[name] * 1e3,
            # actual position of the sampled state + whether it equals the
            # nominal probe plane.  A probe that is NOT step aligned is
            # sampled at the step END and explicitly flagged instead of being
            # passed off as an exact in-step diagnostic.
            "z_actual_mm": z_actual * 1e3,
            "z_exact": bool(abs(z_actual - probe_nominal[name]) < PROBE_TOL_M),
            "sigma_x_um": np.std(xa) * 1e6,
            "sigma_y_um": np.std(ya) * 1e6,
            "sigma_t_fs": np.std(p.tau()) / C_SI * 1e15,
            "eps_x_mm_mrad": emit(xa, xpa) * 1e6,
            "eps_y_mm_mrad": emit(ya, ypa) * 1e6,
            "sigma_delta_e3": np.std(p.p()) / P["beta"] * 1e3,  # δ_p = p_oc/β0
        }
        results[name].update(diag)
        results[name]['eps_x_mm_mrad']=diag['eps_nx_mm_mrad']/P['beta_gamma']
        results[name]['eps_y_mm_mrad']=diag['eps_ny_mm_mrad']/P['beta_gamma']

    def _sample(xa, xpa, ya, ypa, z, z_before):
        # full z-history for the unified output (shared schema)
        diag=particle_diagnostics(p,P)
        diag['z_mm']=z*1e3
        for key in hist:
            hist[key].append(diag[key])
        for name, z_p in list(probes_rem.items()):
            # v0.15 task D: closed interval — a probe exactly at the END of
            # the line must be captured too (the half-open interval dropped
            # the sample plane), and a probe sitting exactly on the step
            # start is captured at this step's end but flagged not-exact.
            if z_before <= z_p <= z + PROBE_TOL_M:
                _record(name, xa, xpa, ya, ypa, z)
                del probes_rem[name]

    def _sample_now(z, z_before):
        """Convenience wrapper: read the current state, then sample."""
        _xa = p.x(); _xpa = p.px(); _ya = p.y(); _ypa = p.py()
        _sample(_xa, _xpa, _ya, _ypa, z, z_before)

    # v0.15 task D: the z=0 start plane is an EXACT diagnostic of the initial
    # state — sampling it at the end of the first step would mislabel a
    # 5 mm-advanced state as z=0.
    _start_names = [n for n, z_p in probes_rem.items() if abs(z_p) < 1e-15]
    if _start_names:
        _xa = p.x(); _xpa = p.px(); _ya = p.y(); _ypa = p.py()
        for _n in _start_names:
            _record(_n, _xa, _xpa, _ya, _ypa, 0.0)
            del probes_rem[_n]

    sc_apply_count = 0
    sc_events = []
    # History and probes now both include the actual initial distribution.
    # This adds a diagnostic row only; no transfer map/process is executed.
    _sample_now(0.0,0.0)
    if sc_proc is not None:
        # ── SC ON: OCELOT NATIVE scheduler (v0.14.1 task 1) ──
        # get_next_step() is the exact mechanism of ocelot.track(); the
        # SpaceCharge PhysProc is triggered by the Navigator process counter
        # with coverage [s_start, s_stop) set by the add_physics_proc anchors
        # (cathode → sample).  The manual counter clone is retired.
        for t_maps, dz_step, proc_list, phys_steps in navi.get_next_step():
            z_start = navi.z0 - dz_step
            _kick_rf_if_due(z_start)
            for tm in t_maps:
                tm.apply(p)
            for proc, zstep in zip(proc_list, phys_steps):
                proc.z0 = navi.z0
                proc.apply(p, zstep)
                if proc is sc_proc:
                    sc_apply_count += 1
                    sc_events.append((float(navi.z0), float(zstep)))
            _sample_now(navi.z0, z_start)
    else:
        # ── SC OFF: fixed-step loop (tracking_step; no PhysProc attached) ──
        # v0.15 task D: int(total/dz) silently DROPS the final sub-step
        # (777 mm / 5 mm → 155 steps → 775 mm; the sample plane at 777 mm was
        # never reached).  Keep every existing full step (physics along the
        # way unchanged) and append ONE tail step with the remaining length.
        # The configured step size is NOT modified.
        n_steps = int(total_length / P["dz_track"]) if total_length > 0 else 1
        def advance_distance(distance):
            target=navi.z0+distance
            while navi.z0 < target-1e-12:
                z_before=navi.z0
                _kick_rf_if_due(z_before)
                pending=[e['z_start'] for i,e in enumerate(rf_elems)
                         if i not in rf_done and e['z_start']>z_before+1e-12]
                end=min([target]+pending) if (rf_transverse or rf_longitudinal) else target
                ds=distance if z_before==target-distance and abs(end-target)<1e-12 else end-z_before
                tracking_step(lat,p,ds,navi)
                _sample_now(navi.z0,z_before)
        for step_i in range(n_steps):
            advance_distance(P['dz_track'])
        _remaining = total_length - navi.z0
        if _remaining > 1e-12:
            advance_distance(_remaining)

    results["history"] = hist
    results["rf_kicks_applied"] = len(rf_done)
    # Provenance of the EFFECTIVE config that this run actually used (repair 1:
    # lets a caller/test verify that a cfg_override reached the production
    # call instead of the module import-time snapshot).
    results["run_params"] = {
        "energy_keV": P["E_keV"], "charge_C": P["Q_C"],
        "n_particles_requested": nparticles,
        "n_particles_actual": int(p.rparticles.shape[1]),
        "charge_total_C": float(np.sum(p.q_array)),
        "sigma_x0_m": P["spot_rms"], "sigma_z0_m": P["sig_z0"],
        "sigma_xp_rad": P["sigma_xp"], "sigma_delta": P["sigma_delta"],
        "gamma": P["gamma"], "beta": P["beta"], "p0": P["p_SI"],
        "dz_track_m": P["dz_track"], "seed": P["seed"],
        "z_probes_mm": list(P["z_probes_mm"]),
        "effective_switches": dict(sw),
    }
    # ── SC runtime state: HARD FAIL + metadata (single state machine) ──
    sc_state.apply_count = sc_apply_count
    if sc_state.requested:
        # expected coverage comes from the SHARED lattice (sample position) —
        # never a hardcoded 0.777
        _sample_elems = [e for e in _lattice_elements(c)
                         if e["type"] == "sample"]
        exp_stop = float(_sample_elems[0]["z_start"]) if _sample_elems else 0.0
        sc_state.verify_final(0.0, exp_stop)
    results.update(sc_state.to_meta())
    if sc_proc is not None:
        results["sc_scheduler"] = "ocelot_native"
        results["sc_events"] = sc_events
    results["rf_events"] = rf_events
    meta = {
        "model": "OCELOT macroparticle tracking (active methods in lattice_sequence)",
        "ocelot_version": ocelot.__version__,
        "transport_policy": getattr(lat, "ued_transport_policy", "caller_supplied"),
        "transport_limits": [
            "Solenoid uses a linear hard-edge map; nonlinear/chromatic solenoid transport is not represented",
            "Drift SecondTM is a second-order expansion around the fixed reference particle",
        ] if getattr(lat, "ued_transport_policy", None) else [],
        "runner": "GPT模拟.ued_beamline_v2.run_from_config",
        "rf": rf_description(sw, "thin-lens (K·sin)"),
        "rf_model": "effective_voltage; reference_subtracted; axisymmetric_linear_transverse; fixed_reference",
        "rf_kicks_applied": len(rf_done), "rf_instances_scheduled": len(rf_elems),
        "rf_events": rf_events, "switches": sw, "effective_switches": sw,
        "config_sha": config_sha(c), "provenance": provenance(c),
        "tracked_length_m": float(total_length),
        "lattice_sequence": tracking_maps,
        "sc_enabled": bool(results["sc_effective"]),
        "longitudinal_native_coordinate": "p_oc = dE/(c*p0)",
        "reported_delta": "delta_p = dp/p0", "conversion_beta": float(P["beta"]),
        "diagnostic_convention": "charge_weighted_centered_population_moments; delta_p=p_oc/beta (first order)",
        "run_params": results["run_params"],
    }
    meta.update(sc_state.to_meta())
    if sc_proc is not None:
        meta.update(sc_scheduler="ocelot_native", sc_events=sc_events)
    results["meta"] = meta
    # Compute the standardized probe output once for both callers.
    results["probes"] = [make_probe(
        z_mm=d["z_mm"], sigma_x_um=d["sigma_x_um"], sigma_y_um=d["sigma_y_um"],
        sigma_z_um=d["sigma_t_fs"] * C_SI * P["beta"] * 1e-9,
        sigma_delta_e3=d["sigma_delta_e3"],
        eps_nx_mm_mrad=d["eps_x_mm_mrad"] * P["beta_gamma"],
        eps_ny_mm_mrad=d["eps_y_mm_mrad"] * P["beta_gamma"],
        z_actual_mm=d["z_actual_mm"], z_exact=d["z_exact"],
        **{key:d[key] for key in DIAGNOSTIC_FIELDS},
        sampling="particle_state_at_step_end")
        for z_mm in P["z_probes_mm"] if (d := results.get(probe_name(z_mm))) is not None]
    return results


# ═══════════════════════════════════════════════════════════
#  main
# ═══════════════════════════════════════════════════════════

def main(out_dir=None, cfg_override=None, step=None):
    """CLI / programmatic entrypoint.

    out_dir : optional results directory (defaults to shared/results).  It is
    forwarded to the REAL shared.output_schema.write_results, so a test can
    exercise the complete serialization chain without touching the repo
    results directory (v0.15 repair 3).
    """
    cfg = globals()["cfg"] if cfg_override is None else cfg_override
    if step is None:
        step = 4  # default: full beamline
        for i, a in enumerate(sys.argv):
            if a == "--step" and i + 1 < len(sys.argv):
                step = int(sys.argv[i + 1])
    if step not in STEP_ACTIVE:
        print(f"  unknown step {step}; must be 1..4")
        sys.exit(1)
    _Pm = run_params(cfg)          # main() runs the module config
    _zprobes = _Pm["z_probes_mm"]

    # v0.14.1 task 3: single source of the requested SC state.
    #   step       → route capability only (1-3: no SC; 4: may run SC)
    #   config     → requested physics state
    #   runtime    → state contract decides the effective state
    # The old dual source (step>=4 for display vs config.enabled for the
    # saved output) is REMOVED — one run, one recorded state.
    sc_requested = sc_requested_from(cfg, step)
    # keep_zero_markers: SC ON keeps the cathode/sample zero-length markers
    # in the runtime sequence so SpaceCharge attaches as cathode → sample
    # (v0.14.1 task 1; SC OFF sequence unchanged).
    _sw_eff = resolve_switches(cfg)
    section = {1: "drift", 2: "solenoid", 3: "full", 4: "full"}[step]
    r = run_from_config(cfg, section=section,
                        sc_enabled=sc_requested, switches=_sw_eff)
    sequence = r["meta"]["lattice_sequence"]
    total_length = r["meta"]["tracked_length_m"]
    rf_elems = [e for e in _lattice_elements(cfg)
                if e["type"] == "rf_cavity" and e["length"] > 0
                and "rf_cavity" in STEP_ACTIVE[step]]
    n_sol = sum(e["type"] == "Solenoid" for e in sequence)
    n_rf = len(rf_elems)

    print(f"\n{'='*65}")
    print(f"  UED Beamline Integration — Step {step}")
    print(f"{'='*65}")
    print(f"  E={_Pm['E_keV']:.0f} keV  ε_n={_Pm['epsilon_n']*1e6:.3f} mm·mrad  "
          f"Q={cfg['beam']['charge_fC']:.0f} fC")
    print(f"  lattice: {len(sequence)} elements, total {total_length*1e3:.0f} mm "
          f"(solenoids={n_sol}, rf={n_rf})")
    print(f"  RF instances: {n_rf}; executed operations: {r['rf_kicks_applied']} "
          f"(nominal entrances: {[e['z_start']*1e3 for e in rf_elems]} mm)")
    print(f"  RF switches (effective): longitudinal="
          f"{'ON' if _sw_eff['rf_longitudinal_kick'] else 'OFF'}, transverse="
          f"{'ON' if _sw_eff['rf_transverse_kick'] else 'OFF'} (shared)")
    print(f"  SC: {'ON' if sc_requested else 'OFF'}  "
          f"(requested via config AND step>=4, mesh={cfg['space_charge'].get('mesh')})")

    print(f"  {'Probe':>8s}  {'σ_x(μm)':>9s}  {'σ_y(μm)':>9s}  {'σ_t(fs)':>9s}  "
          f"{'ε_x(mm·mrad)':>13s}  {'σ_δ(e-3)':>9s}")
    for name in [probe_name(z) for z in _zprobes]:
        if name in r:
            d = r[name]
            # v0.15 repair 3: a probe that is not step-aligned is sampled at
            # the step END — say so explicitly instead of presenting it as an
            # exact in-step value.
            flag = "" if d.get("z_exact", True) else \
                f"  [! sampled at {d['z_actual_mm']:.1f} mm, NOT the exact plane]"
            print(f"  {name:>8s}  {d['sigma_x_um']:9.1f}  {d['sigma_y_um']:9.1f}  "
                  f"{d['sigma_t_fs']:9.0f}  {d['eps_x_mm_mrad']:13.4f}  "
                  f"{d['sigma_delta_e3']:9.2f}{flag}")

    # ═══════════════════════════════════════════════════════
    #  Step-specific validation
    # ═══════════════════════════════════════════════════════
    if step == 1:
        print(f"\n  --- Step 1 Validation: Drift vs Analytic ---")
        for name in [probe_name(z) for z in _zprobes]:
            if name in r:
                z_m = r[name]["z_mm"] * 1e-3
                # display only: use the EFFECTIVE run params (repair 1), not
                # the import-time globals
                sx_an = np.sqrt(_Pm["spot_rms"]**2
                                + _Pm["sigma_xp"]**2 * z_m**2) * 1e6
                sx_oc = r[name]["sigma_x_um"]
                err = abs(sx_oc - sx_an) / sx_an * 100
                flag = "✓" if err < 5 else "✗ FAIL"
                print(f"    z={z_m*1e3:5.0f}mm  σ_x OC={sx_oc:.1f}  "
                      f"analytic={sx_an:.1f}μm  err={err:.2f}%  {flag}")

    elif step == 2:
        print(f"\n  --- Step 2 Validation: Solenoid Focusing ---")
        probe_names = [probe_name(z) for z in _zprobes]
        sx_vals = [r[n]["sigma_x_um"] for n in probe_names if n in r]
        waist = min(sx_vals)
        print(f"    σ_x before solenoid (z=100mm): "
              f"{r.get('z100mm',{}).get('sigma_x_um','?'):.1f} μm")
        print(f"    σ_x after  solenoid (z=160mm): "
              f"{r.get('z160mm',{}).get('sigma_x_um','?'):.1f} μm")
        print(f"    Min σ_x in drift after: {waist:.1f} μm")
        print(f"    ε_x conserved: {r.get('z0mm',{}).get('eps_x_mm_mrad',0):.4f} → "
              f"{r.get('z777mm',{}).get('eps_x_mm_mrad',0):.4f} mm·mrad")

    elif step >= 3 and rf_elems:
        print(f"\n  --- Step 3 Validation: RF Chirp (analytic kick) ---")
        rf0 = rf_elems[0]["parameters"]
        V0 = rf0["voltage_kV"] * 1e3
        phi0 = rf0["phase_rad"]
        k0 = 2.0 * np.pi * rf0["frequency_GHz"] * 1e9 / C_SI
        # display only: effective run params (repair 1), not import-time globals
        _beta_p, _Etot_p = _Pm["beta"], _Pm["E_total_eV"]
        test_tau = np.linspace(-2 * _Pm["sig_z0"], 2 * _Pm["sig_z0"], 1000)
        z_phys = -_beta_p * test_tau
        from shared.rf_model import relative_energy_gain_eV,coefficients
        d_delta = relative_energy_gain_eV(test_tau,rf_elems[0])/(_beta_p**2*_Etot_p)
        chirp = np.polyfit(z_phys, d_delta, 1)[0]
        rho = np.corrcoef(z_phys, d_delta)[0, 1]
        expected_chirp = coefficients(rf_elems[0],_beta_p,_Pm['gamma'],_Etot_p)[0]
        print(f"    δ = ΔE_relative(Δt)/(β² Etotal); time phase=φ-ωΔt")
        print(f"    V={V0*1e-3:.0f} kV  φ={phi0:.3f} rad  "
              f"E_total={_Etot_p*1e-3:.0f} keV")
        print(f"    dδ/dz = {chirp:.2f} m⁻¹  (expected: {expected_chirp:.2f} m⁻¹)")
        print(f"    corr(z,δ) = {rho:.4f}  σ_δ = {np.std(d_delta)*1e3:.2f}e-3")
        slope_ok=abs(chirp-expected_chirp)<=.02*abs(expected_chirp)+1e-12
        print(f"    Linear chirp amplitude/sign: {'✓' if slope_ok else '✗ FAIL'}")

        if step >= 4 and sc_requested:
            print(f"\n  --- Step 4 Validation: Space Charge ---")
            r_sc = run_from_config(cfg, section=section,
                                    sc_enabled=False, switches=_sw_eff)
            probe_names = [probe_name(z) for z in _zprobes]
            dsx = [(r[n]["sigma_x_um"] / r_sc[n]["sigma_x_um"] - 1) * 100
                   for n in probe_names if n in r and n in r_sc]
            dex = [(r[n]["eps_x_mm_mrad"] / r_sc[n]["eps_x_mm_mrad"] - 1) * 100
                   for n in probe_names if n in r and n in r_sc]
            print(f"    Max Δσ_x (SC ON vs OFF): {max(dsx):.2f}%")
            print(f"    Max Δε_x (SC ON vs OFF): {max(dex):.2f}%")
            print(f"    SC effect: {'DETECTED' if max(dsx) > 0.01 else 'NEGLIGIBLE (expected at 100 fC)'}")

    print("\n  Validation complete.")

    # ═══════════════════════════════════════════════════════
    #  unified output (shared schema) — v0.14.1 task 3:
    #  the run above already used the single requested source (config AND
    #  step>=4); there is NO second run with a different SC flag, so the
    #  terminal display and the saved sc_enabled can never disagree.
    # ═══════════════════════════════════════════════════════
    sc_effective = bool(r.get("sc_effective", False))
    sc_flag = sc_effective
    r_uni = r

    probes = r_uni["probes"]
    meta = dict(r_uni["meta"], step_flag=step)
    path = write_results("GPT", probes, r_uni["history"], config_sha(cfg),
                         sc_flag, out_dir=out_dir, meta=meta)
    print(f"\n  Unified output -> {path}")
    print(f"  SC state: requested={sc_requested} effective={sc_effective} "
          f"(saved sc_enabled={sc_flag})")
    return path


if __name__ == "__main__":
    main()
