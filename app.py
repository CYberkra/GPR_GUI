#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal GPR GUI prototype (Tkinter)
- Load CSV
- Display B-scan
- Select processing method (fixed order)
- Apply method (attempts to call PythonModule_core)
"""
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

import numpy as np

# matplotlib for B-scan
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# add core module path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CORE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "PythonModule_core"))
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)
# ensure local dir (for read_file_data.py)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


METHODS = [
    ("0 compensatingGain.py（人工补偿增益）", "compensatingGain", "compensatingGain"),
    ("1 dewow.py（低频漂移矫正）", "dewow", "dewow"),
    ("2 set_zero_time.py（零时矫正）", "set_zero_time", "set_zero_time"),
    ("3 agcGain.py（增益补偿矫正）", "agcGain", "agcGain"),
    ("4 subtracting_average_2D.py（背景抑制）", "subtracting_average_2D", "subtracting_average_2D"),
    ("5 running_average_2D.py（尖锐杂波抑制）", "running_average_2D", "running_average_2D"),
]


class GPRGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GPR GUI - Minimal Prototype")
        self.geometry("1100x700")

        self.data = None
        self.data_path = None

        # UI layout
        left = tk.Frame(self)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=10, pady=10)

        right = tk.Frame(self)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # controls
        tk.Button(left, text="Import CSV", command=self.load_csv, width=20).pack(pady=5)
        tk.Button(left, text="Apply Selected Method", command=self.apply_method, width=20).pack(pady=5)

        tk.Label(left, text="Methods (fixed order)").pack(pady=(15, 5))
        self.method_list = tk.Listbox(left, height=10, width=35)
        for item, _, _ in METHODS:
            self.method_list.insert(tk.END, item)
        self.method_list.selection_set(0)
        self.method_list.pack(pady=5)

        tk.Label(left, text="Info / Notes").pack(pady=(15, 5))
        self.info = tk.Text(left, height=18, width=35)
        self.info.pack(pady=5)
        self._log("Welcome. Please import a CSV to view B-scan.")

        # plot area
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

    def load_csv(self):
        path = filedialog.askopenfilename(
            title="Select CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
        )
        if not path:
            return
        try:
            data = np.loadtxt(path, delimiter=",")
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            self.data = data
            self.data_path = path
            self._log(f"Loaded CSV: {path}  shape={data.shape}")
            self.plot_data(data)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load CSV: {e}")
            self._log(f"Failed to load CSV: {e}")

    def plot_data(self, data: np.ndarray):
        self.ax.clear()
        self.ax.imshow(data, cmap="gray", aspect="auto")
        self.ax.set_title("B-scan")
        self.ax.set_xlabel("Distance (trace index)")
        self.ax.set_ylabel("Time (sample index)")
        self.canvas.draw()

    def apply_method(self):
        if self.data is None or self.data_path is None:
            messagebox.showwarning("No data", "Please import a CSV first.")
            return
        sel = self.method_list.curselection()
        if not sel:
            messagebox.showwarning("No selection", "Please select a method.")
            return
        label, module_name, func_name = METHODS[sel[0]]
        self._log(f"Applying: {label}")

        # Prepare outputs
        out_dir = os.path.join(BASE_DIR, "output")
        os.makedirs(out_dir, exist_ok=True)
        out_csv = os.path.join(out_dir, f"{module_name}_out.csv")
        out_png = os.path.join(out_dir, f"{module_name}_out.png")

        try:
            mod = __import__(module_name)
            func = getattr(mod, func_name)
        except Exception as e:
            self._log(f"Could not import {module_name}.{func_name}: {e}")
            self._log("Using raw data (no processing).")
            self.plot_data(self.data)
            return

        try:
            # Basic default params (can be refined later)
            length_trace = self.data.shape[0]
            start_position = 0
            end_position = self.data.shape[1]
            scans_per_meter = 1
            window = min(31, max(1, self.data.shape[0]//4))
            new_zero_time = min(5.0, max(0.0, length_trace * 0.1))

            # Dispatch based on function signature
            if func_name == "compensatingGain":
                gain_func = np.linspace(1, 6, self.data.shape[0]).tolist()
                func(self.data_path, out_csv, out_png, length_trace, start_position, end_position, gain_func)
            elif func_name == "dewow":
                func(self.data_path, out_csv, out_png, length_trace, start_position, scans_per_meter, window)
            elif func_name == "set_zero_time":
                func(self.data_path, out_csv, out_png, length_trace, start_position, scans_per_meter, new_zero_time)
            elif func_name == "agcGain":
                func(self.data_path, out_csv, out_png, length_trace, start_position, scans_per_meter, window)
            elif func_name == "subtracting_average_2D":
                func(self.data_path, out_csv, out_png, length_trace, start_position, scans_per_meter)
            elif func_name == "running_average_2D":
                func(self.data_path, out_csv, out_png, length_trace, start_position, scans_per_meter)
            else:
                self._log("Unknown method; no processing applied.")
                self.plot_data(self.data)
                return

            # reload processed CSV
            if os.path.exists(out_csv):
                newdata = np.loadtxt(out_csv, delimiter=",")
                if newdata.ndim == 1:
                    newdata = newdata.reshape(-1, 1)
                self.data = newdata
                self.plot_data(newdata)
                self._log(f"Processed data saved: {out_csv}")
            else:
                self._log("Processing finished but output CSV not found.")
        except Exception as e:
            self._log(f"Processing error: {e}")
            messagebox.showerror("Error", f"Processing error: {e}")


if __name__ == "__main__":
    app = GPRGui()
    app.mainloop()
