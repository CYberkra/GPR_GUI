#!/usr/bin/env python3
"""Regression matrix for redraw/skip decisions based on plot signature."""
import os
import sys

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from app_qt import GPRGuiQt


class _SignatureGui:
    def __init__(self):
        self.data = np.zeros((4, 3))
        self._data_revision = 1
        self.ui_signature = ("default",)
        self._last_plot_signature = None
        self.plot_calls = 0
        self._plot_skip_count = 0
        self.debug_logs = []

    def _build_plot_ui_signature(self):
        return self.ui_signature

    def _build_plot_signature(self):
        return GPRGuiQt._build_plot_signature(self)

    def plot_data(self, data):
        self.plot_calls += 1
        self._last_plot_signature = GPRGuiQt._build_plot_signature(self)

    def _log_plot_debug(self, message):
        self.debug_logs.append(message)


def test_render_signature_matrix():
    gui = _SignatureGui()

    # 1) first render should draw
    GPRGuiQt._do_refresh_plot(gui)
    assert gui.plot_calls == 1
    assert gui._plot_skip_count == 0

    # 2) unchanged signature should skip
    GPRGuiQt._do_refresh_plot(gui)
    assert gui.plot_calls == 1
    assert gui._plot_skip_count == 1

    # 3) UI switch should trigger redraw
    gui.ui_signature = ("grid:on",)
    GPRGuiQt._do_refresh_plot(gui)
    assert gui.plot_calls == 2
    assert gui._plot_skip_count == 1

    # 4) data revision bump should trigger redraw
    gui._data_revision += 1
    GPRGuiQt._do_refresh_plot(gui)
    assert gui.plot_calls == 3
    assert gui._plot_skip_count == 1

    # 5) no data should no-op
    gui.data = None
    GPRGuiQt._do_refresh_plot(gui)
    assert gui.plot_calls == 3
    assert gui._plot_skip_count == 1


def main():
    test_render_signature_matrix()
    print("OK: plot signature redraw matrix passed")


if __name__ == "__main__":
    main()
