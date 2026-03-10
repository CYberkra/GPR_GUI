#!/usr/bin/env python3
"""Tests for lightweight GUI observability panel bindings and switch isolation."""
import os
import sys

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from app_qt import GPRGuiQt


class _Label:
    def __init__(self):
        self.text_value = ""

    def setText(self, text):
        self.text_value = text


class _Check:
    def __init__(self, checked=False):
        self._checked = checked

    def setChecked(self, checked):
        self._checked = bool(checked)

    def isChecked(self):
        return self._checked


class _ObsBindingGui:
    def __init__(self):
        self._last_plot_ms = 12.345
        self._plot_draw_count = 7
        self._plot_skip_count = 3
        self._last_prepare_ms = 4.567
        self.obs_last_plot_label = _Label()
        self.obs_draw_count_label = _Label()
        self.obs_skip_count_label = _Label()
        self.obs_last_prepare_label = _Label()


class _ObsToggleGui:
    def __init__(self):
        self.data = np.zeros((3, 3))
        self._data_revision = 1
        self._last_plot_signature = None
        self._plot_skip_count = 0
        self.plot_calls = 0
        self.observability_box = _Check(False)

    def _build_plot_ui_signature(self):
        # Intentionally independent from observability toggle.
        return ("static-ui",)

    def _build_plot_signature(self):
        return GPRGuiQt._build_plot_signature(self)

    def plot_data(self, data):
        self.plot_calls += 1
        self._last_plot_signature = GPRGuiQt._build_plot_signature(self)

    def _log_plot_debug(self, message):
        return None

    def _refresh_observability_panel(self):
        return None


def test_observability_metrics_binding_updates_labels():
    gui = _ObsBindingGui()

    GPRGuiQt._refresh_observability_panel(gui)

    assert gui.obs_last_plot_label.text_value == "最近绘制耗时：12.35 ms"
    assert gui.obs_draw_count_label.text_value == "累计绘制次数：7"
    assert gui.obs_skip_count_label.text_value == "累计跳过重绘：3"
    assert gui.obs_last_prepare_label.text_value == "最近预处理耗时：4.57 ms"


def test_observability_toggle_does_not_change_refresh_flow():
    gui = _ObsToggleGui()

    GPRGuiQt._do_refresh_plot(gui)
    assert gui.plot_calls == 1
    assert gui._plot_skip_count == 0

    # Toggle panel visibility switch; redraw decision should remain unchanged.
    gui.observability_box.setChecked(True)
    GPRGuiQt._do_refresh_plot(gui)

    assert gui.plot_calls == 1
    assert gui._plot_skip_count == 1


def main():
    test_observability_metrics_binding_updates_labels()
    test_observability_toggle_does_not_change_refresh_flow()
    print("OK: observability panel tests passed")


if __name__ == "__main__":
    main()
