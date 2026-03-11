from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import List

import numpy as np

try:
    import cupy as cp  # noqa: F401
    from numba import cuda  # noqa: F401
except Exception:  # pragma: no cover
    cp = None
    cuda = None


_REQUIRED_FILES = [
    "RTM.py",
    "updatafwd.py",
    "updatabwd.py",
    "FDTD/tools.py",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def candidate_rtm_roots() -> List[Path]:
    repo_root = _repo_root()
    sibling_python_module = repo_root.parent / "PythonModule"
    return [
        repo_root / "tools" / "rtm_legacy",
        repo_root / "legacy",
        sibling_python_module,
    ]


def discover_missing_rtm_dependencies() -> List[str]:
    """Return missing dependency file list for the first usable RTM root.

    We check known legacy locations and report against the first location that has RTM.py,
    otherwise against tools/rtm_legacy (preferred vendored location).
    """
    roots = candidate_rtm_roots()
    preferred = roots[0]

    target = preferred
    for root in roots:
        if (root / "RTM.py").exists():
            target = root
            break

    missing: List[str] = []
    for rel in _REQUIRED_FILES:
        if not (target / rel).exists():
            missing.append(str(target / rel))
    return missing


def _load_legacy_rtm_module():
    """Load legacy RTM.py from candidate roots by prepending sys.path."""
    last_err: Exception | None = None
    for root in candidate_rtm_roots():
        if not (root / "RTM.py").exists():
            continue

        root_s = str(root)
        if root_s not in sys.path:
            sys.path.insert(0, root_s)

        try:
            return importlib.import_module("RTM")
        except Exception as exc:  # pragma: no cover
            last_err = exc
            continue

    if last_err is not None:
        raise RuntimeError(f"Failed to import legacy RTM module: {last_err}")
    raise FileNotFoundError("RTM.py not found in candidate roots")


def rtm_gpu(*args, **kwargs):
    """Legacy RTM GPU entry.

    This wrapper validates runtime dependencies and then dispatches to legacy RTM.rtm_gpu.
    """
    if cp is None or cuda is None:
        raise RuntimeError("RTM GPU dependencies unavailable: require cupy + numba[cuda]")

    missing = discover_missing_rtm_dependencies()
    if missing:
        raise FileNotFoundError(
            "Legacy RTM dependency chain incomplete. Missing files:\n- " + "\n- ".join(missing)
        )

    module = _load_legacy_rtm_module()
    if not hasattr(module, "rtm_gpu"):
        raise AttributeError("Legacy RTM module does not export rtm_gpu")

    return module.rtm_gpu(*args, **kwargs)
