#!/usr/bin/env python3
"""Regression: save_image should accept cmap kwarg without TypeError."""
import os
import sys
import tempfile

import numpy as np

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from read_file_data import save_image


def test_save_image_accepts_cmap_kwarg_and_saves_file():
    data = np.arange(16, dtype=float).reshape(4, 4)
    with tempfile.TemporaryDirectory() as td:
        out_png = os.path.join(td, "out.png")
        # This call previously raised:
        # TypeError: save_image() got an unexpected keyword argument 'cmap'
        save_image(data, out_png, title="regression", cmap="viridis")
        assert os.path.exists(out_png)
        assert os.path.getsize(out_png) > 0
