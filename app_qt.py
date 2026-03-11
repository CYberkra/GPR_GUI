#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPR GUI (PyQt6 + themed)
- Load CSV
- Display B-扫 (matplotlib)
- Select processing method (original + researched)
- Configure method parameters
- 撤销/重置 history
- Display downsample + colorbar/grid toggles
- Batch compare + report (with settings + log)
"""
import os
import sys
import re
import time
import subprocess
from datetime import datetime

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("QtAgg")
from matplotlib import font_manager as fm
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from scipy.linalg import svd
from scipy.ndimage import uniform_filter1d
from scipy.fft import fft2, ifft2, fftshift, ifftshift
from scipy.interpolate import interp1d

from PyQt6.QtCore import Qt, QObject, QThread, QTimer, QSignalBlocker, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QFormLayout,
    QGroupBox,
    QScrollArea,
    QSplitter,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QCheckBox,
    QFileDialog,
    QMessageBox,
)

# add core module path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CORE_DIR_CANDIDATES = [
    os.path.abspath(os.path.join(BASE_DIR, "..", "PythonModule_core")),
    os.path.abspath(os.path.join(BASE_DIR, "..", "..", "repos", "PythonModule_core")),
]
for _p in CORE_DIR_CANDIDATES:
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

# ensure local dir (for read_file_data.py)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# read_file_data fallback
_read_file_candidates = [
    BASE_DIR,
    os.path.abspath(os.path.join(BASE_DIR, "..", "..", "repos", "GPR_GUI")),
    os.path.abspath(os.path.join(BASE_DIR, "..", "..", "repos", "PythonModule")),
]
for _p in _read_file_candidates:
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

from gpr_io import savecsv, save_image

try:
    import legacy_migration
except Exception:
    legacy_migration = None

_CORE_FUNC_CACHE = {}


def _format_explainable_error(what_happened: str, possible_causes: list, next_steps: list, technical_detail: str = "") -> str:
    lines = [
        f"发生了什么：{what_happened}",
        "可能原因：",
    ]
    for i, item in enumerate(possible_causes[:2], start=1):
        lines.append(f"  {i}. {item}")
    lines.append("下一步建议：")
    for i, item in enumerate(next_steps, start=1):
        lines.append(f"  {i}. {item}")
    if technical_detail:
        lines.append(f"技术详情：{technical_detail}")
    return "\n".join(lines)


def build_csv_load_error_message(err: Exception) -> str:
    return _format_explainable_error(
        what_happened="CSV 加载失败或格式不符合预期。",
        possible_causes=[
            "文件内容不是纯数值矩阵（包含文本、分隔符异常或空行过多）。",
            "CSV 编码/结构异常，导致读取后数据为空或维度不正确。",
        ],
        next_steps=[
            "用 Excel/文本编辑器确认分隔符与列结构一致，并另存为标准 UTF-8 CSV。",
            "先抽取前 50 行做小样本导入，确认可读后再导入完整文件。",
        ],
        technical_detail=str(err),
    )


def build_param_error_message(label: str, raw_value: str, detail: str) -> str:
    return _format_explainable_error(
        what_happened=f"参数“{label}”无效。",
        possible_causes=[
            "输入为空，或类型与参数要求不一致（例如应为数字却输入了文本）。",
            "参数值超出允许范围。",
        ],
        next_steps=[
            "按参数提示输入有效数值，并避免空值。",
            "若不确定，请恢复默认值后重试。",
        ],
        technical_detail=f"输入值={raw_value!r}；{detail}",
    )


def build_processing_error_message(err: Exception, method_name: str = "未知方法") -> str:
    return _format_explainable_error(
        what_happened=f"处理流程在“{method_name}”步骤执行失败。",
        possible_causes=[
            "worker 执行阶段收到非法输入或中间结果异常。",
            "方法调用失败（依赖函数报错或输出文件未生成）。",
        ],
        next_steps=[
            "先用单步处理验证该方法，再检查参数设置是否合理。",
            "查看日志中的技术详情，必要时切换到其他方法确认数据本身是否可处理。",
        ],
        technical_detail=str(err),
    )


def _read_first_existing_text(paths):
    for path in paths:
        try:
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8-sig") as f:
                    text = f.read().strip()
                if text:
                    return text
        except Exception:
            continue
    return None


def _get_git_short_sha(base_dir: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", base_dir, "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return proc.stdout.strip() or "nogit"
    except Exception:
        return "nogit"


def build_version_string(app_name: str = "GPR_GUI") -> str:
    release_candidates = [
        os.path.join(BASE_DIR, "dist", "RELEASE_VERSION.txt"),
        os.path.join(os.path.dirname(BASE_DIR), "dist", "RELEASE_VERSION.txt"),
        os.path.join(BASE_DIR, "RELEASE_VERSION.txt"),
        os.path.join(BASE_DIR, "VERSION"),
    ]
    release = _read_first_existing_text(release_candidates)
    shortsha = _get_git_short_sha(BASE_DIR)
    if release:
        return f"{app_name} {release} ({shortsha})"
    stamp = datetime.now().strftime("%Y%m%d")
    return f"{app_name} dev-{stamp} ({shortsha})"


def _configure_matplotlib_cjk_fonts() -> None:
    """Configure a safe CJK font fallback chain for Matplotlib titles/labels."""
    preferred_fonts = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "PingFang SC",
        "WenQuanYi Zen Hei",
        "Arial Unicode MS",
    ]
    try:
        installed = {f.name for f in fm.fontManager.ttflist}
    except Exception:
        installed = set()

    available = [name for name in preferred_fonts if name in installed]
    # Keep DejaVu Sans in the tail for ASCII/number glyph safety.
    fallback_chain = available + ["DejaVu Sans"]

    try:
        matplotlib.rcParams["font.sans-serif"] = fallback_chain
        matplotlib.rcParams["font.family"] = "sans-serif"
        # Avoid minus sign rendering issues under some CJK fonts on Windows.
        matplotlib.rcParams["axes.unicode_minus"] = False
    except Exception:
        # Safe downgrade: if rcParams update fails, keep defaults without crashing.
        pass


def _get_core_func(module_name: str, func_name: str):
    key = (module_name, func_name)
    fn = _CORE_FUNC_CACHE.get(key)
    if fn is None:
        mod = __import__(module_name)
        fn = getattr(mod, func_name)
        _CORE_FUNC_CACHE[key] = fn
    return fn


def _read_matrix_csv_fast(path: str) -> np.ndarray:
    """CSV matrix reader optimized for dense numeric GPR outputs."""
    try:
        df = pd.read_csv(path, header=None, na_filter=False, low_memory=False)
        return df.values
    except Exception:
        arr = np.loadtxt(path, delimiter=",", dtype=float)
        if arr.ndim == 1:
            arr = arr.reshape(-1, 1)
        return arr


def _downsample_axis_linear(n: int, max_n: int):
    if max_n <= 0 or n <= max_n:
        return slice(None)
    return np.linspace(0, n - 1, max_n, dtype=int)


# ------------------ CSV header parsing ------------------
_HEADER_KEYS = [
    "Number of Samples",
    "Time windows (ns)",
    "Number of Traces",
    "Trace interval (m)",
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
        "total_time_ns": float(info["Time windows (ns)"]),
        "num_traces": int(info["Number of Traces"]),
        "trace_interval_m": float(info["Trace interval (m)"]),
    }


def detect_csv_header(path: str):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [f.readline().strip() for _ in range(4)]
    except OSError:
        return None
    return _parse_header_lines(lines)


def _is_numeric_row(line: str) -> bool:
    parts = [p.strip() for p in line.split(",")]
    has_num = False
    for p in parts:
        if p == "":
            continue
        try:
            float(p)
            has_num = True
        except ValueError:
            return False
    return has_num


def _detect_skiprows(path: str, max_lines: int = 10) -> int:
    skip = 0
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for _ in range(max_lines):
                line = f.readline()
                if not line:
                    break
                if _is_numeric_row(line.strip()):
                    break
                skip += 1
    except OSError:
        return 0
    return skip


def _select_amp_column(raw_data: np.ndarray) -> int:
    # Prefer column D (index=3) for 5-column CSVs used by UAV-GPR
    if raw_data.shape[1] > 3:
        return 3
    return raw_data.shape[1] - 1


# ------------------ Research methods ------------------

def method_svd_background(data, rank=1, **kwargs):
    U, S, Vt = svd(data, full_matrices=False)
    S_bg = np.zeros_like(S)
    S_bg[:rank] = S[:rank]
    background = (U * S_bg) @ Vt
    return data - background, background


def method_fk_filter(data, angle_low=10, angle_high=65, taper_width=5, **kwargs):
    F = fftshift(fft2(data))
    ny, nx = F.shape

    ky = fftshift(np.fft.fftfreq(ny))
    kx = fftshift(np.fft.fftfreq(nx))

    KY, KX = np.meshgrid(ky, kx, indexing='ij')
    angle = np.degrees(np.arctan2(np.abs(KY), np.abs(KX)))

    band_mask = (angle >= angle_low) & (angle <= angle_high)
    mask = np.ones_like(angle, dtype=float)

    if taper_width > 0:
        sigma = taper_width
        dist_to_low = np.abs(angle - angle_low)
        dist_to_high = np.abs(angle - angle_high)
        dist = np.minimum(dist_to_low, dist_to_high)

        mask[band_mask] = 0.05
        taper_region = band_mask & (dist < taper_width)
        if np.any(taper_region):
            mask[taper_region] = 1 - np.exp(-(dist[taper_region] ** 2) / (2 * sigma ** 2))
    else:
        mask[band_mask] = 0.0

    F_filtered = F * mask
    result = np.real(ifft2(ifftshift(F_filtered)))
    return result, mask


def method_hankel_svd(data, window_length=None, rank=None, **kwargs):
    ny, nx = data.shape
    if window_length is None or window_length <= 0:
        window_length = ny // 4
    window_length = min(window_length, ny - 1)

    result = np.zeros_like(data)
    m = ny - window_length + 1

    counts = np.zeros(ny)
    if m > 0:
        for j in range(window_length):
            counts[j:j + m] += 1

    for col in range(nx):
        trace = data[:, col]
        if m <= 0:
            result[:, col] = trace
            continue

        hankel = np.zeros((m, window_length))
        for i in range(window_length):
            hankel[:, i] = trace[i:i + m]

        U, S, Vt = svd(hankel, full_matrices=False)

        if rank is None or rank <= 0:
            diff_spec = np.diff(S)
            threshold = np.mean(np.abs(diff_spec))
            rank_val = 1
            for i in range(len(diff_spec) - 2):
                if (abs(diff_spec[i]) < threshold and
                        abs(diff_spec[i + 1]) < threshold):
                    rank_val = i + 1
                    break
            rank_val = max(rank_val, 1)
        else:
            rank_val = max(rank, 1)

        S_filtered = np.zeros_like(S)
        S_filtered[:rank_val] = S[:rank_val]
        hankel_filtered = (U * S_filtered) @ Vt

        trace_filtered = np.zeros(ny)
        for j in range(window_length):
            trace_filtered[j:j + m] += hankel_filtered[:, j]

        result[:, col] = trace_filtered / counts

    return result, None


def method_sliding_average(data, window_size=10, axis=1, **kwargs):
    background = uniform_filter1d(data, size=window_size, axis=axis, mode='nearest')
    return data - background, background


def method_kirchhoff_migration(data, dx=0.05, dt=0.1, v=0.10, aperture=20, **kwargs):
    """Kirchhoff 积分迁移 (向量化加速版, stage1 参数映射 + stage2 插值/权重升级)."""
    arr = np.array(data, dtype=float, copy=True)
    ny, nx = arr.shape
    migrated = np.zeros_like(arr)

    # --- stage1: map txt/tzt params into migration path ---
    time_window = max(1, int(float(kwargs.get("T", ny))))
    depth_limit = max(1, int(float(kwargs.get("M-depth", ny))))
    line_len = max(1, int(float(kwargs.get("len", nx))))
    weight = float(kwargs.get("weight", 1.0))
    contrast = float(kwargs.get("Contrast", 1.0))
    linear_interp = int(float(kwargs.get("linear_interp", 1))) != 0

    topo_cor = int(float(kwargs.get("topo_cor", 0))) != 0
    hei_cor = int(float(kwargs.get("hei_cor", 0))) != 0
    interface = int(float(kwargs.get("interface", 0))) != 0

    ny_eff = min(ny, time_window)
    depth_eff = min(ny_eff, depth_limit)

    # len -> spacing scale mapping (line shorter -> tighter spacing, longer -> wider spacing)
    dx_scale = float(nx) / float(line_len) if line_len > 0 else 1.0

    # lightweight corrections gated by switches (non-destructive stage1)
    if topo_cor and ny > 0:
        arr = arr - arr[0:1, :]
    if hei_cor:
        depth_axis = np.linspace(0.0, 1.0, ny, endpoint=True)
        arr = arr * (0.9 + 0.1 * depth_axis[:, None])

    t = np.arange(ny_eff) * dt
    if ny_eff > 0:
        t[0] = 1e-6
    t0_sq = t ** 2

    for ix in range(nx):
        start_tr = max(0, ix - int(aperture))
        end_tr = min(nx, ix + int(aperture) + 1)

        dist = (np.arange(start_tr, end_tr) - ix) * dx * dx_scale
        dx_term = 4 * (dist ** 2) / (v ** 2)

        t_travel = np.sqrt(t0_sq[:, None] + dx_term[None, :])
        t_pos = t_travel / dt

        # stage2: sub-sample interpolation + offset-aware weighting
        trace_offsets = np.abs(np.arange(start_tr, end_tr) - ix).astype(float)
        if trace_offsets.size > 0:
            taper = 1.0 - (trace_offsets / (float(aperture) + 1.0))
            taper = np.clip(taper, 0.15, 1.0)
        else:
            taper = np.array([], dtype=float)
        geom = 1.0 / np.sqrt(1.0 + dx_term)
        trace_weights = taper * geom

        for i_d, tr in enumerate(range(start_tr, end_tr)):
            row_ids = np.arange(depth_eff)
            if row_ids.size == 0:
                continue

            pos = t_pos[row_ids, i_d]
            valid = (pos >= 0.0) & (pos < (ny_eff - 1))
            if not np.any(valid):
                continue

            rows = row_ids[valid]
            pos_v = pos[valid]
            if linear_interp:
                i0 = np.floor(pos_v).astype(int)
                frac = pos_v - i0
                i1 = np.minimum(i0 + 1, ny_eff - 1)

                s0 = arr[i0, tr]
                s1 = arr[i1, tr]
                sampled = (1.0 - frac) * s0 + frac * s1
            else:
                i_nn = np.rint(pos_v).astype(int)
                i_nn = np.clip(i_nn, 0, ny_eff - 1)
                sampled = arr[i_nn, tr]

            migrated[rows, ix] += weight * trace_weights[i_d] * sampled

    if interface:
        migrated = np.abs(np.gradient(migrated, axis=0))

    migrated *= contrast
    return migrated, {
        "mapped_params": {
            "T": time_window,
            "M-depth": depth_limit,
            "len": line_len,
            "weight": weight,
            "Contrast": contrast,
            "linear_interp": int(linear_interp),
            "topo_cor": int(topo_cor),
            "hei_cor": int(hei_cor),
            "interface": int(interface),
        }
    }


def method_time_to_depth(data, dt=0.1, v=0.10, dz=0.02, **kwargs):
    """深度转换与标定"""
    ny, nx = data.shape
    t = np.arange(ny) * dt
    z_old = t * v / 2.0

    z_max = z_old[-1] if ny > 0 else 0.0
    num_z = int(z_max / dz) + 1 if dz > 0 else ny
    z_new = np.linspace(0, z_max, max(num_z, 1))

    f = interp1d(z_old, data, axis=0, bounds_error=False, fill_value=0.0)
    depth_data = f(z_new)
    return depth_data, {"is_depth": True, "z_max": z_max}


# ------------------ Method registry ------------------


def method_sec_gain(data, gain_min=1.0, gain_max=6.0, power=1.0, **kwargs):
    # Simple SEC gain: apply depth-dependent gain curve
    arr = data.astype(float)
    n = arr.shape[0]
    t = (np.linspace(0, 1, n) ** max(power, 1e-6))
    gain = gain_min + (gain_max - gain_min) * t
    return arr * gain[:, None], gain
TZT_MIGRATION_DEFAULTS = {
    "SFCW": 0,
    "freq": 50e6,
    "len": 122,
    "M-depth": 40,
    "T": 800,
    "v": 0.1,
    "num_cal": 1,
    "formatString": "C:/Users/Hzory/Desktop/testN6/data.csv",
    "MIG_Method": "Kir",
    "interface": 0,
    "topo_cor": 1,
    "hei_cor": 1,
    "Drill": 0,
    "Contrast": 1,
    "weight": 0.5,
    "ini_model": 0,
    "gpu_index": 0,
}

KIRCHHOFF_APPLIED_FIELDS = {
    "dx", "dt", "v", "aperture",
    "len", "M-depth", "T", "weight", "Contrast",
    "interface", "topo_cor", "hei_cor",
}
KIRCHHOFF_STORED_ONLY_FIELDS = {
    "SFCW", "freq", "num_cal", "formatString", "MIG_Method",
    "Drill", "ini_model", "gpu_index",
}

PROCESSING_METHODS = {
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
            {"name": "window", "label": "Window (samples)", "type": "int", "default": 41, "min": 1, "max": 1000},
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
            {"name": "angle_low", "label": "Stopband start angle (°)", "type": "int", "default": 12, "min": 0, "max": 90},
            {"name": "angle_high", "label": "Stopband end angle (°)", "type": "int", "default": 55, "min": 0, "max": 90},
            {"name": "taper_width", "label": "Taper width (°)", "type": "int", "default": 4, "min": 0, "max": 20},
        ],
    },
    "hankel_svd": {
        "name": "Hankel SVD denoising",
        "type": "local",
        "func": method_hankel_svd,
        "params": [
            {"name": "window_length", "label": "Window length (0=auto)", "type": "int", "default": 80, "min": 0, "max": 2000},
            {"name": "rank", "label": "Rank kept (0=auto)", "type": "int", "default": 2, "min": 0, "max": 100},
        ],
    },
    
    
    "rpca_placeholder": {
        "name": "RPCA背景抑制（占位）",
        "type": "local",
        "func": lambda d, **k: d,
        "params": [
            {"name": "lambda", "label": "稀疏权重", "type": "float", "default": 0.5, "min": 0.01, "max": 1.0},
        ],
    },
    "wnnm_placeholder": {
        "name": "WNNM背景抑制（占位）",
        "type": "local",
        "func": lambda d, **k: d,
        "params": [
            {"name": "sigma", "label": "噪声方差", "type": "float", "default": 0.1, "min": 0.0, "max": 10.0},
        ],
    },

    "kirchhoff_migration": {
        "name": "Kirchhoff 迁移 (目标聚焦)",
        "type": "local",
        "func": method_kirchhoff_migration,
        "params": [
            {"name": "dx", "label": "道间距 (m)", "type": "float", "default": 0.05, "min": 0.001, "max": 10.0},
            {"name": "dt", "label": "时间步长 (ns)", "type": "float", "default": 0.1, "min": 0.01, "max": 10.0},
            {"name": "v", "label": "波速 (m/ns)", "type": "float", "default": 0.10, "min": 0.01, "max": 0.3},
            {"name": "aperture", "label": "孔径 (单侧道数)", "type": "int", "default": 20, "min": 1, "max": 200},
            {"name": "SFCW", "label": "SFCW", "type": "int", "default": 0, "min": 0, "max": 1},
            {"name": "freq", "label": "频率(Hz)", "type": "float", "default": 50e6, "min": 1.0, "max": 1e12},
            {"name": "len", "label": "长度(len)", "type": "int", "default": 122, "min": 1, "max": 100000},
            {"name": "M-depth", "label": "迁移深度(M-depth)", "type": "int", "default": 40, "min": 1, "max": 100000},
            {"name": "T", "label": "时间窗口T", "type": "int", "default": 800, "min": 1, "max": 10000000},
            {"name": "num_cal", "label": "num_cal", "type": "int", "default": 1, "min": 0, "max": 1000},
            {"name": "formatString", "label": "formatString", "type": "str", "default": "C:/Users/Hzory/Desktop/testN6/data.csv"},
            {"name": "MIG_Method", "label": "MIG_Method", "type": "str", "default": "Kir"},
            {"name": "interface", "label": "interface", "type": "int", "default": 0, "min": 0, "max": 1},
            {"name": "topo_cor", "label": "topo_cor", "type": "int", "default": 1, "min": 0, "max": 1},
            {"name": "hei_cor", "label": "hei_cor", "type": "int", "default": 1, "min": 0, "max": 1},
            {"name": "Drill", "label": "Drill", "type": "int", "default": 0, "min": 0, "max": 1},
            {"name": "Contrast", "label": "Contrast", "type": "int", "default": 1, "min": 0, "max": 1},
            {"name": "weight", "label": "weight", "type": "float", "default": 0.5, "min": 0.0, "max": 10.0},
            {"name": "ini_model", "label": "ini_model", "type": "int", "default": 0, "min": 0, "max": 1000},
            {"name": "gpu_index", "label": "gpu_index", "type": "int", "default": 0, "min": 0, "max": 16},
        ],
    },
    "time_to_depth": {
        "name": "深度转换与标定",
        "type": "local",
        "func": method_time_to_depth,
        "params": [
            {"name": "dt", "label": "时间步长 (ns)", "type": "float", "default": 0.1, "min": 0.01, "max": 10.0},
            {"name": "v", "label": "波速 (m/ns)", "type": "float", "default": 0.10, "min": 0.01, "max": 0.3},
            {"name": "dz", "label": "深度网格步长 (m)", "type": "float", "default": 0.02, "min": 0.001, "max": 1.0},
        ],
    },
"sec_gain": {
        "name": "SEC增益（深度补偿）",
        "type": "local",
        "func": method_sec_gain,
        "params": [
            {"name": "gain_min", "label": "增益下限", "type": "float", "default": 1.0, "min": 0.1, "max": 10.0},
            {"name": "gain_max", "label": "增益上限", "type": "float", "default": 4.5, "min": 0.1, "max": 20.0},
            {"name": "power", "label": "曲线幂次", "type": "float", "default": 1.1, "min": 0.2, "max": 3.0},
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




METHOD_DISPLAY_NAMES = {
    "set_zero_time": "1. 时间零点校正（time-zero）",
    "dewow": "2. 去直流/去漂移（dewow）",
    "subtracting_average_2D": "3. 背景去除（mean）",
    "fk_filter": "4. 频带滤波（F-K）",
    "sec_gain": "5. 增益（SEC，推荐）",
    "hankel_svd": "6. 去噪（Hankel-SVD）",
    "kirchhoff_migration": "7. 迁移（Kirchhoff）",
    "time_to_depth": "8. 深度转换与标定",
    "agcGain": "9. 增益（AGC，备选）",
    "svd_bg": "10. 背景去除（SVD，备选）",
    "rpca_placeholder": "11. 背景去除（RPCA，占位）",
    "wnnm_placeholder": "12. 背景去除（WNNM，占位）",
    "sliding_avg": "13. 滑动平均背景去除（与步骤3重复）",
    "running_average_2D": "14. 运行平均抑噪（与步骤6重复）",
    "compensatingGain": "15. 增益补偿（与步骤5/9重复）",
}

PREFERRED_METHOD_ORDER = [
    "set_zero_time", "dewow", "subtracting_average_2D", "fk_filter", "sec_gain", "hankel_svd",
    "kirchhoff_migration", "time_to_depth",
    "agcGain", "svd_bg", "rpca_placeholder", "wnnm_placeholder",
    "sliding_avg", "running_average_2D", "compensatingGain",
]

METHOD_TAGS = {
    "subtracting_average_2D": "推荐",
    "agcGain": "推荐",
    "dewow": "推荐",
    "set_zero_time": "推荐",
    "svd_bg": "推荐",
    "fk_filter": "实验",
    "hankel_svd": "实验",
    "sliding_avg": "实验",
}


GUI_PRESETS_V1 = {
    "quick_preview": {
        "label": "快速预览（速度优先）",
        "ui": {
            "fast_preview": True,
            "max_samples": 256,
            "max_traces": 120,
            "display_downsample": True,
            "display_max_samples": 500,
            "display_max_traces": 260,
            "normalize": False,
            "demean": False,
            "percentile": False,
        },
        "method_params": {
            "set_zero_time": {"new_zero_time": 4.0},
            "dewow": {"window": 21},
            "fk_filter": {"angle_low": 16, "angle_high": 45, "taper_width": 3},
            "sec_gain": {"gain_min": 1.0, "gain_max": 3.2, "power": 1.0},
            "hankel_svd": {"window_length": 48, "rank": 1},
        },
    },
    "denoise_first": {
        "label": "降噪优先（稳健）",
        "ui": {
            "fast_preview": False,
            "display_downsample": True,
            "display_max_samples": 900,
            "display_max_traces": 420,
            "normalize": True,
            "demean": True,
            "percentile": True,
            "p_low": 1.0,
            "p_high": 99.0,
        },
        "method_params": {
            "set_zero_time": {"new_zero_time": 5.0},
            "dewow": {"window": 61},
            "fk_filter": {"angle_low": 12, "angle_high": 55, "taper_width": 4},
            "sec_gain": {"gain_min": 1.0, "gain_max": 4.2, "power": 1.2},
            "hankel_svd": {"window_length": 96, "rank": 2},
        },
    },
    "detail_first": {
        "label": "保细节（细节优先）",
        "ui": {
            "fast_preview": False,
            "display_downsample": False,
            "normalize": False,
            "demean": True,
            "percentile": True,
            "p_low": 0.5,
            "p_high": 99.5,
        },
        "method_params": {
            "set_zero_time": {"new_zero_time": 4.5},
            "dewow": {"window": 31},
            "fk_filter": {"angle_low": 8, "angle_high": 62, "taper_width": 2},
            "sec_gain": {"gain_min": 1.0, "gain_max": 5.0, "power": 1.05},
            "hankel_svd": {"window_length": 72, "rank": 3},
        },
    },
}


class ProcessingWorker(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int, str)

    def __init__(self, base_data: np.ndarray, tasks: list, base_csv_path: str = None):
        super().__init__()
        self.base_data = np.array(base_data, copy=True)
        self.tasks = tasks
        self.base_csv_path = base_csv_path

    def run(self):
        current_data = np.array(self.base_data, copy=True)
        outputs = []
        total = len(self.tasks)
        current_method_name = "未知方法"
        try:
            for i, task in enumerate(self.tasks, start=1):
                method_key = task["method_key"]
                method = task["method"]
                current_method_name = method.get("name", method_key)
                params = task.get("params", {})
                out_dir = task["out_dir"]

                self.progress.emit(i - 1, total, f"处理中 ({i}/{total}): {method['name']}")

                if method["type"] == "core":
                    func = _get_core_func(method["module"], method["func"])
                    length_trace = current_data.shape[0]
                    start_position = 0
                    end_position = current_data.shape[1]
                    scans_per_meter = 1

                    temp_in_csv = os.path.join(out_dir, "__tmp_in.csv")
                    out_csv = os.path.join(out_dir, f"__tmp_{i}_{method_key}_out.csv")
                    out_png = os.path.join(out_dir, f"__tmp_{i}_{method_key}_out.png")
                    savecsv(current_data, temp_in_csv)

                    if method_key == "compensatingGain":
                        gain_min = float(params.get("gain_min", 1.0))
                        gain_max = float(params.get("gain_max", 6.0))
                        gain_func = np.linspace(gain_min, gain_max, current_data.shape[0]).tolist()
                        func(temp_in_csv, out_csv, out_png, length_trace, start_position, end_position, gain_func)
                    elif method_key == "dewow":
                        window = int(params.get("window", max(1, length_trace // 4)))
                        func(temp_in_csv, out_csv, out_png, length_trace, start_position, scans_per_meter, window)
                    elif method_key == "set_zero_time":
                        new_zero_time = float(params.get("new_zero_time", 5.0))
                        func(temp_in_csv, out_csv, out_png, length_trace, start_position, scans_per_meter, new_zero_time)
                    elif method_key == "agcGain":
                        window = int(params.get("window", max(1, length_trace // 4)))
                        func(temp_in_csv, out_csv, out_png, length_trace, start_position, scans_per_meter, window)
                    elif method_key == "subtracting_average_2D":
                        func(temp_in_csv, out_csv, out_png, length_trace, start_position, scans_per_meter)
                    elif method_key == "running_average_2D":
                        func(temp_in_csv, out_csv, out_png, length_trace, start_position, scans_per_meter)
                    else:
                        raise RuntimeError(f"Unknown core method: {method_key}")

                    if not os.path.exists(out_csv):
                        raise RuntimeError(f"Output CSV not found: {out_csv}")
                    newdata = _read_matrix_csv_fast(out_csv)
                    if newdata.ndim == 1:
                        newdata = newdata.reshape(-1, 1)
                else:
                    if method_key == "kirchhoff_migration" and bool(params.get("_legacy_mode", False)):
                        if legacy_migration is None:
                            raise RuntimeError("legacy_migration import failed")
                        csv_path = params.get("formatString") or self.base_csv_path
                        if not csv_path:
                            raise RuntimeError("legacy mode requires CSV path")
                        legacy_result = legacy_migration.run(params, csv_path)
                        newdata = np.array(legacy_result["migrated"], copy=True)
                    else:
                        local_params = {k: v for k, v in params.items() if not str(k).startswith("_")}
                        result = method["func"](current_data, **local_params)
                        newdata = result[0] if isinstance(result, tuple) else result

                current_data = newdata
                outputs.append({
                    "method_key": method_key,
                    "method_name": method["name"],
                    "data": np.array(newdata, copy=True),
                })
                self.progress.emit(i, total, f"完成 ({i}/{total}): {method['name']}")

            self.finished.emit({"outputs": outputs, "final_data": current_data})
        except Exception as e:
            self.error.emit(build_processing_error_message(e, current_method_name))


_configure_matplotlib_cjk_fonts()


class GPRGuiQt(QMainWindow):
    def __init__(self, version_text: str = ""):
        super().__init__()
        self.version_text = version_text.strip() or "GPR_GUI"
        self.setWindowTitle(self.version_text)
        self.resize(1280, 800)
        self._apply_style()

        self.data = None
        self.data_path = None
        self.header_info = None
        self.original_data = None
        self.history = []
        self.cbar = None
        self._worker_thread = None
        self._worker = None
        self._current_run_context = None
        self._plot_timer = QTimer(self)
        self._plot_timer.setSingleShot(True)
        self._plot_timer.timeout.connect(self._do_refresh_plot)
        self._ds_cache = {}
        self.compare_snapshots = []
        self._compare_syncing = False
        self._data_revision = 0
        self._last_plot_signature = None
        self._plot_debug_metrics = os.getenv("GPR_GUI_PLOT_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
        self._plot_skip_count = 0
        self._plot_draw_count = 0
        self._last_plot_ms = 0.0
        self._last_prepare_ms = None
        self._last_compare_ms = None
        self._method_param_overrides = {}
        self._selected_preset_key = None

        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root_layout.addWidget(splitter)

        # Left panel (controls)
        left_panel = QWidget()
        left_panel.setMinimumWidth(300)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(left_panel)

        # Right panel (plot) -> move to left side of splitter for larger visual area
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 4, 4, 4)
        splitter.addWidget(right_panel)
        splitter.addWidget(scroll)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([1020, 320])

        # ----- Actions -----
        action_box = QGroupBox("🧰 操作")
        action_layout = QVBoxLayout(action_box)
        self.btn_import = QPushButton("导入 CSV")
        self.btn_import.setProperty("class", "primary")
        self.btn_apply = QPushButton("应用所选方法")
        self.btn_apply.setProperty("class", "primary")
        self.btn_quick = QPushButton("一键默认流程")
        self.btn_undo = QPushButton("撤销")
        self.btn_reset = QPushButton("重置原始")
        action_layout.addWidget(self.btn_import)
        action_layout.addWidget(self.btn_apply)
        action_layout.addWidget(self.btn_quick)
        row = QWidget()
        row_l = QHBoxLayout(row)
        row_l.setContentsMargins(0, 0, 0, 0)
        row_l.addWidget(self.btn_undo)
        row_l.addWidget(self.btn_reset)
        action_layout.addWidget(row)
        left_layout.addWidget(action_box)

        # ----- Method selection -----
        method_box = QGroupBox("🧪 方法")
        method_layout = QVBoxLayout(method_box)
        self.method_combo = QComboBox()
        ordered = [k for k in PREFERRED_METHOD_ORDER if k in PROCESSING_METHODS]
        tail = [k for k in PROCESSING_METHODS.keys() if k not in ordered]
        self.method_keys = ordered + tail
        self.method_combo.addItems([METHOD_DISPLAY_NAMES.get(k, PROCESSING_METHODS[k]['name']) for k in self.method_keys])
        method_layout.addWidget(self.method_combo)

        self.preset_combo = QComboBox()
        for preset_key, preset in GUI_PRESETS_V1.items():
            self.preset_combo.addItem(preset["label"], preset_key)
        method_layout.addWidget(self.preset_combo)

        preset_btn_row = QWidget()
        preset_btn_layout = QHBoxLayout(preset_btn_row)
        preset_btn_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_apply_preset = QPushButton("应用预设")
        self.btn_backfill_params = QPushButton("回填当前参数")
        self.btn_import_tzt_defaults = QPushButton("导入 tzt 为迁移默认")
        preset_btn_layout.addWidget(self.btn_apply_preset)
        preset_btn_layout.addWidget(self.btn_backfill_params)
        preset_btn_layout.addWidget(self.btn_import_tzt_defaults)
        method_layout.addWidget(preset_btn_row)

        self.legacy_mode_var = QCheckBox("legacy 模式（测试）")
        self.legacy_mode_var.setChecked(False)
        method_layout.addWidget(self.legacy_mode_var)

        self.param_container = QWidget()
        self.param_layout = QFormLayout(self.param_container)
        self.param_layout.setContentsMargins(4, 4, 4, 4)
        method_layout.addWidget(self.param_container)
        left_layout.addWidget(method_box)

        # ----- Batch -----
        batch_box = QGroupBox("📊 批处理 / 报告")
        batch_layout = QVBoxLayout(batch_box)
        self.batch_list = QListWidget()
        self.batch_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for key in self.method_keys:
            self.batch_list.addItem(QListWidgetItem(METHOD_DISPLAY_NAMES.get(key, PROCESSING_METHODS[key]['name'])))
        batch_layout.addWidget(self.batch_list)
        self.btn_batch = QPushButton("运行批处理对比")
        batch_layout.addWidget(self.btn_batch)
        self.btn_report = QPushButton("生成报告")
        batch_layout.addWidget(self.btn_report)
        left_layout.addWidget(batch_box)

        # ----- Display -----
        display_box = QGroupBox("🎛 显示")
        display_box.setCheckable(True)
        display_box.setChecked(True)
        display_layout = QVBoxLayout(display_box)
        display_body = QWidget()
        display_body_layout = QVBoxLayout(display_body)
        display_body_layout.setContentsMargins(4, 4, 4, 4)

        self.symmetric_var = QCheckBox("对称灰度拉伸（vmin/vmax）")
        display_body_layout.addWidget(self.symmetric_var)

        self.chatgpt_style_var = QCheckBox("自动对比度（裁剪99%）")
        self.chatgpt_style_var.setChecked(False)
        display_body_layout.addWidget(self.chatgpt_style_var)

        self.compare_var = QCheckBox("双视图对比")
        self.compare_var.setChecked(False)
        display_body_layout.addWidget(self.compare_var)

        compare_row = QWidget()
        compare_l = QHBoxLayout(compare_row)
        compare_l.setContentsMargins(0, 0, 0, 0)
        compare_l.addWidget(QLabel("对比"))
        self.compare_left_combo = QComboBox()
        self.compare_right_combo = QComboBox()
        compare_l.addWidget(self.compare_left_combo)
        compare_l.addWidget(QLabel("vs"))
        compare_l.addWidget(self.compare_right_combo)
        display_body_layout.addWidget(compare_row)

        cmap_row = QWidget()
        cmap_l = QHBoxLayout(cmap_row)
        cmap_l.setContentsMargins(0, 0, 0, 0)
        cmap_l.addWidget(QLabel("色图"))
        self.cmap_combo = QComboBox()
        self.cmap_combo.addItems(["gray", "viridis", "plasma", "inferno", "magma", "jet", "seismic"])
        self.cmap_combo.setCurrentText("gray")
        cmap_l.addWidget(self.cmap_combo)
        display_body_layout.addWidget(cmap_row)

        self.cmap_invert_var = QCheckBox("反转色图")
        self.show_cbar_var = QCheckBox("显示色标")
        self.show_grid_var = QCheckBox("显示网格")
        display_body_layout.addWidget(self.cmap_invert_var)
        display_body_layout.addWidget(self.show_cbar_var)
        display_body_layout.addWidget(self.show_grid_var)

        display_layout.addWidget(display_body)
        display_box.toggled.connect(display_body.setVisible)
        left_layout.addWidget(display_box)

        # ----- 对比度 -----
        contrast_box = QGroupBox("对比度")
        contrast_layout = QVBoxLayout(contrast_box)
        self.percentile_var = QCheckBox("百分位拉伸")
        contrast_layout.addWidget(self.percentile_var)
        perc_row = QWidget()
        perc_l = QHBoxLayout(perc_row)
        perc_l.setContentsMargins(0, 0, 0, 0)
        perc_l.addWidget(QLabel("低"))
        self.p_low_edit = QLineEdit("1")
        self.p_low_edit.setFixedWidth(60)
        perc_l.addWidget(self.p_low_edit)
        perc_l.addWidget(QLabel("高"))
        self.p_high_edit = QLineEdit("99")
        self.p_high_edit.setFixedWidth(60)
        perc_l.addWidget(self.p_high_edit)
        contrast_layout.addWidget(perc_row)
        left_layout.addWidget(contrast_box)

        # ----- 预处理 -----
        preprocess_box = QGroupBox("🧹 预处理")
        preprocess_box.setCheckable(True)
        preprocess_box.setChecked(True)
        preprocess_layout = QVBoxLayout(preprocess_box)
        preprocess_body = QWidget()
        preprocess_body_layout = QVBoxLayout(preprocess_body)
        preprocess_body_layout.setContentsMargins(4, 4, 4, 4)
        self.normalize_var = QCheckBox("归一化（最大绝对值）")
        self.demean_var = QCheckBox("去均值（逐道）")
        preprocess_body_layout.addWidget(self.normalize_var)
        preprocess_body_layout.addWidget(self.demean_var)
        preprocess_layout.addWidget(preprocess_body)
        preprocess_box.toggled.connect(preprocess_body.setVisible)
        left_layout.addWidget(preprocess_box)

        # ----- 处理记录 -----
        record_box = QGroupBox("🧾 处理记录")
        record_layout = QVBoxLayout(record_box)
        self.record = QTextEdit()
        self.record.setReadOnly(True)
        self.record.setText("暂无记录")
        record_layout.addWidget(self.record)
        self.btn_record_clear = QPushButton("清空记录")
        self.btn_record_clear.clicked.connect(self.record.clear)
        self.btn_record_export = QPushButton("导出记录")
        self.btn_record_export.clicked.connect(self.export_record)
        record_layout.addWidget(self.btn_record_clear)
        record_layout.addWidget(self.btn_record_export)
        left_layout.addWidget(record_box)


        # ----- Crop -----
        crop_box = QGroupBox("✂️ 裁剪")
        crop_box.setCheckable(True)
        crop_box.setChecked(True)
        crop_layout = QVBoxLayout(crop_box)
        crop_body = QWidget()
        crop_body_layout = QVBoxLayout(crop_body)
        crop_body_layout.setContentsMargins(4, 4, 4, 4)

        self.crop_enable_var = QCheckBox("启用裁剪")
        crop_body_layout.addWidget(self.crop_enable_var)
        self.time_start_edit = QLineEdit()
        self.time_end_edit = QLineEdit()
        self.dist_start_edit = QLineEdit()
        self.dist_end_edit = QLineEdit()
        crop_body_layout.addLayout(self._pair_row("时间起", self.time_start_edit, "止", self.time_end_edit))
        crop_body_layout.addLayout(self._pair_row("距离起", self.dist_start_edit, "止", self.dist_end_edit))
        self.btn_apply_crop = QPushButton("应用裁剪")
        self.btn_reset_crop = QPushButton("重置裁剪")
        crop_body_layout.addWidget(self.btn_apply_crop)
        crop_body_layout.addWidget(self.btn_reset_crop)

        crop_layout.addWidget(crop_body)
        crop_box.toggled.connect(crop_body.setVisible)
        left_layout.addWidget(crop_box)

        # ----- Fast preview -----
        preview_box = QGroupBox("快速预览")
        preview_layout = QVBoxLayout(preview_box)
        self.fast_preview_var = QCheckBox("启用分块预览")
        preview_layout.addWidget(self.fast_preview_var)
        self.max_samples_edit = QLineEdit("512")
        self.max_traces_edit = QLineEdit("200")
        preview_layout.addLayout(self._single_row("最大采样点", self.max_samples_edit))
        preview_layout.addLayout(self._single_row("最大道数", self.max_traces_edit))
        left_layout.addWidget(preview_box)

        # ----- Downsample -----
        down_box = QGroupBox("显示降采样")
        down_layout = QVBoxLayout(down_box)
        self.display_downsample_var = QCheckBox("启用显示降采样")
        self.display_downsample_var.setChecked(True)
        down_layout.addWidget(self.display_downsample_var)
        self.display_max_samples_edit = QLineEdit("800")
        self.display_max_traces_edit = QLineEdit("400")
        down_layout.addLayout(self._single_row("最大采样点", self.display_max_samples_edit))
        down_layout.addLayout(self._single_row("最大道数", self.display_max_traces_edit))
        left_layout.addWidget(down_box)

        # ----- Info -----
        info_box = QGroupBox("ℹ️ 信息 / 记录")
        info_layout = QVBoxLayout(info_box)
        self.info = QTextEdit()
        self.info.setReadOnly(True)
        info_layout.addWidget(self.info)
        left_layout.addWidget(info_box)
        left_layout.addStretch(1)

        # ----- Plot -----
        status_bar = QWidget()
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(0, 0, 0, 0)
        self.status_label = QLabel("未加载文件")
        self.status_label.setStyleSheet("color:#718096;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch(1)
        self.version_label = QLabel(self.version_text)
        self.version_label.setStyleSheet("color:#4A5568;")
        status_layout.addWidget(self.version_label)
        right_layout.addWidget(status_bar)

        self.fig = Figure(figsize=(9.5, 6.4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("B-扫")
        self.ax.set_xlabel("距离（道索引）")
        self.ax.set_ylabel("时间（采样索引）")
        self.canvas = FigureCanvas(self.fig)

        self.observability_box = QGroupBox("📈 可观测性")
        self.observability_box.setCheckable(True)
        self.observability_box.setChecked(False)
        observability_layout = QVBoxLayout(self.observability_box)
        observability_layout.setContentsMargins(8, 6, 8, 6)
        observability_body = QWidget()
        observability_body_layout = QVBoxLayout(observability_body)
        observability_body_layout.setContentsMargins(0, 0, 0, 0)
        observability_body_layout.setSpacing(2)
        self.obs_last_plot_label = QLabel("最近绘制耗时：--")
        self.obs_draw_count_label = QLabel("累计绘制次数：0")
        self.obs_skip_count_label = QLabel("累计跳过重绘：0")
        self.obs_last_prepare_label = QLabel("最近预处理耗时：--")
        for label in [
            self.obs_last_plot_label,
            self.obs_draw_count_label,
            self.obs_skip_count_label,
            self.obs_last_prepare_label,
        ]:
            label.setStyleSheet("color:#4A5568;")
            observability_body_layout.addWidget(label)
        observability_layout.addWidget(observability_body)
        self.observability_box.toggled.connect(observability_body.setVisible)
        observability_body.setVisible(False)
        right_layout.addWidget(self.observability_box)

        right_layout.addWidget(self.canvas, 1)

        # ---- Signals ----
        self.btn_import.clicked.connect(self.load_csv)
        self.btn_apply.clicked.connect(self.apply_method)
        self.btn_quick.clicked.connect(self.run_default_pipeline)
        self.btn_undo.clicked.connect(self.undo_last)
        self.btn_reset.clicked.connect(self.reset_original)
        self.btn_batch.clicked.connect(self.run_batch)
        self.btn_report.clicked.connect(self.generate_report)
        self.btn_apply_crop.clicked.connect(self._refresh_plot)
        self.btn_reset_crop.clicked.connect(self._reset_crop)

        self.method_combo.currentIndexChanged.connect(self._on_method_change)
        self.btn_apply_preset.clicked.connect(self.apply_selected_preset)
        self.btn_backfill_params.clicked.connect(self.backfill_current_method_params)
        self.btn_import_tzt_defaults.clicked.connect(self.import_tzt_as_migration_defaults)
        self.cmap_combo.currentIndexChanged.connect(self._refresh_plot)
        self.compare_left_combo.currentIndexChanged.connect(self._refresh_plot)
        self.compare_right_combo.currentIndexChanged.connect(self._refresh_plot)

        for cb in [
            self.symmetric_var, self.chatgpt_style_var, self.compare_var, self.cmap_invert_var, self.show_cbar_var, self.show_grid_var,
            self.percentile_var, self.normalize_var, self.demean_var,
            self.crop_enable_var, self.display_downsample_var,
        ]:
            cb.stateChanged.connect(self._refresh_plot)

        self.compare_var.toggled.connect(self._on_compare_toggled)
        self._on_compare_toggled(self.compare_var.isChecked())
        self._set_compare_snapshots([])

        self._render_params(self.method_keys[0])
        self._refresh_observability_panel()
        self._log(f"Version: {self.version_text}")
        self._log("Welcome. Please import a CSV to view B-扫.")

    # --------- UI helpers ---------
    def _set_busy(self, busy: bool, text: str = "处理中..."):
        controls = [
            self.btn_import, self.btn_apply, self.btn_quick, self.btn_undo, self.btn_reset,
            self.btn_batch, self.btn_report, self.btn_apply_crop, self.btn_reset_crop,
            self.method_combo, self.batch_list,
        ]
        for w in controls:
            w.setEnabled(not busy)
        if busy:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.status_label.setText(text)
        else:
            QApplication.restoreOverrideCursor()
            self.status_label.setText(text)
        QApplication.processEvents()

    def _pair_row(self, label1, edit1, label2, edit2):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(QLabel(label1))
        edit1.setFixedWidth(80)
        row.addWidget(edit1)
        row.addWidget(QLabel(label2))
        edit2.setFixedWidth(80)
        row.addWidget(edit2)
        row.addStretch(1)
        return row

    def _single_row(self, label, edit):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(QLabel(label))
        edit.setFixedWidth(80)
        row.addWidget(edit)
        row.addStretch(1)
        return row

    # --------- Logging ---------
    def _apply_style(self):
        # Minimal, clean UI theme
        self.setStyleSheet(
            """
            QMainWindow { background: #F5F7FA; font-size: 13px; font-family: "Noto Sans CJK SC"; }
            QGroupBox {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                margin-top: 12px;
                padding: 8px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #2D3748;
            }
            QLabel { color: #4A5568; }
            QPushButton {
                background: #EDF2F7;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 6px 10px;
                color: #2D3748;
                min-height: 26px;
            }
            QPushButton:hover { background: #E6EEF8; }
            QPushButton:pressed { background: #DCE7F5; }
            QPushButton[class="primary"] {
                background: #2F6FED;
                color: #FFFFFF;
                border: 1px solid #2F6FED;
            }
            QPushButton[class="primary"]:hover { background: #2A63D6; }
            QComboBox, QLineEdit {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 4px 6px;
                min-height: 24px;
            }
            QCheckBox { color: #4A5568; }
            QScrollArea { border: none; }
            QTextEdit {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 6px;
            }
            QPushButton:disabled, QLineEdit:disabled, QComboBox:disabled, QCheckBox:disabled, QListWidget:disabled, QTextEdit:disabled {
                background: #F1F5F9;
                color: #A0AEC0;
                border-color: #E2E8F0;
            }
            """
        )

    def _log(self, msg: str):
        self.info.append(msg)
        self.info.ensureCursorVisible()

    def _clip_for_display(self, data: np.ndarray, clip_percent: float = 99.0):
        x = data.astype(np.float64)
        v = np.percentile(np.abs(x), clip_percent)
        v = max(v, 1e-12)
        return np.clip(x, -v, v), v

    # --------- History ---------
    def _push_history(self):
        if self.data is None:
            return
        self.history.append(self.data.copy())
        if len(self.history) > 10:
            self.history.pop(0)

    def undo_last(self):
        if not self.history:
            QMessageBox.information(self, "撤销", "无可恢复的历史状态。")
            return
        self.data = self.history.pop()
        self._mark_data_changed()
        self._update_current_compare_snapshot()
        self.plot_data(self.data)
        self._log("撤销: restored previous state.")

    def reset_original(self):
        if self.original_data is None:
            QMessageBox.information(self, "重置", "未加载原始数据。")
            return
        self._push_history()
        self.data = self.original_data.copy()
        self._mark_data_changed()
        self._set_compare_snapshots([
            {"label": "原始", "data": self.original_data},
            {"label": "当前", "data": self.data},
        ])
        self.plot_data(self.data)
        self._log("重置: restored original data.")

    def _on_compare_toggled(self, checked: bool):
        self.compare_left_combo.setEnabled(checked)
        self.compare_right_combo.setEnabled(checked)

    def _set_compare_snapshots(self, snapshots: list):
        cleaned = []
        for item in snapshots:
            if not item:
                continue
            label = str(item.get("label", "阶段"))
            data = item.get("data")
            if data is None:
                continue
            cleaned.append({"label": label, "data": np.array(data, copy=True)})
        self.compare_snapshots = cleaned

        self._compare_syncing = True
        try:
            with QSignalBlocker(self.compare_left_combo), QSignalBlocker(self.compare_right_combo):
                self.compare_left_combo.clear()
                self.compare_right_combo.clear()
                for s in self.compare_snapshots:
                    self.compare_left_combo.addItem(s["label"])
                    self.compare_right_combo.addItem(s["label"])
                if self.compare_snapshots:
                    self.compare_left_combo.setCurrentIndex(0)
                    right_idx = 1 if len(self.compare_snapshots) > 1 else 0
                    self.compare_right_combo.setCurrentIndex(right_idx)
        finally:
            self._compare_syncing = False

    def _update_current_compare_snapshot(self):
        if self.data is None:
            return
        if not self.compare_snapshots:
            self._set_compare_snapshots([
                {"label": "原始", "data": self.original_data if self.original_data is not None else self.data},
                {"label": "当前", "data": self.data},
            ])
            return
        self.compare_snapshots[-1] = {"label": self.compare_snapshots[-1]["label"], "data": np.array(self.data, copy=True)}

    # --------- UI callbacks ---------
    def _on_method_change(self, idx=None):
        idx = self.method_combo.currentIndex()
        if idx < 0:
            return
        key = self.method_keys[idx]
        self._render_params(key)

    def _refresh_plot(self):
        if self.data is None or self._compare_syncing:
            return
        # debounce frequent UI-triggered redraws
        self._plot_timer.start(30)

    def _do_refresh_plot(self):
        if self.data is None:
            return
        signature = self._build_plot_signature()
        if signature == self._last_plot_signature:
            self._plot_skip_count += 1
            if hasattr(self, "_refresh_observability_panel"):
                self._refresh_observability_panel()
            self._log_plot_debug(f"skip redraw: count={self._plot_skip_count}")
            return
        self.plot_data(self.data)

    def _mark_data_changed(self):
        self._data_revision += 1

    def _build_plot_signature(self):
        if self.data is None:
            return None
        return (self._data_revision,) + self._build_plot_ui_signature()

    def _log_plot_debug(self, message: str):
        if self._plot_debug_metrics:
            self._log(f"[plot-debug] {message}")

    def _refresh_observability_panel(self):
        if not hasattr(self, "obs_last_plot_label"):
            return
        self.obs_last_plot_label.setText(f"最近绘制耗时：{GPRGuiQt._format_metric_ms(self._last_plot_ms)}")
        self.obs_draw_count_label.setText(f"累计绘制次数：{int(self._plot_draw_count)}")
        self.obs_skip_count_label.setText(f"累计跳过重绘：{int(self._plot_skip_count)}")
        self.obs_last_prepare_label.setText(f"最近预处理耗时：{GPRGuiQt._format_metric_ms(self._last_prepare_ms)}")

    @staticmethod
    def _format_metric_ms(value):
        if value is None:
            return "--"
        try:
            return f"{float(value):.2f} ms"
        except Exception:
            return "--"

    def _reset_crop(self):
        self.time_start_edit.setText("")
        self.time_end_edit.setText("")
        self.dist_start_edit.setText("")
        self.dist_end_edit.setText("")
        self.crop_enable_var.setChecked(False)
        self._refresh_plot()

    # --------- Data helpers ---------
    def _parse_float(self, text: str):
        try:
            return float(text)
        except Exception:
            return None

    def _get_colormap(self):
        cmap = (self.cmap_combo.currentText() or "gray").strip()
        if self.cmap_invert_var.isChecked():
            if cmap.endswith("_r"):
                cmap = cmap[:-2]
            else:
                cmap = cmap + "_r"
        return cmap

    def _get_percentile_bounds(self, data: np.ndarray):
        if not self.percentile_var.isChecked():
            return None
        try:
            low = float(self.p_low_edit.text() or 1.0)
            high = float(self.p_high_edit.text() or 99.0)
        except Exception:
            return None
        low = max(0.0, min(100.0, low))
        high = max(0.0, min(100.0, high))
        if high <= low:
            return None
        vmin, vmax = np.percentile(data, [low, high])
        if vmin == vmax:
            return None
        return vmin, vmax

    def _apply_preprocess(self, data: np.ndarray) -> np.ndarray:
        out = data
        if self.demean_var.isChecked():
            mean = np.mean(out, axis=0, keepdims=True)
            out = out - mean
        if self.normalize_var.isChecked():
            maxv = np.max(np.abs(out))
            if maxv == 0:
                maxv = 1e-6
            out = out / maxv
        return out

    def _get_crop_bounds(self, data: np.ndarray):
        if not self.crop_enable_var.isChecked():
            return None

        n_time, n_dist = data.shape
        time_start = self._parse_float(self.time_start_edit.text().strip())
        time_end = self._parse_float(self.time_end_edit.text().strip())
        dist_start = self._parse_float(self.dist_start_edit.text().strip())
        dist_end = self._parse_float(self.dist_end_edit.text().strip())

        if self.header_info:
            total_time = float(self.header_info.get("total_time_ns", n_time))
            num_traces = max(1, int(self.header_info.get("num_traces", n_dist)))
            trace_interval = float(self.header_info.get("trace_interval_m", 1.0))
            dist_total = trace_interval * (num_traces - 1)

            if time_start is None:
                time_start = 0.0
            if time_end is None:
                time_end = total_time
            if dist_start is None:
                dist_start = 0.0
            if dist_end is None:
                dist_end = dist_total

            time_start = max(0.0, min(total_time, time_start))
            time_end = max(0.0, min(total_time, time_end))
            dist_start = max(0.0, min(dist_total, dist_start))
            dist_end = max(0.0, min(dist_total, dist_end))

            if time_end < time_start:
                time_start, time_end = time_end, time_start
            if dist_end < dist_start:
                dist_start, dist_end = dist_end, dist_start

            def time_to_idx(t):
                if total_time <= 0 or n_time <= 1:
                    return 0
                return int(round(t / total_time * (n_time - 1)))

            def dist_to_idx(d):
                if dist_total <= 0 or n_dist <= 1:
                    return 0
                return int(round(d / dist_total * (n_dist - 1)))

            t0 = max(0, min(n_time - 1, time_to_idx(time_start)))
            t1 = max(0, min(n_time - 1, time_to_idx(time_end)))
            d0 = max(0, min(n_dist - 1, dist_to_idx(dist_start)))
            d1 = max(0, min(n_dist - 1, dist_to_idx(dist_end)))
        else:
            if time_start is None:
                time_start = 0.0
            if time_end is None:
                time_end = float(n_time - 1)
            if dist_start is None:
                dist_start = 0.0
            if dist_end is None:
                dist_end = float(n_dist - 1)

            time_start = max(0.0, min(n_time - 1, time_start))
            time_end = max(0.0, min(n_time - 1, time_end))
            dist_start = max(0.0, min(n_dist - 1, dist_start))
            dist_end = max(0.0, min(n_dist - 1, dist_end))

            if time_end < time_start:
                time_start, time_end = time_end, time_start
            if dist_end < dist_start:
                dist_start, dist_end = dist_end, dist_start

            t0 = int(round(time_start))
            t1 = int(round(time_end))
            d0 = int(round(dist_start))
            d1 = int(round(dist_end))

        return {
            "t0": t0,
            "t1": t1,
            "d0": d0,
            "d1": d1,
            "time_start": time_start,
            "time_end": time_end,
            "dist_start": dist_start,
            "dist_end": dist_end,
        }

    def _apply_crop(self, data: np.ndarray):
        bounds = self._get_crop_bounds(data)
        if not bounds:
            return data, None
        t0, t1, d0, d1 = bounds["t0"], bounds["t1"], bounds["d0"], bounds["d1"]
        cropped = data[t0:t1 + 1, d0:d1 + 1]
        return cropped, bounds

    def _parse_int_edit(self, edit: QLineEdit, default: int = 0) -> int:
        text = (edit.text() or "").strip()
        if text == "":
            return default
        try:
            return int(float(text))
        except Exception:
            return default

    def _get_downsample_indices(self, n_time: int, n_dist: int, max_samples: int, max_traces: int):
        key = (n_time, n_dist, max_samples, max_traces)
        if key in self._ds_cache:
            return self._ds_cache[key]
        t_idx = _downsample_axis_linear(n_time, max_samples)
        d_idx = _downsample_axis_linear(n_dist, max_traces)
        if len(self._ds_cache) > 64:
            self._ds_cache.clear()
        self._ds_cache[key] = (t_idx, d_idx)
        return t_idx, d_idx

    @staticmethod
    def _select_2d(data: np.ndarray, row_idx, col_idx) -> np.ndarray:
        """Safe 2D selector for mixed slice/array indices.

        np.ix_ only accepts 1-D sequences and raises on slice objects.
        This helper keeps fast paths for pure slicing and uses np.ix_ only
        when both axes are array-like integer indices.
        """
        if isinstance(row_idx, slice) or isinstance(col_idx, slice):
            return data[row_idx, col_idx]

        row_arr = np.asarray(row_idx).reshape(-1)
        col_arr = np.asarray(col_idx).reshape(-1)
        return data[np.ix_(row_arr, col_arr)]

    def _downsample_data(self, data: np.ndarray) -> np.ndarray:
        if not self.fast_preview_var.isChecked():
            return data
        max_samples = self._parse_int_edit(self.max_samples_edit, default=0)
        max_traces = self._parse_int_edit(self.max_traces_edit, default=0)
        n_time, n_dist = data.shape
        t_idx, d_idx = self._get_downsample_indices(n_time, n_dist, max_samples, max_traces)
        return self._select_2d(data, t_idx, d_idx)

    def _downsample_for_display(self, data: np.ndarray) -> np.ndarray:
        if not self.display_downsample_var.isChecked():
            return data
        max_samples = self._parse_int_edit(self.display_max_samples_edit, default=0)
        max_traces = self._parse_int_edit(self.display_max_traces_edit, default=0)
        n_time, n_dist = data.shape
        t_idx, d_idx = self._get_downsample_indices(n_time, n_dist, max_samples, max_traces)
        return self._select_2d(data, t_idx, d_idx)

    def _prepare_view_data(self, data: np.ndarray):
        prepare_start_ts = time.perf_counter()
        arr = np.asarray(data)
        if np.isfinite(arr).all():
            safe_data = arr
        else:
            safe_data = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
        valid_data = self._apply_preprocess(safe_data)
        cropped_data, bounds = self._apply_crop(valid_data)
        display_data = self._downsample_for_display(cropped_data)
        prepare_elapsed_ms = (time.perf_counter() - prepare_start_ts) * 1000.0
        self._last_prepare_ms = prepare_elapsed_ms
        if hasattr(self, "_refresh_observability_panel"):
            self._refresh_observability_panel()
        self._log_plot_debug(
            f"prepare view: {prepare_elapsed_ms:.2f} ms, shape={display_data.shape[0]}x{display_data.shape[1]}"
        )
        return display_data, bounds

    # --------- Params rendering ---------
    def _render_params(self, method_key: str):
        while self.param_layout.rowCount():
            self.param_layout.removeRow(0)
        self.param_vars = {}
        params = PROCESSING_METHODS[method_key].get("params", [])
        overrides = self._method_param_overrides.get(method_key, {})
        if not params:
            self.param_layout.addRow(QLabel("(No parameters)"))
            return
        for p in params:
            value = overrides.get(p["name"], p.get("default", ""))
            edit = QLineEdit(str(value))
            edit.setFixedWidth(120)
            self.param_layout.addRow(QLabel(p["label"]), edit)
            self.param_vars[p["name"]] = (edit, p)

    
    def _move_flow_item(self, direction: int):
        row = self.batch_list.currentRow()
        if row < 0:
            return
        new_row = row + direction
        if new_row < 0 or new_row >= self.batch_list.count():
            return
        item = self.batch_list.takeItem(row)
        self.batch_list.insertItem(new_row, item)
        self.batch_list.setCurrentRow(new_row)

    def _get_params(self):
        params = {}
        for name, (edit, meta) in self.param_vars.items():
            label = meta.get("label", name)
            raw = edit.text().strip()
            if raw == "":
                default_val = meta.get("default", "")
                if default_val in (None, ""):
                    raise ValueError(build_param_error_message(label, raw, "参数为空且无默认值"))
                raw = str(default_val)

            try:
                if meta["type"] == "int":
                    val = int(float(raw))
                elif meta["type"] == "float":
                    val = float(raw)
                else:
                    val = raw
            except ValueError:
                raise ValueError(build_param_error_message(label, raw, "类型错误"))

            min_v = meta.get("min")
            max_v = meta.get("max")
            if isinstance(val, (int, float)):
                if min_v is not None and val < min_v:
                    raise ValueError(build_param_error_message(label, raw, f"低于最小值 {min_v}"))
                if max_v is not None and val > max_v:
                    raise ValueError(build_param_error_message(label, raw, f"高于最大值 {max_v}"))

            params[name] = val
        return params

    def _update_current_method_overrides(self):
        if not hasattr(self, "param_vars"):
            return
        idx = self.method_combo.currentIndex()
        if idx < 0:
            return
        try:
            params = self._get_params()
        except ValueError:
            return
        self._method_param_overrides[self.method_keys[idx]] = params

    def _resolve_method_params(self, method_key: str):
        method = PROCESSING_METHODS[method_key]
        defaults = {p["name"]: p.get("default") for p in method.get("params", [])}
        overrides = self._method_param_overrides.get(method_key, {})
        defaults.update(overrides)
        if method_key == "kirchhoff_migration":
            defaults["_legacy_mode"] = bool(getattr(self, "legacy_mode_var", None) and self.legacy_mode_var.isChecked())
        return defaults

    def _apply_preset_by_key(self, preset_key: str):
        preset = GUI_PRESETS_V1.get(preset_key)
        if not preset:
            return
        ui = preset.get("ui", {})
        self.fast_preview_var.setChecked(bool(ui.get("fast_preview", self.fast_preview_var.isChecked())))
        if "max_samples" in ui:
            self.max_samples_edit.setText(str(ui["max_samples"]))
        if "max_traces" in ui:
            self.max_traces_edit.setText(str(ui["max_traces"]))
        self.display_downsample_var.setChecked(bool(ui.get("display_downsample", self.display_downsample_var.isChecked())))
        if "display_max_samples" in ui:
            self.display_max_samples_edit.setText(str(ui["display_max_samples"]))
        if "display_max_traces" in ui:
            self.display_max_traces_edit.setText(str(ui["display_max_traces"]))
        self.normalize_var.setChecked(bool(ui.get("normalize", self.normalize_var.isChecked())))
        self.demean_var.setChecked(bool(ui.get("demean", self.demean_var.isChecked())))
        self.percentile_var.setChecked(bool(ui.get("percentile", self.percentile_var.isChecked())))
        if "p_low" in ui:
            self.p_low_edit.setText(str(ui["p_low"]))
        if "p_high" in ui:
            self.p_high_edit.setText(str(ui["p_high"]))

        for method_key, params in preset.get("method_params", {}).items():
            self._method_param_overrides[method_key] = dict(params)

        idx = self.method_combo.currentIndex()
        if idx >= 0:
            self._render_params(self.method_keys[idx])
        self._selected_preset_key = preset_key
        preset_name = preset.get("label", preset_key)
        self._log(f"Preset applied: {preset_name}")
        self.status_label.setText(f"已应用预设：{preset_name}")
        self._refresh_plot()

    def apply_selected_preset(self):
        preset_key = self.preset_combo.currentData()
        self._apply_preset_by_key(preset_key)

    def backfill_current_method_params(self):
        idx = self.method_combo.currentIndex()
        if idx < 0:
            return
        method_key = self.method_keys[idx]
        try:
            params = self._get_params()
        except ValueError as e:
            QMessageBox.critical(self, "参数无效", str(e))
            return
        self._method_param_overrides[method_key] = params
        self._render_params(method_key)
        self._log(f"Backfilled current params: {METHOD_DISPLAY_NAMES.get(method_key, method_key)}")
        self.status_label.setText("已回填当前参数到UI")

    def _extract_kirchhoff_migration_snapshot(self, params: dict) -> dict:
        method = PROCESSING_METHODS.get("kirchhoff_migration", {})
        ordered = [p["name"] for p in method.get("params", [])]
        snapshot = {}
        for name in ordered:
            if name in params:
                snapshot[name] = params[name]
        return snapshot

    def _log_kirchhoff_migration_config(self, params: dict, source: str = "执行"):
        snapshot = self._extract_kirchhoff_migration_snapshot(params)
        if not snapshot:
            return
        applied = {k: snapshot[k] for k in snapshot if k in KIRCHHOFF_APPLIED_FIELDS}
        stored_only = {k: snapshot[k] for k in snapshot if k in KIRCHHOFF_STORED_ONLY_FIELDS}
        self._log(f"Kirchhoff迁移默认配置({source}) - 应用参数: {applied}")
        if stored_only:
            self._log(f"Kirchhoff迁移默认配置({source}) - 存档参数(仅记录): {stored_only}")

    def _parse_tzt_file(self, path: str) -> dict:
        parsed = {}
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(None, 1)
                if len(parts) < 2:
                    continue
                key = parts[0].strip()
                val_raw = parts[1].strip()
                if val_raw.lower() in {"true", "false"}:
                    parsed[key] = 1 if val_raw.lower() == "true" else 0
                    continue
                try:
                    num = float(val_raw)
                    parsed[key] = int(num) if num.is_integer() else num
                except ValueError:
                    parsed[key] = val_raw
        return parsed

    def import_tzt_as_migration_defaults(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入 tzt 参数", "", "参数文件 (*.tzt *.txt *.cfg);;所有文件 (*)")
        if not path:
            return
        try:
            parsed = self._parse_tzt_file(path)
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"读取 tzt 参数失败: {e}")
            return

        method = PROCESSING_METHODS["kirchhoff_migration"]
        allowed = {p["name"] for p in method.get("params", [])}
        merged = self._resolve_method_params("kirchhoff_migration")
        for k, v in TZT_MIGRATION_DEFAULTS.items():
            if k in allowed:
                merged[k] = v
        for k, v in parsed.items():
            if k in allowed:
                merged[k] = v

        self._method_param_overrides["kirchhoff_migration"] = merged
        current_key = self.method_keys[self.method_combo.currentIndex()] if self.method_combo.currentIndex() >= 0 else ""
        if current_key == "kirchhoff_migration":
            self._render_params("kirchhoff_migration")

        covered = sorted([k for k in merged.keys() if k in allowed and k in parsed])
        missing = sorted([k for k in TZT_MIGRATION_DEFAULTS.keys() if k not in parsed])
        self._log(f"已导入 tzt 迁移默认配置: {path}")
        self._log(f"tzt覆盖参数: {covered}")
        if missing:
            self._log(f"tzt缺失参数（已回退内置默认）: {missing}")
        self._log_kirchhoff_migration_config(merged, source="导入tzt")
        self.status_label.setText("已导入 tzt 为 Kirchhoff 迁移默认配置")

    # --------- Data I/O ---------
    def load_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 CSV", "", "CSV 文件 (*.csv);;所有文件 (*)")
        if not path:
            return

        try:
            header_info = detect_csv_header(path)

            skip_lines = _detect_skiprows(path)

            if self.fast_preview_var.isChecked():
                max_samples = self._parse_int_edit(self.max_samples_edit, default=0)
                max_traces = self._parse_int_edit(self.max_traces_edit, default=0)
                target_rows = max_samples if max_samples > 0 else 200000
                if header_info and max_samples > 0 and max_traces > 0:
                    target_rows = max_samples * max_traces
                rows = []
                count = 0
                for chunk in pd.read_csv(
                    path,
                    header=None,
                    skiprows=skip_lines,
                    chunksize=200000,
                    na_filter=False,
                    low_memory=False,
                ):
                    rows.append(chunk)
                    count += len(chunk)
                    if count >= target_rows:
                        break
                df = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
                raw_data = df.values
            else:
                df = pd.read_csv(path, header=None, skiprows=skip_lines, na_filter=False, low_memory=False)
                raw_data = df.values

            if raw_data.size == 0:
                raise ValueError("CSV 未读取到有效数据（空文件或分隔符不匹配）")

            if header_info:
                samples = header_info["a_scan_length"]
                traces = header_info["num_traces"]

                if raw_data.shape[1] <= 10 and raw_data.shape[0] >= samples * traces:
                    col_idx = _select_amp_column(raw_data)
                    signal_1d = raw_data[:, col_idx]
                    data = signal_1d[:traces * samples].reshape((traces, samples)).T
                elif raw_data.shape[0] == traces and raw_data.shape[1] >= samples:
                    data = raw_data[:, :samples].T
                elif raw_data.shape[0] >= samples and raw_data.shape[1] >= traces:
                    data = raw_data[:samples, :traces]
                else:
                    data = raw_data
            else:
                data = raw_data

            try:
                data = np.asarray(data, dtype=float)
            except Exception as conv_err:
                raise ValueError(f"CSV 包含非数值内容，无法转换为数值矩阵: {conv_err}")

            if data.size == 0:
                raise ValueError("CSV 数据矩阵为空")

            if self.fast_preview_var.isChecked():
                data = self._downsample_data(data)
                self._log("快速预览：数据已降采样。")

            if np.isnan(data).any():
                data = np.nan_to_num(data, nan=np.nanmean(data))

            if data.ndim == 1:
                data = data.reshape(-1, 1)

            self.data = data
            self.data_path = path
            self.header_info = header_info
            self.original_data = data.copy()
            self.history = []
            self._mark_data_changed()
            self._set_compare_snapshots([
                {"label": "原始", "data": self.original_data},
                {"label": "当前", "data": self.data},
            ])

            self._log(f"已加载 CSV： {path}  shape={data.shape}")
            if header_info:
                self.status_label.setText(
                    f"{os.path.basename(path)} | 采样:{header_info['a_scan_length']} 道数:{header_info['num_traces']}"
                )
            else:
                self.status_label.setText(os.path.basename(path))
            if header_info:
                self._log(
                    "检测到头信息： "
                    f"A-scan length={header_info['a_scan_length']} samples; "
                    f"Total time={header_info['total_time_ns']} ns; "
                    f"A-scan count={header_info['num_traces']}; "
                    f"Trace interval={header_info['trace_interval_m']} m"
                )
            else:
                self._log("未检测到头信息；使用索引坐标。")

            self.plot_data(data)

        except Exception as e:
            friendly_msg = build_csv_load_error_message(e)
            QMessageBox.critical(self, "错误", friendly_msg)
            self._log(f"加载 CSV 失败：\n{friendly_msg}")

    # --------- Plot ---------
    def _build_plot_ui_signature(self):
        return (
            self.method_combo.currentIndex(),
            self.cmap_combo.currentText(),
            self.cmap_invert_var.isChecked(),
            self.compare_var.isChecked(),
            self.compare_left_combo.currentIndex(),
            self.compare_right_combo.currentIndex(),
            self.symmetric_var.isChecked(),
            self.chatgpt_style_var.isChecked(),
            self.percentile_var.isChecked(),
            self.p_low_edit.text().strip(),
            self.p_high_edit.text().strip(),
            self.show_cbar_var.isChecked(),
            self.show_grid_var.isChecked(),
            self.normalize_var.isChecked(),
            self.demean_var.isChecked(),
            self.crop_enable_var.isChecked(),
            self.time_start_edit.text().strip(),
            self.time_end_edit.text().strip(),
            self.dist_start_edit.text().strip(),
            self.dist_end_edit.text().strip(),
            self.display_downsample_var.isChecked(),
            self.display_max_samples_edit.text().strip(),
            self.display_max_traces_edit.text().strip(),
        )

    def _draw_image_with_colormap(self, ax, d: np.ndarray, cmap: str, extent):
        if self.chatgpt_style_var.isChecked():
            clipped, v = self._clip_for_display(d, clip_percent=99.0)
            im = ax.imshow(
                clipped,
                cmap=cmap,
                aspect="auto",
                extent=extent,
                vmin=-v,
                vmax=v,
                interpolation="nearest",
                origin="upper",
            )
            return im, f" (clip=±{v:.3g})"

        if self.symmetric_var.isChecked():
            stdcont = np.nanmax(np.abs(d))
            if stdcont == 0:
                stdcont = 1e-6
            vmin = -stdcont
            vmax = stdcont
            im = ax.imshow(
                d,
                cmap=cmap,
                aspect="auto",
                extent=extent,
                vmin=vmin,
                vmax=vmax,
                interpolation="nearest",
            )
            return im, ""

        perc_bounds = None
        try:
            perc_bounds = self._get_percentile_bounds(d)
        except Exception:
            perc_bounds = None

        if perc_bounds:
            try:
                vmin, vmax = perc_bounds
                im = ax.imshow(
                    d,
                    cmap=cmap,
                    aspect="auto",
                    extent=extent,
                    vmin=vmin,
                    vmax=vmax,
                    interpolation="nearest",
                )
                return im, ""
            except Exception:
                pass

        im = ax.imshow(d, cmap=cmap, aspect="auto", extent=extent, interpolation="nearest")
        return im, ""

    def _draw_colorbar_if_needed(self, im, axes):
        if self.show_cbar_var.isChecked() and not self.chatgpt_style_var.isChecked():
            self.cbar = self.fig.colorbar(im, ax=axes, fraction=0.046, pad=0.04)

    def _build_compare_data_pairs(self, display_data: np.ndarray):
        if self.compare_var.isChecked() and len(self.compare_snapshots) >= 1:
            left_idx = self.compare_left_combo.currentIndex()
            right_idx = self.compare_right_combo.currentIndex()
            if left_idx < 0:
                left_idx = 0
            if right_idx < 0:
                right_idx = 0
            left_idx = min(left_idx, len(self.compare_snapshots) - 1)
            right_idx = min(right_idx, len(self.compare_snapshots) - 1)
            pair_indices = [left_idx, right_idx]
            if len(self.compare_snapshots) == 1:
                pair_indices = [0, 0]

            data_pairs = []
            for idx in pair_indices:
                snap = self.compare_snapshots[idx]
                snap_data, _ = self._prepare_view_data(snap["data"])
                data_pairs.append((snap_data, snap["label"]))
            return data_pairs

        return [(display_data, "B-扫")]

    def _apply_axis_grid(self, ax):
        show_grid = self.show_grid_var.isChecked()
        if show_grid:
            ax.grid(True, color="#D7DEE5", alpha=0.4)
        else:
            # Avoid matplotlib warning: grid kwargs are ignored when visible=False.
            ax.grid(False)

    def _resolve_plot_extent_and_labels(self, valid_data: np.ndarray, bounds):
        if self.header_info:
            total_time = float(self.header_info.get("total_time_ns", valid_data.shape[0]))
            num_traces = max(1, int(self.header_info.get("num_traces", valid_data.shape[1])))
            trace_interval = float(self.header_info.get("trace_interval_m", 1.0))
            distance_end = trace_interval * (num_traces - 1)
            time_start = 0.0
            time_end = total_time
            dist_start = 0.0
            dist_end = distance_end
            if bounds:
                time_start = bounds["time_start"]
                time_end = bounds["time_end"]
                dist_start = bounds["dist_start"]
                dist_end = bounds["dist_end"]
            return {
                "extent": [dist_start, dist_end, time_end, time_start],
                "xlabel": "距离 (m)",
                "ylabel": "时间 (ns)",
            }

        extent = None
        if bounds:
            extent = [bounds["dist_start"], bounds["dist_end"], bounds["time_end"], bounds["time_start"]]

        return {
            "extent": extent,
            "xlabel": "距离（道索引）",
            "ylabel": "时间（采样索引）",
        }

    def _resolve_plot_extent(self, valid_data: np.ndarray, bounds):
        return self._resolve_plot_extent_and_labels(valid_data, bounds)["extent"]

    def _create_plot_axes(self, pair_count: int):
        if pair_count > 1:
            ax_top = self.fig.add_subplot(2, 1, 1)
            ax_bottom = self.fig.add_subplot(2, 1, 2)
            return [ax_top, ax_bottom]

        ax_left = self.fig.add_subplot(1, 1, 1)
        return [ax_left]

    def _apply_axis_labels(self, ax, labels):
        ax.set_xlabel(labels["xlabel"])
        ax.set_ylabel(labels["ylabel"])

    def _render_data_pairs(self, axes, data_pairs, cmap, extent, plot_config):
        compare_start_ts = time.perf_counter() if len(data_pairs) > 1 else None
        last_im = None
        for ax, (d, title) in zip(axes, data_pairs):
            last_im, title_suffix = self._draw_image_with_colormap(ax, d, cmap, extent)
            ax.set_title(f"{title}{title_suffix}")
            self._apply_axis_labels(ax, plot_config)
            self._apply_axis_grid(ax)
        if compare_start_ts is not None:
            compare_elapsed_ms = (time.perf_counter() - compare_start_ts) * 1000.0
            self._last_compare_ms = compare_elapsed_ms
            self._log_plot_debug(f"compare render: {compare_elapsed_ms:.2f} ms, panels={len(data_pairs)}")
        return last_im

    def plot_data(self, data: np.ndarray):
        start_ts = time.perf_counter()
        self.fig.clear()
        self._last_plot_signature = self._build_plot_signature()

        display_data, bounds = self._prepare_view_data(data)
        plot_config = self._resolve_plot_extent_and_labels(display_data, bounds)
        extent = plot_config["extent"]
        cmap = self._get_colormap()

        if self.cbar is not None:
            try:
                self.cbar.remove()
            except Exception:
                pass
            self.cbar = None

        data_pairs = self._build_compare_data_pairs(display_data)
        axes = self._create_plot_axes(len(data_pairs))
        last_im = self._render_data_pairs(axes, data_pairs, cmap, extent, plot_config)

        if last_im is not None:
            self._draw_colorbar_if_needed(last_im, axes)
        self.canvas.draw_idle()

        elapsed_ms = (time.perf_counter() - start_ts) * 1000.0
        self._plot_draw_count += 1
        self._last_plot_ms = elapsed_ms
        if hasattr(self, "_refresh_observability_panel"):
            self._refresh_observability_panel()
        self._log_plot_debug(
            f"draw#{self._plot_draw_count}: {elapsed_ms:.2f} ms, skipped={self._plot_skip_count}"
        )

    # --------- Save outputs ---------
    def _save_outputs(self, data: np.ndarray, method_key: str):
        out_dir = os.path.join(BASE_DIR, "output")
        os.makedirs(out_dir, exist_ok=True)
        out_csv = os.path.join(out_dir, f"{method_key}_out.csv")
        out_png = os.path.join(out_dir, f"{method_key}_out.png")

        save_data = self._apply_preprocess(np.nan_to_num(data))
        save_data, bounds = self._apply_crop(save_data)
        savecsv(save_data, out_csv)

        time_range = None
        distance_range = None
        if self.header_info:
            total_time = float(self.header_info["total_time_ns"])
            num_traces = max(1, int(self.header_info["num_traces"]))
            trace_interval = float(self.header_info["trace_interval_m"])
            distance_end = trace_interval * (num_traces - 1)
            if bounds:
                time_range = (bounds["time_start"], bounds["time_end"])
                distance_range = (bounds["dist_start"], bounds["dist_end"])
            else:
                time_range = (0.0, total_time)
                distance_range = (0.0, distance_end)

        save_image(
            save_data,
            out_png,
            title=method_key,
            time_range=time_range,
            distance_range=distance_range,
            cmap=self._get_colormap(),
        )
        return out_csv, out_png

    # --------- Batch ---------
    def run_batch(self):
        if self.data is None or self.data_path is None:
            QMessageBox.warning(self, "No data", "Please import a CSV first.")
            return
        selected = [i.row() for i in self.batch_list.selectedIndexes()]
        if not selected:
            QMessageBox.warning(self, "No selection", "Please select methods for batch processing.")
            return

        out_dir = os.path.join(BASE_DIR, "output")
        os.makedirs(out_dir, exist_ok=True)
        tasks = []
        for idx in selected:
            method_key = self.method_keys[idx]
            method = PROCESSING_METHODS[method_key]
            params = self._resolve_method_params(method_key)
            tasks.append({
                "method_key": method_key,
                "method": method,
                "params": params,
                "out_dir": out_dir,
            })
            self._log(f"Batch queued: {method['name']}")

        self._push_history()
        self._start_processing_worker(tasks, run_type="batch")


    # --------- Report ---------
    def generate_report(self):
        if self.data is None or self.data_path is None:
            QMessageBox.warning(self, "No data", "Please import a CSV first.")
            return
        out_dir = os.path.join(BASE_DIR, "output")
        os.makedirs(out_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(out_dir, f"report_{ts}.md")
        image_path = os.path.join(out_dir, f"report_{ts}.png")

        try:
            self.fig.savefig(image_path, dpi=150)
        except Exception as e:
            self._log(f"Report screenshot failed: {e}")

        bounds = None
        try:
            bounds = self._get_crop_bounds(self._apply_preprocess(np.nan_to_num(self.data)))
        except Exception:
            bounds = None

        method_key = self.method_keys[self.method_combo.currentIndex()]
        method_name = PROCESSING_METHODS[method_key]["name"]
        try:
            params = self._get_params()
        except Exception:
            params = {}

        lines = []
        lines.append(f"# GPR GUI Report ({ts})")
        lines.append("")
        lines.append(f"- Data file: {self.data_path}")
        lines.append(f"- Method: {method_name}")
        if params:
            lines.append(f"- Params: {params}")
        lines.append(f"- 色图: {self._get_colormap()}")
        lines.append(f"- 显示色标: {self.show_cbar_var.isChecked()}")
        lines.append(f"- 显示网格: {self.show_grid_var.isChecked()}")
        lines.append(f"- Symmetric stretch: {self.symmetric_var.isChecked()}")
        if self.percentile_var.isChecked():
            lines.append(
                f"- 百分位拉伸: {self.percentile_var.isChecked()} (low={self.p_low_edit.text()}, high={self.p_high_edit.text()})"
            )
        else:
            lines.append(f"- 百分位拉伸: {self.percentile_var.isChecked()}")
        lines.append(f"- Normalize: {self.normalize_var.isChecked()}")
        lines.append(f"- Demean: {self.demean_var.isChecked()}")
        lines.append(
            f"- Display downsample: {self.display_downsample_var.isChecked()} (max_samples={self.display_max_samples_edit.text()}, max_traces={self.display_max_traces_edit.text()})"
        )
        if bounds:
            lines.append(
                f"- Crop: time {bounds['time_start']}~{bounds['time_end']} ; distance {bounds['dist_start']}~{bounds['dist_end']}"
            )
        else:
            lines.append("- Crop: disabled")
        lines.append("")
        lines.append(f"- Screenshot: {image_path}")
        lines.append("")
        lines.append("## Log")
        log_text = self.info.toPlainText().strip()
        lines.append("```")
        lines.append(log_text)
        lines.append("```")

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        self._log(f"Report saved: {report_path}")

    
    def export_record(self):
        if self.record is None:
            return
        text = self.record.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "提示", "记录为空。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "保存记录", "record.txt", "Text (*.txt);;All files (*)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        self._log(f"记录已导出：{path}")

    def _start_processing_worker(self, tasks: list, run_type: str, restore_method_idx: int = None):
        if self._worker_thread is not None:
            QMessageBox.warning(self, "忙碌", "已有任务正在执行，请稍候。")
            return
        self._current_run_context = {
            "run_type": run_type,
            "restore_method_idx": restore_method_idx,
        }
        self._worker_thread = QThread(self)
        self._worker = ProcessingWorker(self.data, tasks, base_csv_path=self.data_path)
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.error.connect(self._worker_thread.quit)
        self._worker_thread.finished.connect(self._cleanup_worker)
        self._set_busy(True, "处理中...")
        self._worker_thread.start()

    def _on_worker_progress(self, current: int, total: int, text: str):
        self.status_label.setText(text)

    def _on_worker_finished(self, payload: dict):
        outputs = payload.get("outputs", [])
        final_data = payload.get("final_data")
        if final_data is not None:
            self.data = final_data
            self._mark_data_changed()

        compare_snapshots = []
        if self.original_data is not None:
            compare_snapshots.append({"label": "原始", "data": self.original_data})

        for out in outputs:
            method_key = out["method_key"]
            method_name = out["method_name"]
            method_data = out["data"]
            out_csv, _ = self._save_outputs(method_data, method_key)
            self._log(f"Processed data saved: {out_csv}")
            self.record.append(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {method_name} | {os.path.basename(out_csv)}"
            )
            if method_key == "kirchhoff_migration":
                migration_params = self._resolve_method_params("kirchhoff_migration")
                self._log_kirchhoff_migration_config(migration_params, source="执行后记录")
                self.record.append(f"  migration-config={self._extract_kirchhoff_migration_snapshot(migration_params)}")
            compare_snapshots.append({"label": method_name, "data": method_data})

        if self.data is not None:
            if compare_snapshots:
                compare_snapshots.append({"label": "当前", "data": self.data})
                self._set_compare_snapshots(compare_snapshots)
            else:
                self._update_current_compare_snapshot()
            self.plot_data(self.data)

        ctx = self._current_run_context or {}
        restore_idx = ctx.get("restore_method_idx")
        if restore_idx is not None:
            self.method_combo.setCurrentIndex(restore_idx)
        self.status_label.setText(f"处理完成 | 最后处理:{datetime.now().strftime('%H:%M:%S')}")
        self._set_busy(False, "就绪")

    def _on_worker_error(self, err: str):
        self._log(f"Processing error: {err}")
        QMessageBox.critical(self, "错误", f"Processing error: {err}")
        self._set_busy(False, "处理失败")

    def _cleanup_worker(self):
        if self._worker is not None:
            self._worker.deleteLater()
        if self._worker_thread is not None:
            self._worker_thread.deleteLater()
        self._worker = None
        self._worker_thread = None
        self._current_run_context = None

    def run_default_pipeline(self):
        if self.data is None or self.data_path is None:
            QMessageBox.warning(self, "无数据", "请先导入 CSV。")
            return
        self._log("运行默认流程v2：time-zero → dewow → 背景去除 → F-K → SEC → Hankel-SVD")
        order = ["set_zero_time", "dewow", "subtracting_average_2D", "fk_filter", "sec_gain", "hankel_svd"]
        current_idx = self.method_combo.currentIndex()
        tasks = []
        out_dir = os.path.join(BASE_DIR, "output")
        os.makedirs(out_dir, exist_ok=True)
        for key in order:
            if key in self.method_keys:
                method = PROCESSING_METHODS[key]
                params = self._resolve_method_params(key)
                tasks.append({
                    "method_key": key,
                    "method": method,
                    "params": params,
                    "out_dir": out_dir,
                })
        if not tasks:
            return
        self._push_history()
        self._start_processing_worker(tasks, run_type="pipeline", restore_method_idx=current_idx)

    # --------- Apply ---------
    def apply_method(self):
        if self.data is None or self.data_path is None:
            QMessageBox.warning(self, "No data", "Please import a CSV first.")
            return
        idx = self.method_combo.currentIndex()
        method_key = self.method_keys[idx]
        method = PROCESSING_METHODS[method_key]
        self._log(f"Applying: {method['name']}")
        self._push_history()

        try:
            params = self._get_params()
        except ValueError as e:
            QMessageBox.critical(self, "Invalid parameter", str(e))
            return
        self._method_param_overrides[method_key] = dict(params)
        if method_key == "kirchhoff_migration":
            params["_legacy_mode"] = bool(self.legacy_mode_var.isChecked())
            if params["_legacy_mode"]:
                self._log("Kirchhoff 迁移：legacy 模式已启用（测试）")
            self._log_kirchhoff_migration_config(params, source="手动执行")

        out_dir = os.path.join(BASE_DIR, "output")
        os.makedirs(out_dir, exist_ok=True)
        task = {
            "method_key": method_key,
            "method": method,
            "params": params,
            "out_dir": out_dir,
        }
        self._start_processing_worker([task], run_type="single")


def apply_theme(app: QApplication):
    """Try qt-material, then qdarkstyle. Returns theme name."""
    try:
        from qt_material import apply_stylesheet
        apply_stylesheet(app, theme="light_blue.xml")
        return "qt-material: light_blue.xml"
    except Exception:
        try:
            import qdarkstyle
            app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt6())
            return "qdarkstyle"
        except Exception:
            return "default"


def main():
    app = QApplication(sys.argv)
    theme_name = apply_theme(app)
    version_text = build_version_string("GPR_GUI")
    print(f"[GPR_GUI] version={version_text}")
    win = GPRGuiQt(version_text=version_text)
    win.statusBar().showMessage(f"Theme: {theme_name} | {version_text}")
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
