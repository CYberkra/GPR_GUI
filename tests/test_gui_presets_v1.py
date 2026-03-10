#!/usr/bin/env python3
"""Preset system regression tests (Week2 Day8-Day9)."""
import os
import sys

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from app_qt import GPRGuiQt, PROCESSING_METHODS


class _DummyCheck:
    def __init__(self, checked=False):
        self._checked = checked

    def setChecked(self, v):
        self._checked = bool(v)

    def isChecked(self):
        return self._checked


class _DummyEdit:
    def __init__(self, text=""):
        self._text = str(text)

    def setText(self, v):
        self._text = str(v)

    def text(self):
        return self._text


class _DummyCombo:
    def __init__(self, idx=0):
        self._idx = idx

    def currentIndex(self):
        return self._idx


class _DummyStatus:
    def __init__(self):
        self.last_text = ""

    def setText(self, text):
        self.last_text = text


class _DummyGui:
    def __init__(self):
        self.fast_preview_var = _DummyCheck(False)
        self.max_samples_edit = _DummyEdit("512")
        self.max_traces_edit = _DummyEdit("200")
        self.display_downsample_var = _DummyCheck(True)
        self.display_max_samples_edit = _DummyEdit("800")
        self.display_max_traces_edit = _DummyEdit("400")
        self.normalize_var = _DummyCheck(False)
        self.demean_var = _DummyCheck(False)
        self.percentile_var = _DummyCheck(False)
        self.p_low_edit = _DummyEdit("1")
        self.p_high_edit = _DummyEdit("99")
        self.method_keys = ["set_zero_time", "dewow", "hankel_svd"]
        self.method_combo = _DummyCombo(0)
        self._method_param_overrides = {}
        self._selected_preset_key = None
        self.status_label = _DummyStatus()
        self.log_lines = []
        self.rendered_method = None

    def _render_params(self, method_key):
        self.rendered_method = method_key

    def _log(self, msg):
        self.log_lines.append(msg)

    def _refresh_plot(self):
        return


def test_apply_quick_preview_preset_updates_key_controls_and_params():
    gui = _DummyGui()
    GPRGuiQt._apply_preset_by_key(gui, "quick_preview")

    assert gui.fast_preview_var.isChecked() is True
    assert gui.max_samples_edit.text() == "256"
    assert gui.max_traces_edit.text() == "120"
    assert gui._method_param_overrides["hankel_svd"]["window_length"] == 48
    assert gui._method_param_overrides["hankel_svd"]["rank"] == 1
    assert "已应用预设" in gui.status_label.last_text


def test_preset_switch_keeps_pipeline_param_resolution_stable():
    gui = _DummyGui()
    GPRGuiQt._apply_preset_by_key(gui, "quick_preview")
    quick_params = GPRGuiQt._resolve_method_params(gui, "hankel_svd")
    assert quick_params["rank"] == 1

    GPRGuiQt._apply_preset_by_key(gui, "denoise_first")
    denoise_params = GPRGuiQt._resolve_method_params(gui, "hankel_svd")
    assert denoise_params["rank"] == 2

    for key in ["set_zero_time", "dewow", "hankel_svd"]:
        resolved = GPRGuiQt._resolve_method_params(gui, key)
        for p in PROCESSING_METHODS[key].get("params", []):
            assert p["name"] in resolved
