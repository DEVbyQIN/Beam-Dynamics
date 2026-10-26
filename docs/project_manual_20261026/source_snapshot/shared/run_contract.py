"""Execution conventions shared by the two model drivers (no force model)."""
from pathlib import Path
import hashlib
import json
import subprocess
import importlib.metadata
from datetime import datetime

from shared.params import config_sha, _lattice_elements


def section_active_types(section):
    sections = {
        "drift": {"drift"},
        "solenoid": {"drift", "solenoid"},
        "rf": {"drift", "rf_cavity"},
        "full": {"drift", "solenoid", "rf_cavity"},
    }
    if section not in sections:
        raise ValueError(f"unknown section {section!r}; expected {tuple(sections)}")
    return sections[section]


def resolve_switches(cfg, switches=None):
    """Explicit fields override config fields; omitted fields inherit config."""
    eff = dict(cfg.get("physics_switches") or {})
    eff.update(switches or {})
    return {"rf_longitudinal_kick": bool(eff.get("rf_longitudinal_kick", True)),
            "rf_transverse_kick": bool(eff.get("rf_transverse_kick", False))}


def rf_description(sw, longitudinal):
    roles = []
    if sw["rf_longitudinal_kick"]:
        roles.append(longitudinal)
    if sw["rf_transverse_kick"]:
        roles.append("transverse kick")
    return " + ".join(roles) if roles else "RF OFF"


def provenance(cfg):
    """Record the source checkout rather than the caller's working directory."""
    repo = Path(__file__).resolve().parents[1]
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo,
                                capture_output=True, text=True, timeout=5)
        git_commit = commit.stdout.strip() or "unknown"
    except (OSError, subprocess.TimeoutExpired):
        git_commit = "unknown"
    lattice = json.dumps(_lattice_elements(cfg), sort_keys=True, default=str)
    sources=("AG/alpha_coefficients.py","AG/beam_dynamics_6d.py","AG/external_forces.py","AG/runner.py",
             "AG/longitudinal_state.py","AG/beamline_sim.py","GPT模拟/ued_beamline_v2.py",
             "shared/params.py","shared/constants.py","shared/beam_physics.py",
             "shared/diagnostics.py","shared/rf_model.py","shared/beam_result.py")
    hashes={p:hashlib.sha256((repo/p).read_bytes()).hexdigest() for p in sources}
    versions={}
    for name in ('numpy','scipy','ocelot-desy'):
        try:versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:versions[name]='unavailable'
    return {
        "git_commit": git_commit,
        "config_sha": config_sha(cfg),
        "lattice_hash": hashlib.sha1(lattice.encode()).hexdigest()[:12],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "python": __import__("sys").version.split()[0],
        "random_seed": int(cfg.get("random", {}).get("seed", 0)),
        "coordinate_convention": "delta_p = dp/p0; OCELOT native p_oc = dE/(c*p0)",
        "source_sha256":hashes,
        "dependency_versions":versions,
    }
