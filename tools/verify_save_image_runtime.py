#!/usr/bin/env python3
"""Print runtime save_image source module/path/signature."""
from __future__ import annotations

import os
import sys

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

import gpr_io

print(gpr_io.runtime_save_image_debug())
