#!/usr/bin/env python3
"""Exercise shared drivers through CLI serialization and validation adapters.

These are execution-contract tests. Analytical physics checks remain in the
existing drift/solenoid/RF tests; seeded equality is not a convergence claim.
"""
import contextlib
import copy
import io
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from shared.params import load_config, config_sha
from validation.backend import run_ag, run_ocelot

FIELDS = ("z_mm", "sigma_x_um", "sigma_y_um", "sigma_z_um",
          "sigma_delta_e3", "eps_nx_mm_mrad", "eps_ny_mm_mrad")


def quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


def assert_history(result, history):
    for field in FIELDS:
        assert np.array_equal(getattr(result, field), history[field]), field


def short_config(cfg, sc=False):
    c = copy.deepcopy(cfg)
    c["beam"]["n_particles"] = 1500
    c["space_charge"].update(enabled=sc, mesh=[33, 33, 33])
    c["lattice"]["elements"] = [
        {"name": "cathode", "type": "cathode", "z_start": 0., "length": 0., "parameters": {}},
        {"name": "d1", "type": "drift", "z_start": 0., "length": .02, "parameters": {}},
        {"name": "rf1", "type": "rf_cavity", "z_start": .02, "length": .022,
         "parameters": {"frequency_GHz": 2.856, "voltage_kV": 30., "phase_rad": 3.1416}},
        {"name": "d2", "type": "drift", "z_start": .042, "length": .011, "parameters": {}},
        {"name": "sample", "type": "sample", "z_start": .053, "length": 0., "parameters": {}},
    ]
    c["output"]["z_diagnostics_mm"] = [0, 20, 22.1, 22.4, 53]
    return c


def main():
    from AG import run_shared
    from GPT模拟 import ued_beamline_v2 as model
    cfg = load_config()
    cfg["beam"]["n_particles"] = 3000
    sha = config_sha(cfg)
    with tempfile.TemporaryDirectory(prefix="ued_runner_contract_") as output:
        ag = quiet(run_ag, cfg, "full")
        ag_json = json.loads(Path(quiet(run_shared.main, out_dir=output, cfg_override=cfg)).read_text())
        assert_history(ag, ag_json["history"])
        assert ag.meta["solenoid_coupling"] is False
        assert ag.meta["runner"] == ag_json["meta"]["runner"]
        print("AG CLI saved history == validation history; default coupling=False: PASS")

        oc = quiet(run_ocelot, cfg, "full")
        oc_json = json.loads(Path(quiet(model.main, out_dir=output, cfg_override=cfg, step=4)).read_text())
        assert_history(oc, oc_json["history"])
        assert oc.meta["run_params"]["dz_track_m"] == cfg["output"]["step_size_m"]
        assert abs(oc.z_mm[-1] - 777) < 1e-9
        assert oc_json["probes"][-1]["z_exact"] is True
        print("OCELOT CLI saved history == validation history; config dz + 777-mm tail: PASS")

        short = short_config(cfg)
        for long_on, trans_on in ((False, False), (True, False), (False, True), (True, True)):
            sw = {"rf_longitudinal_kick": long_on, "rf_transverse_kick": trans_on}
            a = quiet(run_ag, short, "full", switches=sw)
            o = quiet(run_ocelot, short, "full", switches=sw)
            formal = quiet(model.run_from_config, short, switches=sw)
            assert_history(o, formal["history"])
            assert a.meta["switches"] == o.meta["switches"] == sw
            assert o.meta["rf_kicks_applied"] == int(long_on or trans_on)
            assert a.meta["rf_kicks_applied"] == int(long_on or trans_on)
        print("RF four combinations: both models share precedence; OFF count=0: PASS")

        formal = quiet(model.run_from_config, short, dz=.007)
        assert abs(formal["history"]["z_mm"][-1] - 53) < 1e-9
        assert formal["run_params"]["dz_track_m"] == .007
        assert {p["z_mm"] for p in formal["probes"]} == {0, 20, 22.1, 22.4, 53}
        event = formal["rf_events"][0]
        assert event["z_nominal_m"] == .02
        assert abs(event["z_actual_m"] - .02) < 1e-12
        print("Fractional probes distinct; explicit dz wins; RF entrance exact: PASS")

        multiple = copy.deepcopy(short)
        multiple["lattice"]["elements"].insert(3, dict(
            multiple["lattice"]["elements"][2], name="rf2", z_start=.042))
        multiple["lattice"]["elements"][4]["z_start"] = .064
        multiple["lattice"]["elements"][-1]["z_start"] = .075
        multiple["output"]["z_diagnostics_mm"] = [0, 75]
        multi = quiet(model.run_from_config, multiple)
        assert multi["rf_kicks_applied"] == 2
        assert [e["instance"] for e in multi["rf_events"]] == ["rf1", "rf2"]
        assert quiet(run_ag, multiple, "full").meta["rf_kicks_applied"] == 2
        print("Two RF instances execute once each through each model driver: PASS")

        sc_cfg = short_config(cfg, sc=True)
        sc_run = quiet(model.run_from_config, sc_cfg)
        sc_backend = quiet(run_ocelot, sc_cfg, "full")
        assert_history(sc_backend, sc_run["history"])
        assert sc_backend.meta["sc_requested"] and sc_backend.meta["sc_effective"]
        assert abs(sc_backend.meta["sc_coverage_stop_m"] - .053) < 1e-12
        lat, rf = model.build_lattice_from_shared(sc_cfg, model.STEP_ACTIVE[4], keep_zero_markers=True)
        assert quiet(model.run_beamline, lat, rf, cfg_override=sc_cfg)["sc_effective"]
        print("Omitted SC flag inherits config; native scheduler and coverage identical: PASS")

        for dz in (0, -.001, float("nan")):
            try:
                quiet(run_ocelot, short, "full", dz=dz)
            except ValueError as error:
                assert "tracking step" in str(error)
            else:
                raise AssertionError("invalid dz accepted")
        try:
            ag.at("sigma_x_um", 800)
        except ValueError as error:
            assert "outside the tracked range" in str(error)
        else:
            raise AssertionError("out-of-range interpolation silently clamped")
        assert config_sha(cfg) == sha
        print("Invalid step/out-of-range queries fail; input config unchanged: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
