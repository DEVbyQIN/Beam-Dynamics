"""Validation adapters; each model's formal driver owns all execution.

These wrappers keep the historical test API. They perform no particle
initialization, lattice assembly, RF kick operation or tracking loop.
_rf_constants is retained only as the existing test-reference coefficient API.
"""
import os
import sys
import numpy as np

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_THIS_DIR)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from shared.beam_result import BeamResult
from shared.constants import C_SI, M_E_SI, E_SI


def _rf_constants(cfg, d, rf_elem=None):
    """Return (H, K_trans, k_rf, E_rf) for ONE rf cavity element.

    rf_elem : lattice element dict of type 'rf_cavity' (default: first one).
    """
    from shared.params import elem_params, first_of_type
    rf = elem_params(rf_elem if rf_elem is not None
                     else first_of_type(cfg, "rf_cavity"))
    k_rf = 2.0 * np.pi * rf["frequency_GHz"] * 1e9 / C_SI
    V = rf["voltage_kV"] * 1e3
    E_rf = V / rf["length_m"]
    gamma, beta = d["gamma"], d["beta"]
    ETA = E_SI / (M_E_SI * C_SI**2)
    H = E_SI * V * k_rf * np.cos(rf["phase_rad"]) / (beta**3 * gamma * M_E_SI * C_SI**2)
    K_trans = -H/(2*gamma**2)
    return H, K_trans, k_rf, E_rf



def run_ag(cfg, section, n_points=2000, sc_enabled=None,
           solenoid_coupling=False, switches=None, sc_model=None,
           longitudinal_check="warn"):
    """Delegate to the same AG driver used by AG/run_shared.py."""
    from AG.runner import run_from_config
    return run_from_config(cfg, section=section, n_points=n_points,
                           sc_enabled=sc_enabled,
                           solenoid_coupling=solenoid_coupling,
                           switches=switches, sc_model=sc_model,
                           longitudinal_check=longitudinal_check)


def _ocelot_rf_kick(p, rf_elem, cfg, d, sw):
    """Compatibility helper for existing RF tests; use the production kick."""
    from GPT模拟 import ued_beamline_v2 as model
    model.apply_rf_kick(p, rf_elem,
                        rf_transverse=sw["rf_transverse_kick"],
                        rf_longitudinal=sw["rf_longitudinal_kick"],
                        ref=model.run_params(cfg))


def run_ocelot(cfg, section, n_particles=None, dz=None, sc_enabled=None,
               switches=None, sc_step=None, sc_mesh=None):
    """Delegate to the CLI's formal driver; omitted dz inherits config."""
    from GPT模拟 import ued_beamline_v2 as model
    run = model.run_from_config(cfg, section=section, n_particles=n_particles,
                                dz=dz, sc_enabled=sc_enabled, switches=switches,
                                sc_step=sc_step, sc_mesh=sc_mesh)
    return BeamResult.from_history("OCELOT", run["history"],
                                   cfg["beam"]["energy_keV"], meta=run["meta"])
