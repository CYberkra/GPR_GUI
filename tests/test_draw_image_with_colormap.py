#!/usr/bin/env python3
"""Lightweight branch tests for GPRGuiQt._draw_image_with_colormap."""
import os
import sys

import numpy as np
from matplotlib.figure import Figure

# Ensure Qt can initialize in CI/headless shells.
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


class _DummyGui:
    def __init__(self, *, chatgpt=False, symmetric=False, perc_bounds=None):
        self.chatgpt_style_var = _BoolVar(chatgpt)
        self.symmetric_var = _BoolVar(symmetric)
        self._perc_bounds = perc_bounds

    def _clip_for_display(self, data, clip_percent=99.0):
        # Deterministic clipped output for assertion.
        return data * 0.5, 2.5

    def _get_percentile_bounds(self, _data):
        return self._perc_bounds


def _new_ax():
    fig = Figure()
    return fig.add_subplot(1, 1, 1)


def test_chatgpt_style_branch():
    gui = _DummyGui(chatgpt=True)
    ax = _new_ax()
    data = np.array([[1.0, -3.0], [2.0, 4.0]])
    im, suffix = GPRGuiQt._draw_image_with_colormap(gui, ax, data, "gray", [0, 1, 1, 0])
    assert suffix == " (clip=±2.5)", suffix
    assert im.get_clim() == (-2.5, 2.5)


def test_symmetric_branch():
    gui = _DummyGui(chatgpt=False, symmetric=True)
    ax = _new_ax()
    data = np.array([[1.0, -3.0], [2.0, 4.0]])
    im, suffix = GPRGuiQt._draw_image_with_colormap(gui, ax, data, "viridis", None)
    assert suffix == ""
    assert im.get_clim() == (-4.0, 4.0)


def test_percentile_branch():
    gui = _DummyGui(chatgpt=False, symmetric=False, perc_bounds=(-1.0, 3.0))
    ax = _new_ax()
    data = np.array([[1.0, -3.0], [2.0, 4.0]])
    im, suffix = GPRGuiQt._draw_image_with_colormap(gui, ax, data, "magma", None)
    assert suffix == ""
    assert im.get_clim() == (-1.0, 3.0)


def main():
    test_chatgpt_style_branch()
    test_symmetric_branch()
    test_percentile_branch()
    print("OK: _draw_image_with_colormap branch tests passed")


if __name__ == "__main__":
    main()
