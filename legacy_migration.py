from pathlib import Path
from typing import Any, Dict

import numpy as np

from legacy.legacy_imagesc import process_kir_images
from legacy.legacy_kir import process_kir
from legacy.legacy_tools import read_gpr_csv_arrays


def run(params: Dict[str, Any], csv_path: str):
    """Legacy migration entry: CSV -> Kirchhoff.

    RTM path intentionally left TODO in testing phase.
    """
    csv_path = str(csv_path)
    data, lon, lat, elev, flight, meta = read_gpr_csv_arrays(csv_path)

    method = str(params.get("MIG_Method", "Kir"))
    if method.upper().startswith("RTM"):
        raise NotImplementedError("Legacy RTM branch TODO")

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
