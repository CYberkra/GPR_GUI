#!/usr/bin/env python3
"""Regression tests for explainable error UX messages (Week1 Day6-Day7)."""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from app_qt import GPRGuiQt, build_csv_load_error_message, build_processing_error_message


class _DummyEdit:
    def __init__(self, text: str):
        self._text = text

    def text(self):
        return self._text


class _DummyGuiForParams:
    def __init__(self):
        self.param_vars = {
            "window": (
                _DummyEdit("abc"),
                {"label": "Window (samples)", "type": "int", "default": 41, "min": 1, "max": 1000},
            )
        }


def test_csv_error_message_contains_required_sections():
    msg = build_csv_load_error_message(ValueError("simulated csv parse error"))
    assert "发生了什么：" in msg
    assert "可能原因：" in msg
    assert "下一步建议：" in msg
    assert "技术详情：" in msg
    assert "CSV" in msg


def test_invalid_param_message_triggered_from_get_params():
    gui = _DummyGuiForParams()
    try:
        GPRGuiQt._get_params(gui)
        assert False, "Expected ValueError"
    except ValueError as e:
        msg = str(e)
        assert "发生了什么：" in msg
        assert "可能原因：" in msg
        assert "下一步建议：" in msg
        assert "Window (samples)" in msg


def test_processing_error_message_contains_method_context():
    msg = build_processing_error_message(RuntimeError("boom"), "dewow")
    assert "处理流程" in msg
    assert "dewow" in msg
    assert "下一步建议：" in msg


if __name__ == "__main__":
    test_csv_error_message_contains_required_sections()
    test_invalid_param_message_triggered_from_get_params()
    test_processing_error_message_contains_method_context()
    print("OK: error message UX regression tests passed")
