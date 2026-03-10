#!/usr/bin/env python3
"""Lightweight tests for GPRGuiQt._build_compare_data_pairs."""
import os
import sys

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from app_qt import GPRGuiQt


class _BoolVar:
    def __init__(self, checked=False):
        self._checked = checked

    def isChecked(self):
        return self._checked


class _Combo:
    def __init__(self, idx=0):
        self._idx = idx

    def currentIndex(self):
        return self._idx


class _DummyGui:
    def __init__(self, compare_enabled, snapshots, left_idx=0, right_idx=0):
        self.compare_var = _BoolVar(compare_enabled)
        self.compare_snapshots = snapshots
        self.compare_left_combo = _Combo(left_idx)
        self.compare_right_combo = _Combo(right_idx)
        self.prepare_calls = []

    def _prepare_view_data(self, data):
        self.prepare_calls.append(data)
        return data, None


def _sample_array(seed):
    rng = np.random.default_rng(seed)
    return rng.standard_normal((3, 2))


def test_empty_snapshots_falls_back_to_display_data():
    display_data = _sample_array(0)
    gui = _DummyGui(compare_enabled=True, snapshots=[])
    out = GPRGuiQt._build_compare_data_pairs(gui, display_data)
    assert len(out) == 1
    assert out[0][1] == "B-扫"
    assert np.array_equal(out[0][0], display_data)


def test_single_snapshot_uses_same_snapshot_twice():
    snap0 = {"label": "S0", "data": _sample_array(1)}
    gui = _DummyGui(compare_enabled=True, snapshots=[snap0], left_idx=0, right_idx=99)
    out = GPRGuiQt._build_compare_data_pairs(gui, _sample_array(2))
    assert len(out) == 2
    assert out[0][1] == "S0" and out[1][1] == "S0"
    assert np.array_equal(out[0][0], snap0["data"])
    assert np.array_equal(out[1][0], snap0["data"])


def test_two_snapshots_clamps_out_of_range_indexes():
    snap0 = {"label": "S0", "data": _sample_array(3)}
    snap1 = {"label": "S1", "data": _sample_array(4)}
    gui = _DummyGui(compare_enabled=True, snapshots=[snap0, snap1], left_idx=9, right_idx=8)
    out = GPRGuiQt._build_compare_data_pairs(gui, _sample_array(5))
    assert [x[1] for x in out] == ["S1", "S1"]


def test_negative_indexes_are_corrected_to_zero():
    snap0 = {"label": "S0", "data": _sample_array(6)}
    snap1 = {"label": "S1", "data": _sample_array(7)}
    gui = _DummyGui(compare_enabled=True, snapshots=[snap0, snap1], left_idx=-3, right_idx=-1)
    out = GPRGuiQt._build_compare_data_pairs(gui, _sample_array(8))
    assert [x[1] for x in out] == ["S0", "S0"]


def test_compare_disabled_ignores_snapshots_and_indexes():
    display_data = _sample_array(9)
    snap0 = {"label": "S0", "data": _sample_array(10)}
    snap1 = {"label": "S1", "data": _sample_array(11)}
    gui = _DummyGui(compare_enabled=False, snapshots=[snap0, snap1], left_idx=1, right_idx=0)
    out = GPRGuiQt._build_compare_data_pairs(gui, display_data)
    assert out == [(display_data, "B-扫")]
    assert gui.prepare_calls == []


def test_mixed_valid_indexes_preserve_order_and_prepare_each_selected_snapshot():
    snap0 = {"label": "S0", "data": _sample_array(12)}
    snap1 = {"label": "S1", "data": _sample_array(13)}
    snap2 = {"label": "S2", "data": _sample_array(14)}
    gui = _DummyGui(compare_enabled=True, snapshots=[snap0, snap1, snap2], left_idx=0, right_idx=2)
    out = GPRGuiQt._build_compare_data_pairs(gui, _sample_array(15))
    assert [x[1] for x in out] == ["S0", "S2"]
    assert np.array_equal(out[0][0], snap0["data"])
    assert np.array_equal(out[1][0], snap2["data"])
    assert len(gui.prepare_calls) == 2
    assert np.array_equal(gui.prepare_calls[0], snap0["data"])
    assert np.array_equal(gui.prepare_calls[1], snap2["data"])


def main():
    test_empty_snapshots_falls_back_to_display_data()
    test_single_snapshot_uses_same_snapshot_twice()
    test_two_snapshots_clamps_out_of_range_indexes()
    test_negative_indexes_are_corrected_to_zero()
    test_compare_disabled_ignores_snapshots_and_indexes()
    test_mixed_valid_indexes_preserve_order_and_prepare_each_selected_snapshot()
    print("OK: _build_compare_data_pairs lightweight tests passed")


if __name__ == "__main__":
    main()
