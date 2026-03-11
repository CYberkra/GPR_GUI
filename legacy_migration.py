from pathlib import Path
from typing import Any, Dict

import numpy as np

from legacy.legacy_imagesc import process_kir_images
from legacy.legacy_kir import process_kir
from legacy.legacy_rtm import discover_missing_rtm_dependencies, rtm_gpu
from legacy.legacy_tools import read_gpr_csv_arrays


def run(params: Dict[str, Any], csv_path: str):
    """Legacy migration entry: CSV -> Kirchhoff / RTM."""
    csv_path = str(csv_path)
    data, lon, lat, elev, flight, meta = read_gpr_csv_arrays(csv_path)

    method = str(params.get("MIG_Method", "Kir"))
    if method.upper().startswith("RTM"):
        if not bool(params.get("legacy_enable_rtm", False)):
            raise RuntimeError(
                "Legacy RTM branch is disabled by default. Set params['legacy_enable_rtm']=True to enable."
            )

        missing = discover_missing_rtm_dependencies()
        if missing:
            raise FileNotFoundError(
                "Legacy RTM dependency chain incomplete. Missing files:\n- " + "\n- ".join(missing)
            )

        # NOTE: legacy RTM needs a full parameter set; this branch only wires dispatch.
        rtm_params = dict(params.get("rtm", {}))
        migrated = rtm_gpu(data=data, **rtm_params)
    else:
        migrated = process_kir(
            data,
            dx=float(params.get("dx", meta.get("trace_interval_m", 0.05))),
            dt=float(params.get("dt", 0.1)),
            v=float(params.get("v", 0.1)),
            aperture=int(params.get("aperture", 20)),
        )

    out_root = str(Path(csv_path).parent)
    csv_name = Path(csv_path).stem
    img_info = process_kir_images(migrated, out_root=out_root, csv_name=csv_name, contrast=float(params.get("Contrast", 1.0)))

    return {
        "migrated": np.asarray(migrated),
        "meta": meta,
        "lon": lon,
        "lat": lat,
        "elev": elev,
        "flight": flight,
        "image": img_info,
    }
