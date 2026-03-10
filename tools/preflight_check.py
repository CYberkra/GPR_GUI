#!/usr/bin/env python3
"""Release preflight checker for Windows GUI artifact."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path


@dataclass
class CheckResult:
    artifact_exists: bool
    artifact_size_bytes: int | None
    artifact_mtime: str | None
    verify_log_exists: bool
    verify_fields: dict
    release_version_exists: bool
    release_version: str | None
    git_short_head: str | None
    commit_aligned: bool


def _git_short_head(repo_root: Path) -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short=7", "HEAD"], cwd=repo_root, text=True
        ).strip()
        return out
    except Exception:
        return None


def _read_verify_fields(path: Path) -> dict:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip().lstrip("\ufeff")
        if "=" in line and not line.startswith("----"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")


def run(repo_root: Path, artifact_rel: str) -> CheckResult:
    artifact = repo_root / artifact_rel
    base = artifact.stem
    verify_log = artifact.with_name(f"{base}_pe_verify.txt")
    release_version_file = artifact.with_name("RELEASE_VERSION.txt")

    verify_fields = _read_verify_fields(verify_log)
    release_version = None
    if release_version_file.exists():
        release_version = release_version_file.read_text(encoding="utf-8", errors="ignore").strip().lstrip("\ufeff")

    git_short = _git_short_head(repo_root)
    commit_aligned = False
    if release_version and git_short:
        m = re.search(r"([0-9a-f]{7})$", release_version)
        commit_aligned = bool(m and m.group(1) == git_short)

    return CheckResult(
        artifact_exists=artifact.exists(),
        artifact_size_bytes=artifact.stat().st_size if artifact.exists() else None,
        artifact_mtime=_iso_mtime(artifact) if artifact.exists() else None,
        verify_log_exists=verify_log.exists(),
        verify_fields=verify_fields,
        release_version_exists=release_version_file.exists(),
        release_version=release_version,
        git_short_head=git_short,
        commit_aligned=commit_aligned,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Check windows release preflight")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--artifact", required=True, help="Path relative to repo root")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    result = run(repo_root, args.artifact)
    data = asdict(result)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print("[preflight]")
        for k, v in data.items():
            print(f"{k}: {v}")

    hard_fail = not (
        result.artifact_exists
        and result.verify_log_exists
        and result.release_version_exists
        and str(result.verify_fields.get("pe_verify_passed", "")).lower() == "true"
        and result.commit_aligned
    )
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
