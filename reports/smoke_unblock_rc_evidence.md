# Smoke Unblock RC Evidence

- GeneratedAt: 2026-03-11 10:05 (Asia/Shanghai)
- Command:
  - `python3 scripts/smoke_offscreen.py --json-out reports/gui_step8_smoke_result.json --timeout-sec 25 --hard-timeout-sec 60`
- Result: **PASS**

## PASS JSON Evidence (reports/gui_step8_smoke_result.json)

- `timestamp`: `2026-03-11T10:04:57+08:00`
- `pass`: `true`
- `reason`: `PASS`
- `checkpoints.startup`: `true`
- `checkpoints.load_sample`: `true`
- `checkpoints.core_process_once`: `true`
- `checkpoints.plot_refresh`: `true`
- `checkpoints.shutdown`: `true`
- `metrics.process_status`: `worker completed`
- `metrics.plot_status`: `refresh dedup skip_count 0 -> 1`
- `metrics.plot_draw_count`: `2`
- `metrics.elapsed_sec`: `1.9`

## Root Cause & Fix Summary

- Root cause 1 (stability risk): offscreen 场景下若触发 `QMessageBox.*`，会进入不可交互的模态对话框，导致 smoke 卡住。
- Root cause 2 (hidden exception): `_downsample_axis_linear` 在无需降采样时返回 `slice(None)`，后续 `np.ix_(slice, slice)` 会抛 `ValueError`，导致 worker 完成回调中断并降低稳定性。

Applied fixes:
- `scripts/smoke_offscreen.py`
  - 增加 `--hard-timeout-sec`（默认 60s）确保总时限可收敛。
  - offscreen 模式下对 `QMessageBox.information/warning/critical/question` 打桩为无阻塞返回，避免模态阻塞。
  - 增加 `timestamp` 与 `metrics.elapsed_sec`，提升结构化证据可追溯性。
- `app_qt.py`
  - 在 `_downsample_data` 与 `_downsample_for_display` 中处理 `slice` 索引，避免 `np.ix_` 对 slice 抛错。
