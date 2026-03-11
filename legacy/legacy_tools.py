import os
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import numpy as np
import pandas as pd


def read_param(fname, param_name):
    try:
        with open(fname, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line.startswith(param_name):
                    parts = line.split()
                    if len(parts) < 2:
                        raise ValueError(f"Invalid line format for parameter {param_name} in file: {fname}")
                    try:
                        return float(parts[1])
                    except ValueError:
                        return parts[1]
            raise ValueError(f"Parameter {param_name} not found in file: {fname}")
    except FileNotFoundError:
        raise FileNotFoundError(f"Cannot open file: {fname}")


def read_gpr_csv_arrays(
    csv_path: Union[str, Path],
    reshape_as: str = "time_rows",
    verify_samples: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, Dict[str, float]]:
    """Legacy-compatible CSV reader from original tools script."""
    csv_path = Path(csv_path)

    with csv_path.open(encoding="utf-8") as f:
        hdr = [next(f).strip() for _ in range(4)]

    _val = lambda s: s.split("=", 1)[1].split(",")[0].strip()
    meta = {
        "n_samples": int(_val(hdr[0])),
        "time_window_ns": float(_val(hdr[1])),
        "n_traces": int(_val(hdr[2])),
        "trace_interval_m": float(_val(hdr[3])),
    }
    if verify_samples is not None and meta["n_samples"] != verify_samples:
        raise ValueError(f"Number of Samples = {meta['n_samples']}, expected {verify_samples}")

    df = pd.read_csv(csv_path, skiprows=4, header=None, names=["lon", "lat", "elev", "gpr", "flight"])

    per_trace = df.groupby(df.index // meta["n_samples"]).first()
    lon = per_trace["lon"].to_numpy()
    lat = per_trace["lat"].to_numpy()
    elev = per_trace["elev"].to_numpy()
    flight = per_trace["flight"].to_numpy()

    gpr_1d = df["gpr"].to_numpy()
    expected = meta["n_samples"] * meta["n_traces"]
    if gpr_1d.size != expected:
        raise ValueError(f"Data length {gpr_1d.size} != {expected}")

    gpr_mat = gpr_1d.reshape((meta["n_traces"], meta["n_samples"]))
    if reshape_as == "time_rows":
        gpr_mat = gpr_mat.T
    elif reshape_as != "trace_rows":
        raise ValueError('reshape_as must be "time_rows" or "trace_rows"')

    return gpr_mat, lon, lat, elev, flight, meta


def ensure_legacy_workdirs(base_dir: Union[str, Path]) -> Dict[str, str]:
    root = Path(base_dir)
    image3 = root / "tools" / "image3"
    image3.mkdir(parents=True, exist_ok=True)
    results = root / "output" / "legacy_results"
    results.mkdir(parents=True, exist_ok=True)
    return {"image3": str(image3), "results": str(results), "root": str(root)}
