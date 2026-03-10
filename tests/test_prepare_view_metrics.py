#!/usr/bin/env python3
"""Regression tests for GPRGuiQt._prepare_view_data debug metrics."""
import os
import sys

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from app_qt import GPRGuiQt


class _DummyGui:
    def __init__(self):
        self.logs = []

    def _apply_preprocess(self, data):
        return data + 1

    def _apply_crop(self, data):
        return data[:2, :], {"mock": True}

    def _downsample_for_display(self, data):
        return data[:, :1]

    def _log_plot_debug(self, message):
        self.logs.append(message)


def test_prepare_view_data_logs_elapsed_and_shape():
    gui = _DummyGui()
    data = np.arange(12, dtype=float).reshape(3, 4)

    out, bounds = GPRGuiQt._prepare_view_data(gui, data)

    assert out.shape == (2, 1)
    assert bounds == {"mock": True}
    assert len(gui.logs) == 1
    assert "prepare view:" in gui.logs[0]
    assert "shape=2x1" in gui.logs[0]


def main():
    test_prepare_view_data_logs_elapsed_and_shape()
    print("OK: _prepare_view_data metrics test passed")


if __name__ == "__main__":
    main()
