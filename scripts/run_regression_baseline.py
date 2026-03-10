#!/usr/bin/env python3
"""Run lightweight regression baseline on a manifest-defined GPR sample set.

Outputs:
- JSON metrics (machine diff friendly)
- Markdown summary report (human readable)
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "tests" / "regression_samples_manifest.json"
DEFAULT_JSON = REPO_ROOT / "reports" / "regression_baseline_v1.json"
DEFAULT_MD = REPO_ROOT / "reports" / "regression_baseline_v1.md"


def _safe_stats(arr: np.ndarray) -> dict:
    flat = np.asarray(arr, dtype=float).reshape(-1)
    return {
        "min": float(np.min(flat)),
        "max": float(np.max(flat)),
        "mean": float(np.mean(flat)),
        "std": float(np.std(flat)),
        "abs_mean": float(np.mean(np.abs(flat))),
        "p01": float(np.percentile(flat, 1)),
        "p99": float(np.percentile(flat, 99)),
    }


def _load_csv(path: Path) -> np.ndarray:
    df = pd.read_csv(path, header=None)
    arr = df.values.astype(float)
    return arr


def _light_pipeline(arr: np.ndarray) -> np.ndarray:
    x = np.asarray(arr, dtype=float)
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)

    # 1) Demean by trace (axis=0)
    x = x - np.mean(x, axis=0, keepdims=True)

    # 2) Background suppression (subtract row mean)
    x = x - np.mean(x, axis=1, keepdims=True)

    # 3) AGC-like depth gain (lightweight and deterministic)
    n = x.shape[0]
    gain = np.linspace(1.0, 2.2, n, dtype=float)[:, None]
    x = x * gain

    # 4) Normalize by max abs to improve comparability across runs
    max_abs = float(np.max(np.abs(x)))
    if max_abs > 1e-12:
        x = x / max_abs
    return x


def _git_commit() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, text=True).strip()
        return out
    except Exception:
        return "unknown"


def run(manifest_path: Path, output_json: Path, output_md: Path, compare_with: Path | None) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    samples = manifest["samples"]

    rows = []
    total_start = time.perf_counter()

    for item in samples:
        sample_path = REPO_ROOT / item["path"]
        raw = _load_csv(sample_path)

        non_finite_count = int(np.size(raw) - int(np.isfinite(raw).sum()))
        t0 = time.perf_counter()
        out = _light_pipeline(raw)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        row = {
            "id": item["id"],
            "path": item["path"],
            "source": item.get("source", ""),
            "purpose": item.get("purpose", ""),
            "input_shape": list(raw.shape),
            "output_shape": list(out.shape),
            "non_finite_input_count": non_finite_count,
            "elapsed_ms": round(elapsed_ms, 3),
            "input_stats": _safe_stats(np.nan_to_num(raw, nan=0.0, posinf=0.0, neginf=0.0)),
            "output_stats": _safe_stats(out),
        }
        rows.append(row)

    total_elapsed_ms = (time.perf_counter() - total_start) * 1000.0

    payload = {
        "version": "regression-baseline-v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "repo_commit": _git_commit(),
        "manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "sample_count": len(rows),
        "total_elapsed_ms": round(total_elapsed_ms, 3),
        "samples": rows,
    }

    deltas = {}
    if compare_with and compare_with.exists():
        prev = json.loads(compare_with.read_text(encoding="utf-8"))
        prev_map = {s["id"]: s for s in prev.get("samples", [])}
        for s in rows:
            p = prev_map.get(s["id"])
            if not p:
                continue
            deltas[s["id"]] = {
                "elapsed_ms_delta": round(s["elapsed_ms"] - p.get("elapsed_ms", 0.0), 3),
                "output_mean_delta": round(s["output_stats"]["mean"] - p.get("output_stats", {}).get("mean", 0.0), 6),
                "output_std_delta": round(s["output_stats"]["std"] - p.get("output_stats", {}).get("std", 0.0), 6),
            }
        payload["compare_with"] = str(compare_with.relative_to(REPO_ROOT))
        payload["deltas"] = deltas

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    output_md.parent.mkdir(parents=True, exist_ok=True)
    md_lines = [
        "# Regression Baseline v1",
        "",
        f"- Generated: {payload['generated_at']}",
        f"- Commit: {payload['repo_commit']}",
        f"- Manifest: `{payload['manifest']}`",
        f"- Samples: {payload['sample_count']}",
        f"- Total elapsed: {payload['total_elapsed_ms']} ms",
        "",
        "## Sample Metrics",
        "",
        "| Sample | Input Shape | Output Shape | Non-finite In | Elapsed (ms) | Out mean | Out std | Out p01 | Out p99 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in rows:
        st = s["output_stats"]
        md_lines.append(
            f"| {s['id']} | {s['input_shape'][0]}x{s['input_shape'][1]} | {s['output_shape'][0]}x{s['output_shape'][1]} | {s['non_finite_input_count']} | {s['elapsed_ms']:.3f} | {st['mean']:.6f} | {st['std']:.6f} | {st['p01']:.6f} | {st['p99']:.6f} |"
        )

    if deltas:
        md_lines += ["", "## Deltas vs previous baseline", "", "| Sample | ΔElapsed(ms) | ΔMean | ΔStd |", "|---|---:|---:|---:|"]
        for sid, d in deltas.items():
            md_lines.append(f"| {sid} | {d['elapsed_ms_delta']:.3f} | {d['output_mean_delta']:.6f} | {d['output_std_delta']:.6f} |")

    output_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Run GPR regression baseline on sample manifest")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Path to sample manifest JSON")
    parser.add_argument("--output-json", default=str(DEFAULT_JSON), help="Path to output JSON")
    parser.add_argument("--output-md", default=str(DEFAULT_MD), help="Path to output Markdown")
    parser.add_argument("--compare-with", default=None, help="Optional previous baseline JSON for delta")
    args = parser.parse_args()

    manifest = Path(args.manifest).resolve()
    out_json = Path(args.output_json).resolve()
    out_md = Path(args.output_md).resolve()
    compare_with = Path(args.compare_with).resolve() if args.compare_with else None

    payload = run(manifest, out_json, out_md, compare_with)
    print(f"Baseline done: {payload['sample_count']} samples, {payload['total_elapsed_ms']:.3f} ms total")
    for s in payload["samples"]:
        print(
            f"- {s['id']}: elapsed={s['elapsed_ms']:.3f}ms, shape={tuple(s['output_shape'])}, "
            f"out_mean={s['output_stats']['mean']:.6f}, out_std={s['output_stats']['std']:.6f}"
        )


if __name__ == "__main__":
    main()
