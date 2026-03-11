#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stable local I/O bridge for GPR_GUI.

Avoids accidental import of homonymous ``read_file_data`` modules from sibling
repos / polluted ``sys.path`` (e.g. PythonModule/read_file_data.py).
"""
from __future__ import annotations

import importlib.util
import inspect
import os
import sys
from types import ModuleType

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_LOCAL_READ_FILE_DATA = os.path.join(BASE_DIR, "read_file_data.py")


def _load_local_read_file_data() -> ModuleType:
    spec = importlib.util.spec_from_file_location("gpr_gui_read_file_data", _LOCAL_READ_FILE_DATA)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load local read_file_data.py from: {_LOCAL_READ_FILE_DATA}")
    mod = importlib.util.module_from_spec(spec)
    # Register for inspect/module introspection.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_rfd = _load_local_read_file_data()

readcsv = _rfd.readcsv
savecsv = _rfd.savecsv
save_image = _rfd.save_image
show_image = _rfd.show_image


def runtime_save_image_debug() -> str:
    """Return runtime module path + callable signature for diagnostics."""
    mod = inspect.getmodule(save_image)
    mod_file = getattr(mod, "__file__", "<unknown>") if mod else "<unknown>"
    return f"module={save_image.__module__} file={mod_file} sig={inspect.signature(save_image)}"
