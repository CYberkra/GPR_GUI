#!/usr/bin/env python3
"""Minimal repro/verification for save_image cmap mismatch.

- Reproduces historical failure by prioritizing sibling PythonModule on sys.path.
- Verifies fixed runtime path via gpr_io bridge (always local module).
"""
from __future__ import annotations

import inspect
import os
import sys
import tempfile

import numpy as np

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PYTHONMODULE_DIR = os.path.abspath(os.path.join(REPO_DIR, "..", "PythonModule"))


def repro_old_failure() -> None:
    sys.path[:] = [PYTHONMODULE_DIR, REPO_DIR] + [p for p in sys.path if p not in (PYTHONMODULE_DIR, REPO_DIR)]
    import read_file_data as rfd  # resolves to PythonModule/read_file_data.py when path polluted

    print("[repro] read_file_data file:", rfd.__file__)
    print("[repro] save_image signature:", inspect.signature(rfd.save_image))

    with tempfile.TemporaryDirectory() as td:
        out_png = os.path.join(td, "old.png")
        try:
            rfd.save_image(np.ones((4, 4)), out_png, cmap="viridis")
            print("[repro] unexpected: no error")
        except TypeError as e:
            print("[repro] expected TypeError:", e)


def verify_fixed_path() -> None:
    # Keep polluted path to prove gpr_io is robust.
    sys.path[:] = [PYTHONMODULE_DIR, REPO_DIR] + [p for p in sys.path if p not in (PYTHONMODULE_DIR, REPO_DIR)]
    import gpr_io

    print("[verify]", gpr_io.runtime_save_image_debug())

    with tempfile.TemporaryDirectory() as td:
        out_png = os.path.join(td, "fixed.png")
        gpr_io.save_image(np.arange(16).reshape(4, 4), out_png, title="ok", cmap="viridis")
        print("[verify] wrote:", out_png, "size=", os.path.getsize(out_png))


if __name__ == "__main__":
    repro_old_failure()
    print("-" * 60)
    verify_fixed_path()
