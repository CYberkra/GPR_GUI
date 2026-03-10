#!/usr/bin/env python3
"""Regression tests for GPRGuiQt._render_data_pairs refactor."""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from app_qt import GPRGuiQt


class _Axis:
    def __init__(self):
        self.title = None
        self.xlabel = None
        self.ylabel = None

    def set_title(self, title):
        self.title = title

    def set_xlabel(self, text):
        self.xlabel = text

    def set_ylabel(self, text):
        self.ylabel = text


class _DummyGui:
    def __init__(self):
        self.calls = []
        self.draw_count = 0
        self.debug_logs = []

    def _draw_image_with_colormap(self, ax, data, cmap, extent):
        self.calls.append((ax, data, cmap, extent))
        self.draw_count += 1
        return f"im-{self.draw_count}", " (suffix)"

    def _apply_axis_labels(self, ax, labels):
        GPRGuiQt._apply_axis_labels(self, ax, labels)

    def _apply_axis_grid(self, ax):
        # noop for lightweight test
        self.calls.append(("grid", ax))

    def _log_plot_debug(self, message):
        self.debug_logs.append(message)


def test_render_data_pairs_sets_titles_and_returns_last_image():
    gui = _DummyGui()
    axes = [_Axis(), _Axis()]
    data_pairs = [([1], "Left"), ([2], "Right")]
    plot_config = {"xlabel": "距离", "ylabel": "时间"}

    last_im = GPRGuiQt._render_data_pairs(gui, axes, data_pairs, "gray", [0, 1, 2, 3], plot_config)

    assert last_im == "im-2"
    assert axes[0].title == "Left (suffix)"
    assert axes[1].title == "Right (suffix)"
    assert axes[0].xlabel == "距离" and axes[0].ylabel == "时间"
    assert axes[1].xlabel == "距离" and axes[1].ylabel == "时间"
    assert any("compare render:" in msg for msg in gui.debug_logs)


def test_render_data_pairs_single_panel_has_no_compare_metric():
    gui = _DummyGui()
    axes = [_Axis()]
    data_pairs = [([1], "Only")]
    plot_config = {"xlabel": "x", "ylabel": "y"}

    GPRGuiQt._render_data_pairs(gui, axes, data_pairs, "gray", None, plot_config)

    assert axes[0].title == "Only (suffix)"
    assert not any("compare render:" in msg for msg in gui.debug_logs)


def main():
    test_render_data_pairs_sets_titles_and_returns_last_image()
    test_render_data_pairs_single_panel_has_no_compare_metric()
    print("OK: _render_data_pairs regression tests passed")


if __name__ == "__main__":
    main()
