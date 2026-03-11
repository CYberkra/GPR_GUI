import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def process_kir_images(data: np.ndarray, out_root: str, csv_name: str, contrast: float = 1.0):
    """Legacy imagesc processing placeholder adapted from original script."""
    arr = np.array(data, dtype=float)
    if arr.size == 0:
        raise ValueError("empty input for process_kir_images")

    data_min = np.min(arr)
    data_max = np.max(arr)
    if data_max > data_min:
        normalized_data = 2 * ((arr - data_min) / (data_max - data_min)) - 1
    else:
        normalized_data = arr.copy()
    normalized_data = normalized_data * float(contrast)

    out_dir = Path(out_root) / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_png_path = out_dir / f"{csv_name}_Kir.png"

    plt.figure(figsize=(10, 4))
    plt.imshow(normalized_data, aspect="auto", cmap="seismic")
    plt.colorbar()
    plt.title("Legacy Kirchhoff Image")
    plt.tight_layout()
    plt.savefig(out_png_path, dpi=150)
    plt.close()

    return {
        "png": str(out_png_path),
        "shape": tuple(normalized_data.shape),
    }
