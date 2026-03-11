#!/usr/bin/env python3
import os
import sys
import inspect

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PYTHONMODULE_DIR = os.path.abspath(os.path.join(REPO_DIR, "..", "PythonModule"))

# Simulate polluted path order that previously caused wrong module import.
sys.path[:] = [PYTHONMODULE_DIR, REPO_DIR] + [p for p in sys.path if p not in (PYTHONMODULE_DIR, REPO_DIR)]

import gpr_io


def test_runtime_save_image_comes_from_local_repo_module():
    mod = inspect.getmodule(gpr_io.save_image)
    assert mod is not None
    assert os.path.samefile(mod.__file__, os.path.join(REPO_DIR, "read_file_data.py"))
    sig = str(inspect.signature(gpr_io.save_image))
    assert "cmap" in sig
    assert "**" in sig
