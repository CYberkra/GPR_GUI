#!/usr/bin/env python3
"""Tests for extent + axis label resolution helper."""
import os
import sys

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from app_qt import GPRGuiQt


class _ExtentGui:
    def __init__(self, header_info=None):
        self.header_info = header_info


def test_extent_labels_with_header_and_bounds():
    gui = _ExtentGui(
        {
            "total_time_ns": 120.0,
            "num_traces": 5,
            "trace_interval_m": 0.5,
        }
    )
    data = np.zeros((10, 5))
    bounds = {
        "time_start": 10.0,
        "time_end": 80.0,
        "dist_start": 0.5,
        "dist_end": 1.5,
    }
    out = GPRGuiQt._resolve_plot_extent_and_labels(gui, data, bounds)
    assert out["extent"] == [0.5, 1.5, 80.0, 10.0]
    assert out["xlabel"] == "距离 (m)"
    assert out["ylabel"] == "时间 (ns)"


def test_extent_labels_without_header_and_without_bounds():
    gui = _ExtentGui()
    data = np.zeros((8, 4))
    out = GPRGuiQt._resolve_plot_extent_and_labels(gui, data, None)
    assert out["extent"] is None
    assert out["xlabel"] == "距离（道索引）"
    assert out["ylabel"] == "时间（采样索引）"


def main():
    test_extent_labels_with_header_and_bounds()
    test_extent_labels_without_header_and_without_bounds()
    print("OK: extent/labels helper tests passed")


if __name__ == "__main__":
    main()
