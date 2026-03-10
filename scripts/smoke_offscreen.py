#!/usr/bin/env python3
"""Offscreen smoke test for GUI runtime without launching full interactive app."""

from __future__ import annotations

import importlib
import os
import sys
import traceback
from pathlib import Path

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


def main() -> int:
    print("=== GPR_GUI offscreen smoke ===")
    print(f"Python: {sys.version.split()[0]}")
    print(f"QT_QPA_PLATFORM={os.environ.get('QT_QPA_PLATFORM')}")

    try:
        backend, version = _check_qt_backend()
        print(f"Qt backend detected: {backend} ({version})")

        # app_qt currently depends on PyQt6 symbols; enforce clear diagnostic
        if backend != "PyQt6":
            print("WARN: backend is not PyQt6. app_qt.py requires PyQt6 imports.")

        from PyQt6.QtWidgets import QApplication
        from app_qt import GPRGuiQt, apply_theme

        app = QApplication.instance() or QApplication([])
        theme = apply_theme(app)
        win = GPRGuiQt()

        _ = win.windowTitle()
        _ = win.method_combo.count()
        if hasattr(win, "display_downsample_var"):
            _ = win.display_downsample_var.isChecked()

        print(f"Theme resolved: {theme}")
        print("Smoke checkpoints: QApplication OK, GPRGuiQt init OK, core widgets OK")

        win.close()
        app.quit()
        print("RESULT: PASS")
        return 0
    except Exception as exc:
        print(f"RESULT: FAIL -> {exc}")
        traceback.print_exc()
        print("\nRecommended fix:")
        print("  python3 -m pip install -r requirements-dev.txt")
        print("Then re-run:")
        print("  python3 scripts/env_check.py")
        print("  QT_QPA_PLATFORM=offscreen python3 scripts/smoke_offscreen.py")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
