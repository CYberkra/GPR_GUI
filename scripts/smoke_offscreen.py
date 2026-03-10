#!/usr/bin/env python3
"""GUI key-path offscreen smoke test.

Path covered:
1) start QApplication + main window
2) load sample CSV (via GUI load_csv path)
3) run one core processing method
4) refresh plot
5) close window and quit app

Outputs structured JSON and PASS/FAIL summary.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import time
import traceback
from pathlib import Path
from unittest.mock import patch

# Ensure repo root is importable when script is executed from scripts/
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Force headless Qt for CI/WSL servers
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "QtAgg")


def _check_qt_backend() -> tuple[str, str]:
    """Return (backend_name, version). Prefer PyQt6; fallback to PySide6."""
    for name in ("PyQt6", "PySide6"):
        try:
            mod = importlib.import_module(name)
            ver = getattr(mod, "__version__", "unknown")
            return name, str(ver)
        except Exception:
            continue
    raise RuntimeError("Neither PyQt6 nor PySide6 is importable")


def _parse_args() -> argparse.Namespace:
    default_sample = REPO_ROOT / "sample_data" / "regression_v1" / "sample_layered_small.csv"
    parser = argparse.ArgumentParser(description="Run GUI key-path smoke test in offscreen mode")
    parser.add_argument("--sample", type=Path, default=default_sample, help="CSV sample path")
    parser.add_argument("--method-key", default="dewow", help="Processing method key to run once")
    parser.add_argument("--timeout-sec", type=float, default=30.0, help="Timeout for async processing")
    parser.add_argument(
        "--json-out",
        type=Path,
        default=REPO_ROOT / "reports" / "gui_step8_smoke_result.json",
        help="Where to write structured JSON result",
    )
    return parser.parse_args()


def _wait_worker_done(app, win, timeout_sec: float) -> tuple[bool, str]:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        app.processEvents()
        worker = getattr(win, "_worker_thread", None)
        if worker is None:
            return True, "worker completed"
        time.sleep(0.02)
    return False, f"processing timeout after {timeout_sec:.1f}s"


def _refresh_plot_and_wait(app, win, timeout_sec: float = 3.0) -> tuple[bool, str]:
    before_draw = int(getattr(win, "_plot_draw_count", 0))
    before_skip = int(getattr(win, "_plot_skip_count", 0))
    win._refresh_plot()
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        app.processEvents()
        now_draw = int(getattr(win, "_plot_draw_count", 0))
        now_skip = int(getattr(win, "_plot_skip_count", 0))
        if now_draw > before_draw:
            return True, f"draw_count {before_draw} -> {now_draw}"
        if now_skip > before_skip:
            return True, f"refresh dedup skip_count {before_skip} -> {now_skip}"
        time.sleep(0.02)
    return False, "plot refresh timeout"


def main() -> int:
    args = _parse_args()
    result = {
        "name": "gui_keypath_smoke_offscreen",
        "pass": False,
        "reason": "",
        "env": {
            "python": sys.version.split()[0],
            "qt_qpa_platform": os.environ.get("QT_QPA_PLATFORM"),
        },
        "input": {
            "sample": str(args.sample),
            "method_key": args.method_key,
            "timeout_sec": args.timeout_sec,
        },
        "checkpoints": {
            "startup": False,
            "load_sample": False,
            "core_process_once": False,
            "plot_refresh": False,
            "shutdown": False,
        },
        "metrics": {},
        "error": None,
    }

    app = None
    win = None
    try:
        backend, version = _check_qt_backend()
        result["env"]["qt_backend"] = backend
        result["env"]["qt_backend_version"] = version
        if backend != "PyQt6":
            raise RuntimeError("app_qt.py requires PyQt6")

        if not args.sample.exists():
            raise FileNotFoundError(f"Sample CSV not found: {args.sample}")

        from PyQt6.QtWidgets import QApplication
        from app_qt import GPRGuiQt, apply_theme, QFileDialog

        app = QApplication.instance() or QApplication([])
        theme = apply_theme(app)
        win = GPRGuiQt()
        result["metrics"]["theme"] = theme
        result["checkpoints"]["startup"] = True

        # 1) GUI load_csv path (mock file dialog selection)
        with patch.object(QFileDialog, "getOpenFileName", return_value=(str(args.sample), "CSV 文件 (*.csv)")):
            win.load_csv()
        if getattr(win, "data", None) is None:
            raise RuntimeError("load_csv executed but win.data is None")
        result["checkpoints"]["load_sample"] = True
        result["metrics"]["data_shape"] = list(win.data.shape)

        # 2) run one core processing method
        if args.method_key not in getattr(win, "method_keys", []):
            raise RuntimeError(f"Method key not found in UI: {args.method_key}")
        method_idx = win.method_keys.index(args.method_key)
        win.method_combo.setCurrentIndex(method_idx)
        # Smoke focuses on GUI key path; bypass file-export side effects in _on_worker_finished.
        with patch.object(win, "_save_outputs", return_value=(str(REPO_ROOT / "output" / "smoke_dummy.csv"), None)):
            win.apply_method()
            ok, msg = _wait_worker_done(app, win, args.timeout_sec)
        if not ok:
            raise TimeoutError(msg)
        result["checkpoints"]["core_process_once"] = True
        result["metrics"]["process_status"] = msg

        # 3) explicit plot refresh
        ok, msg = _refresh_plot_and_wait(app, win)
        if not ok:
            raise TimeoutError(msg)
        result["checkpoints"]["plot_refresh"] = True
        result["metrics"]["plot_status"] = msg
        result["metrics"]["plot_draw_count"] = int(getattr(win, "_plot_draw_count", 0))
        result["metrics"]["plot_last_ms"] = float(getattr(win, "_last_plot_ms", 0.0))

        # 4) close
        win.close()
        app.processEvents()
        app.quit()
        result["checkpoints"]["shutdown"] = True

        result["pass"] = all(result["checkpoints"].values())
        result["reason"] = "PASS" if result["pass"] else "checkpoint incomplete"

    except Exception as exc:
        result["pass"] = False
        result["reason"] = f"FAIL: {exc}"
        result["error"] = {
            "type": exc.__class__.__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        if win is not None:
            try:
                win.close()
            except Exception:
                pass
        if app is not None:
            try:
                app.quit()
            except Exception:
                pass

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== GPR_GUI key-path offscreen smoke ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"RESULT: {'PASS' if result['pass'] else 'FAIL'} | {result['reason']}")
    print(f"JSON: {args.json_out}")

    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
