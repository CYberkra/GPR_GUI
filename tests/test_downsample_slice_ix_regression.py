#!/usr/bin/env python3
"""Regression tests for slice + np.ix_ indexing pitfalls."""
import os
import sys

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from app_qt import GPRGuiQt


def test_select_2d_mixed_slice_and_array_indices():
    data = np.arange(30, dtype=float).reshape(5, 6)
    row_idx = slice(None)  # simulates max_samples <= 0 or no row downsample
    col_idx = np.array([0, 2, 5], dtype=int)

    out = GPRGuiQt._select_2d(data, row_idx, col_idx)

    assert out.shape == (5, 3)
    assert np.array_equal(out, data[:, [0, 2, 5]])


def test_downsample_data_handles_slice_plus_array_without_cross_index_error():
    class _DummyCheck:
        def __init__(self, checked):
            self._checked = checked

        def isChecked(self):
            return self._checked

    class _DummyEdit:
        def __init__(self, value):
            self._value = value

        def text(self):
            return self._value

    class _DummyGui:
        def __init__(self):
            self.fast_preview_var = _DummyCheck(True)
            self.max_samples_edit = _DummyEdit("0")
            self.max_traces_edit = _DummyEdit("3")
            self._ds_cache = {}

        def _parse_int_edit(self, edit, default=0):
            return GPRGuiQt._parse_int_edit(self, edit, default)

        def _get_downsample_indices(self, n_time, n_dist, max_samples, max_traces):
            return GPRGuiQt._get_downsample_indices(self, n_time, n_dist, max_samples, max_traces)

        _select_2d = staticmethod(GPRGuiQt._select_2d)

    gui = _DummyGui()
    data = np.arange(80, dtype=float).reshape(10, 8)

    out = GPRGuiQt._downsample_data(gui, data)

    assert out.shape == (10, 3)


def main():
    test_select_2d_mixed_slice_and_array_indices()
    test_downsample_data_handles_slice_plus_array_without_cross_index_error()
    print("OK: downsample slice+ix regression passed")


if __name__ == "__main__":
    main()
