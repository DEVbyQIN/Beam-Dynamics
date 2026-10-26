"""Effective axisymmetric RF thin lens at fixed reference energy.

V is the effective integrated voltage (no additional transit-time factor).
Reference-subtracted modulation, not an accelerating reference trajectory.
See rf_model_physics_note.md; phi=pi gives head deceleration/compression.
"""
import numpy as np
from shared.constants import C_SI


def coefficients(rf, beta, gamma, energy_total_eV):
    p=rf.get('parameters',rf)
    values=np.array([beta,gamma,energy_total_eV,p['frequency_GHz'],p['voltage_kV'],p['phase_rad']],float)
    if not np.isfinite(values).all() or not 0 < beta < 1 or gamma <= 1 or energy_total_eV <= 0 or p['frequency_GHz'] <= 0:
        raise ValueError('RF requires finite parameters and a moving massive reference')
    k=2*np.pi*p['frequency_GHz']*1e9/C_SI
    h=p['voltage_kV']*1e3*k*np.cos(p['phase_rad'])/(beta**3*energy_total_eV)
    return h,-h/(2*gamma**2),k


def relative_energy_gain_eV(tau_m, rf):
    """g(Delta t)-g(0), using tau=c*Delta t; no beta in time phase."""
    p=rf.get('parameters',rf)
    angle=2*np.pi*p['frequency_GHz']*1e9*np.asarray(tau_m)/C_SI
    # Stable sin(phi-angle)-sin(phi), including the short-bunch limit.
    return -2*p['voltage_kV']*1e3*np.sin(angle/2)*np.cos(p['phase_rad']-angle/2)
