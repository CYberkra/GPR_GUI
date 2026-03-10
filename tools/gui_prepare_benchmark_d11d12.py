#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "tests" / "regression_samples_manifest.json"


def load_samples():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = []
    for s in manifest["samples"]:
        p = REPO / s["path"]
        arr = pd.read_csv(p, header=None, na_filter=False, low_memory=False).values.astype(float)
        rows.append((s["id"], arr))
    return rows


def _downsample_old(data: np.ndarray, max_samples: int, max_traces: int) -> np.ndarray:
    n_time, n_dist = data.shape
    t_step = max(1, int(np.ceil(n_time / max_samples))) if max_samples > 0 else 1
    d_step = max(1, int(np.ceil(n_dist / max_traces))) if max_traces > 0 else 1
    t_idx = np.arange(0, n_time, t_step, dtype=int)
    d_idx = np.arange(0, n_dist, d_step, dtype=int)
    return data[t_idx, :][:, d_idx]


def _downsample_new(data: np.ndarray, max_samples: int, max_traces: int) -> np.ndarray:
    n_time, n_dist = data.shape
    t_step = max(1, int(np.ceil(n_time / max_samples))) if max_samples > 0 else 1
    d_step = max(1, int(np.ceil(n_dist / max_traces))) if max_traces > 0 else 1
    t_idx = np.arange(0, n_time, t_step, dtype=int)
    d_idx = np.arange(0, n_dist, d_step, dtype=int)
    return data[np.ix_(t_idx, d_idx)]


def prepare_old(data: np.ndarray) -> np.ndarray:
    x = np.nan_to_num(data)
    return _downsample_old(x, max_samples=160, max_traces=64)


def prepare_new(data: np.ndarray) -> np.ndarray:
    arr = np.asarray(data)
    if np.isfinite(arr).all():
        x = arr
    else:
        x = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    return _downsample_new(x, max_samples=160, max_traces=64)


def bench(fn, data, repeat=30):
    best = float("inf")
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn(data)
        dt = (time.perf_counter() - t0) * 1000.0
        if dt < best:
            best = dt
    return best


def main():
    samples = load_samples()
    old_total = 0.0
    new_total = 0.0
    print("sample,old_ms,new_ms,speedup")
    for sid, data in samples:
        old_ms = bench(prepare_old, data)
        new_ms = bench(prepare_new, data)
        old_total += old_ms
        new_total += new_ms
        speedup = old_ms / max(new_ms, 1e-9)
        print(f"{sid},{old_ms:.4f},{new_ms:.4f},{speedup:.3f}x")

    n = max(1, len(samples))
    print(f"TOTAL old={old_total:.4f}ms new={new_total:.4f}ms speedup={old_total/max(new_total,1e-9):.3f}x")
    print(f"AVG   old={old_total/n:.4f}ms new={new_total/n:.4f}ms speedup={(old_total/n)/max(new_total/n,1e-9):.3f}x")


if __name__ == "__main__":
    main()
