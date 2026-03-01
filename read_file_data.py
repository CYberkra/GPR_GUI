#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal read_file_data.py for CSV-based workflows.
Provides: readcsv, savecsv, save_image, show_image
Includes NaN-trace handling (all-NaN columns -> 0) + nan_to_num.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import re


def _handle_nan_traces(arr: np.ndarray) -> np.ndarray:
    # Replace all-NaN traces (columns) with zeros
    if arr.ndim != 2:
        return np.nan_to_num(arr)
    col_all_nan = np.all(np.isnan(arr), axis=0)
    if np.any(col_all_nan):
        arr[:, col_all_nan] = 0.0
    # Replace remaining NaN/inf with 0
    return np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)


_HEADER_KEYS = [
    "Number of Samples",
    "Time windows",
    "Number of Traces",
    "Trace interval",
]


def _parse_header_lines(lines):
    if len(lines) < 4:
        return None
    info = {}
    for line in lines[:4]:
        if "=" not in line:
            return None
        left, right = line.split("=", 1)
        key = left.strip()
        m = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", right)
        if not m:
            return None
        try:
            val = float(m.group(0))
        except ValueError:
            return None
        info[key] = val
    if not all(k in info for k in _HEADER_KEYS):
        return None
    return {
        "a_scan_length": int(info["Number of Samples"]),
        "total_time_ns": float(info["Time windows"]),
        "num_traces": int(info["Number of Traces"]),
        "trace_interval_m": float(info["Trace interval"]),
    }


def _detect_header(path: str):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [f.readline().strip() for _ in range(4)]
    except OSError:
        return None
    return _parse_header_lines(lines)


def readcsv(path: str) -> np.ndarray:
    # Read numeric CSV, auto-skip 4-line header if present
    header_info = _detect_header(path)
    skiprows = 4 if header_info else 0
    df = pd.read_csv(path, header=None, skiprows=skiprows)
    arr = df.values.astype(float)
    return _handle_nan_traces(arr)


def savecsv(data, path: str):
    arr = np.asarray(data)
    pd.DataFrame(arr).to_csv(path, index=False, header=False)


def save_image(data, outimagename: str, title: str = '',
               time_range=None, distance_range=None):
    arr = np.asarray(data)
    plt.figure(figsize=(8, 4))
    extent = None
    if time_range is not None and distance_range is not None:
        extent = [distance_range[0], distance_range[1], time_range[1], time_range[0]]
    plt.imshow(arr, cmap='gray', aspect='auto', extent=extent)
    plt.title(title)
    plt.xlabel('Distance (m)')
    plt.ylabel('Time (ns)')
    plt.tight_layout()
    plt.savefig(outimagename, dpi=150)
    plt.close()


def show_image(data, time_range=None, distance_range=None):
    arr = np.asarray(data)
    extent = None
    if time_range is not None and distance_range is not None:
        extent = [distance_range[0], distance_range[1], time_range[1], time_range[0]]
    plt.imshow(arr, cmap='gray', aspect='auto', extent=extent)
    plt.xlabel('Distance (m)')
    plt.ylabel('Time (ns)')
    plt.show()
