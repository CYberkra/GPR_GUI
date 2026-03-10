#!/usr/bin/env python3
"""Environment validator for GPR_GUI Day1-Day2 hardening."""

from __future__ import annotations

import importlib
import platform
import sys
from dataclasses import dataclass


@dataclass
class CheckItem:
    name: str
    import_name: str
    required: bool = True
    note: str = ""


CHECKS = [
    CheckItem("numpy", "numpy", True),
    CheckItem("pandas", "pandas", True),
    CheckItem("scipy", "scipy", True),
    CheckItem("matplotlib", "matplotlib", True),
    CheckItem("PyQt6", "PyQt6", True, "GUI backend required by app_qt.py"),
    CheckItem("qt-material", "qt_material", False, "optional theme"),
    CheckItem("qdarkstyle", "qdarkstyle", False, "optional theme fallback"),
    CheckItem("pytest", "pytest", False, "recommended for test execution"),
]


def _version_of(module) -> str:
    for attr in ("__version__", "VERSION"):
        value = getattr(module, attr, None)
        if value:
            return str(value)
    return "unknown"


def main() -> int:
    print("=== GPR_GUI Environment Check ===")
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    print(f"Platform: {platform.platform()}")
    print()

    missing_required: list[str] = []
    missing_optional: list[str] = []

    for item in CHECKS:
        try:
            module = importlib.import_module(item.import_name)
            version = _version_of(module)
            print(f"[OK ] {item.name:<12} {version}")
        except Exception as exc:  # broad on purpose for broken installations
            state = "MISS" if item.required else "WARN"
            print(f"[{state}] {item.name:<12} import failed: {exc}")
            if item.note:
                print(f"      └─ {item.note}")
            if item.required:
                missing_required.append(item.name)
            else:
                missing_optional.append(item.name)

    print()
    print("Backend note: this repo uses PyQt6 in app_qt.py.")
    print("If previous scripts expected PySide6, use scripts/smoke_offscreen.py (backend-agnostic).")

    if missing_required:
        print("\nRESULT: FAIL (missing required packages)")
        print("Install with:")
        print("  python3 -m pip install -r requirements-dev.txt")
        print("Missing required:", ", ".join(missing_required))
        if "PyQt6" in missing_required:
            print("PyQt6 is mandatory for current GUI entrypoint app_qt.py.")
        return 1

    if missing_optional:
        print("\nRESULT: PASS (with warnings)")
        print("Optional missing:", ", ".join(missing_optional))
        print("GUI can still run; theme may downgrade to default.")
        return 0

    print("\nRESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
