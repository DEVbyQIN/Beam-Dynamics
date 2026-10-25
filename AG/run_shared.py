#!/usr/bin/env python3
"""AG CLI: run the shared AG driver and save the standard result JSON."""
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_THIS_DIR)
for p in (_REPO, _THIS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from shared.params import load_config, config_sha
from shared.output_schema import write_results
from AG.runner import run_from_config, build_regions, rf_thin_lens_H

# Compatibility alias; the shared runner uses the same round-beam default.
SOLENOID_COUPLING = False


def main(out_dir=None, cfg_override=None):
    cfg = load_config() if cfg_override is None else cfg_override
    result = run_from_config(cfg, solenoid_coupling=SOLENOID_COUPLING)
    probes = result.probes_at(cfg["output"]["z_diagnostics_mm"])
    history = result.history()
    kwargs = {"meta": result.meta}
    if out_dir is not None:
        kwargs["out_dir"] = out_dir
    path = write_results("AG", probes, history, config_sha(cfg),
                         result.meta["sc_effective"], **kwargs)
    print(f"AG done -> {path}")
    print(f"  final: sigma_x={history['sigma_x_um'][-1]:.1f} um, "
          f"sigma_z={history['sigma_z_um'][-1]:.1f} um, "
          f"eps_nx={history['eps_nx_mm_mrad'][-1]:.4f} mm.mrad")
    return path


if __name__ == "__main__":
    main()
