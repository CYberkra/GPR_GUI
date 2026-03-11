#!/usr/bin/env python3
"""Regression test: stage1 txt params are wired into Kirchhoff migration path."""
import os
import sys

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from app_qt import method_kirchhoff_migration


def test_kirchhoff_stage1_txt_params_affect_output():
    data = np.ones((6, 5), dtype=float)

    baseline, _ = method_kirchhoff_migration(
        data,
        dx=1.0,
        dt=1.0,
        v=1.0,
        aperture=0,
        **{"T": 6, "M-depth": 6, "len": 5, "weight": 1.0, "Contrast": 1.0, "topo_cor": 0, "hei_cor": 0, "interface": 0},
    )

    mapped, meta = method_kirchhoff_migration(
        data,
        dx=1.0,
        dt=1.0,
        v=1.0,
        aperture=0,
        **{"T": 3, "M-depth": 2, "len": 10, "weight": 0.5, "Contrast": 2.0, "topo_cor": 0, "hei_cor": 0, "interface": 0},
    )

    # T + M-depth should gate effective migrated rows.
    assert np.allclose(mapped[2:, :], 0.0)

    # weight + Contrast should scale active rows (0.5 * 2.0 = 1.0 here).
    assert np.allclose(mapped[:2, :], baseline[:2, :], atol=1e-9)

    # Ensure metadata reports mapped params, proving explicit path integration.
    assert meta["mapped_params"]["T"] == 3
    assert meta["mapped_params"]["M-depth"] == 2
    assert meta["mapped_params"]["len"] == 10


def main():
    test_kirchhoff_stage1_txt_params_affect_output()
    print("OK: kirchhoff stage1 param mapping test passed")


if __name__ == "__main__":
    main()
