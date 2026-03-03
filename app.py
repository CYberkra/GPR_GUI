#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPR GUI (Enhanced)
- Load CSV
- Display B-scan
- Select processing method (original + researched)
- Configure method parameters (window width, time, rank, etc.)
"""
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np
import re

# matplotlib for B-scan
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from scipy.linalg import svd
from scipy.ndimage import uniform_filter1d
from scipy.fft import fft2, ifft2, fftshift, ifftshift

# add core module path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CORE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "PythonModule_core"))
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)
# ensure local dir (for read_file_data.py)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from read_file_data import savecsv, save_image


_HEADER_KEYS = [
    "Number of Samples",
    "Time windows",
    "Number of Traces",
    "Trace interval",
]


def _normalize_header_key(key: str) -> str:
    return (key
            .replace("Time windows (ns)", "Time windows")
            .replace("Trace interval (m)", "Trace interval"))


def _parse_header_lines(lines):
    if len(lines) < 4:
        return None
    info = {}
    for line in lines[:4]:
        if "=" not in line:
            return None
        left, right = line.split("=", 1)
        key = _normalize_header_key(left.strip())
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


def detect_csv_header(path: str):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [f.readline().strip() for _ in range(4)]
    except OSError:
        return None
    return _parse_header_lines(lines)


# ============ Methods (research) ============

def method_svd_background(data, rank=1, **kwargs):
    """SVD background removal - remove top-r singular values"""
    U, S, Vt = svd(data, full_matrices=False)
    S_bg = np.zeros_like(S)
    S_bg[:rank] = S[:rank]
    background = (U * S_bg) @ Vt
    return data - background, background


def method_fk_filter(data, angle_low=10, angle_high=65, taper_width=5, **kwargs):
    """F-K cone filter (Corrected)"""
    F = fftshift(fft2(data))
    ny, nx = F.shape
    
    # 必须将频率轴也 shift 到中心
    ky = fftshift(np.fft.fftfreq(ny))
    kx = fftshift(np.fft.fftfreq(nx))
    
    KY, KX = np.meshgrid(ky, kx, indexing='ij')
    
    # 使用绝对值角度保证左右倾斜的信号都被同等过滤
    angle = np.degrees(np.arctan2(np.abs(KY), np.abs(KX)))

    mask = np.ones_like(F)
    band_mask = (angle >= angle_low) & (angle <= angle_high)

    if taper_width > 0:
        sigma = taper_width
        for i in range(ny):
            for j in range(nx):
                if band_mask[i, j]:
                    dist_to_low = abs(angle[i, j] - angle_low)
                    dist_to_high = abs(angle[i, j] - angle_high)
                    dist = min(dist_to_low, dist_to_high)
                    if dist < taper_width:
                        mask[i, j] = 1 - np.exp(-(dist**2) / (2 * sigma**2))
                    else:
                        mask[i, j] = 0.05
    else:
        mask[band_mask] = 0.0

    F_filtered = F * mask
    result = np.real(ifft2(ifftshift(F_filtered)))
    return result, mask


def method_hankel_svd(data, window_length=None, rank=None, **kwargs):
    """Hankel SVD denoising (Corrected with Diagonal Averaging)"""
    ny, nx = data.shape
    if window_length is None or window_length <= 0:
        window_length = ny // 4
    window_length = min(window_length, ny - 1)

    result = np.zeros_like(data)
    for col in range(nx):
        trace = data[:, col]
        m = ny - window_length + 1
        if m <= 0:
            result[:, col] = trace
            continue
            
        hankel = np.zeros((m, window_length))
        for i in range(window_length):
            hankel[:, i] = trace[i:i+m]
            
        U, S, Vt = svd(hankel, full_matrices=False)
        
        if rank is None or rank <= 0:
            diff_spec = np.diff(S)
            threshold = np.mean(np.abs(diff_spec))
            rank_val = 1
            for i in range(len(diff_spec) - 2):
                if (abs(diff_spec[i]) < threshold and
                    abs(diff_spec[i+1]) < threshold):
                    rank_val = i + 1
                    break
            rank_val = max(rank_val, 1)
        else:
            rank_val = max(rank, 1)
            
        S_filtered = np.zeros_like(S)
        S_filtered[:rank_val] = S[:rank_val]
        hankel_filtered = (U * S_filtered) @ Vt
        
        # 反对角线平均 (Diagonal Averaging)
        trace_filtered = np.zeros(ny)
        counts = np.zeros(ny)
        
        for i in range(m):
            for j in range(window_length):
                trace_filtered[i + j] += hankel_filtered[i, j]
                counts[i + j] += 1
                
        trace_filtered /= counts
        result[:, col] = trace_filtered
        
    return result, None


def method_sliding_average(data, window_size=10, axis=1, **kwargs):
    """Sliding-average background removal"""
    background = uniform_filter1d(data, size=window_size, axis=axis, mode='nearest')
    return data - background, background


# ============ Method registry ============

PROCESSING_METHODS = {
    # Original methods (PythonModule_core)
    "compensatingGain": {
        "name": "0 compensatingGain (manual gain compensation)",
        "type": "core",
        "module": "compensatingGain",
        "func": "compensatingGain",
        "params": [
            {"name": "gain_min", "label": "Gain min", "type": "float", "default": 1.0, "min": 0.1, "max": 20.0},
            {"name": "gain_max", "label": "Gain max", "type": "float", "default": 6.0, "min": 0.1, "max": 50.0},
        ],
    },
    "dewow": {
        "name": "1 dewow (low-frequency drift correction)",
        "type": "core",
        "module": "dewow",
        "func": "dewow",
        "params": [
            {"name": "window", "label": "Window (samples)", "type": "int", "default": 31, "min": 1, "max": 1000},
        ],
    },
    "set_zero_time": {
        "name": "2 set_zero_time (zero-time correction)",
        "type": "core",
        "module": "set_zero_time",
        "func": "set_zero_time",
        "params": [
            {"name": "new_zero_time", "label": "Zero-time (ns)", "type": "float", "default": 5.0, "min": 0.0, "max": 1000.0},
        ],
    },
    "agcGain": {
        "name": "3 agcGain (AGC correction)",
        "type": "core",
        "module": "agcGain",
        "func": "agcGain",
        "params": [
            {"name": "window", "label": "Window (samples)", "type": "int", "default": 31, "min": 1, "max": 1000},
        ],
    },
    "subtracting_average_2D": {
        "name": "4 subtracting_average_2D (background removal)",
        "type": "core",
        "module": "subtracting_average_2D",
        "func": "subtracting_average_2D",
        "params": [],
    },
    "running_average_2D": {
        "name": "5 running_average_2D (spike clutter suppression)",
        "type": "core",
        "module": "running_average_2D",
        "func": "running_average_2D",
        "params": [],
    },

    # Research methods (local)
    "svd_bg": {
        "name": "SVD background removal (low-rank)",
        "type": "local",
        "func": method_svd_background,
        "params": [
            {"name": "rank", "label": "Rank (remove top r)", "type": "int", "default": 1, "min": 1, "max": 20},
        ],
    },
    "fk_filter": {
        "name": "F-K cone filter",
        "type": "local",
        "func": method_fk_filter,
        "params": [
            {"name": "angle_low", "label": "Stopband start angle (°)", "type": "int", "default": 10, "min": 0, "max": 90},
            {"name": "angle_high", "label": "Stopband end angle (°)", "type": "int", "default": 65, "min": 0, "max": 90},
            {"name": "taper_width", "label": "Taper width (°)", "type": "int", "default": 5, "min": 0, "max": 20},
        ],
    },
    "hankel_svd": {
        "name": "Hankel SVD denoising",
        "type": "local",
        "func": method_hankel_svd,
        "params": [
            {"name": "window_length", "label": "Window length (0=auto)", "type": "int", "default": 0, "min": 0, "max": 2000},
            {"name": "rank", "label": "Rank kept (0=auto)", "type": "int", "default": 0, "min": 0, "max": 100},
        ],
    },
    "sliding_avg": {
        "name": "Sliding-average background removal",
        "type": "local",
        "func": method_sliding_average,
        "params": [
            {"name": "window_size", "label": "Window size", "type": "int", "default": 10, "min": 1, "max": 200},
            {"name": "axis", "label": "Axis (0/1)", "type": "int", "default": 1, "min": 0, "max": 1},
        ],
    },
}


class GPRGui(tk.Tk):
    def __init__(self):
        super().__init__()
        try:
            ttk.Style().theme_use("clam")
        except Exception:
            pass
        self.title("GPR GUI - Enhanced")
        self.geometry("1200x760")

        self.data = None
        self.data_path = None
        self.header_info = None

        left = tk.Frame(self)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=10, pady=10)
        right = tk.Frame(self)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Button(left, text="Import CSV", command=self.load_csv, width=22).pack(pady=5)
        tk.Button(left, text="Apply Selected Method", command=self.apply_method, width=22).pack(pady=5)

        tk.Label(left, text="Methods").pack(pady=(15, 5))
        self.method_combo = ttk.Combobox(left, state="readonly", width=30)
        self.method_keys = list(PROCESSING_METHODS.keys())
        self.method_combo["values"] = [PROCESSING_METHODS[k]["name"] for k in self.method_keys]
        self.method_combo.current(0)
        self.method_combo.pack(pady=5)
        self.method_combo.bind("<<ComboboxSelected>>", self._on_method_change)

        tk.Label(left, text="Parameters").pack(pady=(15, 5))
        self.param_frame = tk.Frame(left)
        self.param_frame.pack(fill=tk.X, pady=5)
        self.param_vars = {}
        self._render_params(self.method_keys[0])

        tk.Label(left, text="Info / Notes").pack(pady=(15, 5))
        self.info = tk.Text(left, height=18, width=35)
        self.info.pack(pady=5)
        self._log("Welcome. Please import a CSV to view B-scan.")

        self.fig = Figure(figsize=(7, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("B-scan")
        self.ax.set_xlabel("Distance (trace index)")
        self.ax.set_ylabel("Time (sample index)")

        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _log(self, msg: str):
        self.info.insert(tk.END, msg + "\n")
        self.info.see(tk.END)

    def _on_method_change(self, event=None):
        idx = self.method_combo.current()
        key = self.method_keys[idx]
        self._render_params(key)

    def _render_params(self, method_key: str):
        for widget in self.param_frame.winfo_children():
            widget.destroy()
        self.param_vars = {}
        params = PROCESSING_METHODS[method_key].get("params", [])
        if not params:
            tk.Label(self.param_frame, text="(No parameters)").pack(anchor="w")
            return
        for p in params:
            row = tk.Frame(self.param_frame)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=p["label"], width=18, anchor="w").pack(side=tk.LEFT)
            var = tk.StringVar(value=str(p.get("default", "")))
            entry = tk.Entry(row, textvariable=var, width=12)
            entry.pack(side=tk.LEFT)
            self.param_vars[p["name"]] = (var, p)

    def _get_params(self):
        params = {}
        for name, (var, meta) in self.param_vars.items():
            raw = var.get().strip()
            if raw == "":
                raw = str(meta.get("default", ""))
            try:
                if meta["type"] == "int":
                    val = int(float(raw))
                elif meta["type"] == "float":
                    val = float(raw)
                else:
                    val = raw
            except ValueError:
                raise ValueError(f"Invalid value for {meta['label']}")
            params[name] = val
        return params

    def load_csv(self):
        path = filedialog.askopenfilename(
            title="Select CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
        )
        if not path:
            return
        try:
            header_info = detect_csv_header(path)
            if header_info:
                data = np.loadtxt(path, delimiter=",", skiprows=4)
            else:
                data = np.loadtxt(path, delimiter=",")
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            self.data = data
            self.data_path = path
            self.header_info = header_info
            self._log(f"Loaded CSV: {path}  shape={data.shape}")
            if header_info:
                self._log(
                    "Header detected: "
                    f"A-scan length={header_info['a_scan_length']} samples; "
                    f"Total time={header_info['total_time_ns']} ns; "
                    f"A-scan count={header_info['num_traces']}; "
                    f"Trace interval={header_info['trace_interval_m']} m"
                )
            else:
                self._log("No header metadata detected; using index axes.")
            self.plot_data(data)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load CSV: {e}")
            self._log(f"Failed to load CSV: {e}")

    def plot_data(self, data: np.ndarray):
        self.ax.clear()
        extent = None
        if self.header_info:
            num_traces = max(1, int(self.header_info["num_traces"]))
            trace_interval = float(self.header_info["trace_interval_m"])
            total_time = float(self.header_info["total_time_ns"])
            distance_end = trace_interval * (num_traces - 1)
            extent = [0.0, distance_end, total_time, 0.0]
            self.ax.set_xlabel("Distance (m)")
            self.ax.set_ylabel("Time (ns)")
        else:
            self.ax.set_xlabel("Distance (trace index)")
            self.ax.set_ylabel("Time (sample index)")

        self.ax.imshow(data, cmap="gray", aspect="auto", extent=extent)
        self.ax.set_title("B-scan")
        self.canvas.draw()

    def _save_outputs(self, data: np.ndarray, method_key: str):
        out_dir = os.path.join(BASE_DIR, "output")
        os.makedirs(out_dir, exist_ok=True)
        out_csv = os.path.join(out_dir, f"{method_key}_out.csv")
        out_png = os.path.join(out_dir, f"{method_key}_out.png")
        savecsv(data, out_csv)

        time_range = None
        distance_range = None
        if self.header_info:
            total_time = float(self.header_info["total_time_ns"])
            num_traces = max(1, int(self.header_info["num_traces"]))
            trace_interval = float(self.header_info["trace_interval_m"])
            distance_end = trace_interval * (num_traces - 1)
            time_range = (0.0, total_time)
            distance_range = (0.0, distance_end)

        save_image(data, out_png, title=method_key, time_range=time_range, distance_range=distance_range)
        return out_csv, out_png

    def apply_method(self):
        if self.data is None or self.data_path is None:
            messagebox.showwarning("No data", "Please import a CSV first.")
            return
        idx = self.method_combo.current()
        method_key = self.method_keys[idx]
        method = PROCESSING_METHODS[method_key]
        self._log(f"Applying: {method['name']}")

        try:
            params = self._get_params()
        except ValueError as e:
            messagebox.showerror("Invalid parameter", str(e))
            return

        out_dir = os.path.join(BASE_DIR, "output")
        os.makedirs(out_dir, exist_ok=True)
        out_csv = os.path.join(out_dir, f"{method_key}_out.csv")
        out_png = os.path.join(out_dir, f"{method_key}_out.png")

        try:
            if method["type"] == "core":
                mod = __import__(method["module"])
                func = getattr(mod, method["func"])
                length_trace = self.data.shape[0]
                start_position = 0
                end_position = self.data.shape[1]
                scans_per_meter = 1

                if method_key == "compensatingGain":
                    gain_min = float(params.get("gain_min", 1.0))
                    gain_max = float(params.get("gain_max", 6.0))
                    gain_func = np.linspace(gain_min, gain_max, self.data.shape[0]).tolist()
                    func(self.data_path, out_csv, out_png, length_trace, start_position, end_position, gain_func)
                elif method_key == "dewow":
                    window = int(params.get("window", max(1, length_trace // 4)))
                    func(self.data_path, out_csv, out_png, length_trace, start_position, scans_per_meter, window)
                elif method_key == "set_zero_time":
                    new_zero_time = float(params.get("new_zero_time", 5.0))
                    func(self.data_path, out_csv, out_png, length_trace, start_position, scans_per_meter, new_zero_time)
                elif method_key == "agcGain":
                    window = int(params.get("window", max(1, length_trace // 4)))
                    func(self.data_path, out_csv, out_png, length_trace, start_position, scans_per_meter, window)
                elif method_key == "subtracting_average_2D":
                    func(self.data_path, out_csv, out_png, length_trace, start_position, scans_per_meter)
                elif method_key == "running_average_2D":
                    func(self.data_path, out_csv, out_png, length_trace, start_position, scans_per_meter)
                else:
                    self._log("Unknown core method; no processing applied.")
                    self.plot_data(self.data)
                    return

                if os.path.exists(out_csv):
                    newdata = np.loadtxt(out_csv, delimiter=",")
                    if newdata.ndim == 1:
                        newdata = newdata.reshape(-1, 1)
                    self.data = newdata
                    self.plot_data(newdata)
                    self._log(f"Processed data saved: {out_csv}")
                else:
                    self._log("Processing finished but output CSV not found.")
            else:
                result = method["func"](self.data, **params)
                if isinstance(result, tuple):
                    newdata = result[0]
                else:
                    newdata = result
                self.data = newdata
                self.plot_data(newdata)
                out_csv, out_png = self._save_outputs(newdata, method_key)
                self._log(f"Processed data saved: {out_csv}")
        except Exception as e:
            self._log(f"Processing error: {e}")
            messagebox.showerror("Error", f"Processing error: {e}")


if __name__ == "__main__":
    app = GPRGui()
    app.mainloop()