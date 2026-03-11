# GUI Optimization Notes (2026-03-12)

## Scope
Small, low-risk improvements focused on GUI stability, UX consistency, and error-handling robustness in `app_qt.py`.
No architecture refactor.

## Changes

### 1) Core worker temp file isolation + cleanup
- **Change**: Replaced fixed temp paths (`__tmp_in.csv`, `__tmp_*_out.csv/png`) with per-task unique `tempfile.NamedTemporaryFile(...)` paths, and added `finally` cleanup.
- **Reason**:
  - Fixed-name temp files can collide across runs / stale artifacts.
  - Leftover tmp files can accumulate and create confusion or storage noise.
- **Expected benefit**:
  - Better run stability and less chance of file conflict.
  - Cleaner output directory and fewer "mysterious tmp" artifacts.

### 2) CSV import robustness for NaN/Inf
- **Change**: Replaced NaN-only handling with `np.isfinite` check; now fills NaN/Inf using finite mean if available, otherwise `0.0`, with a clear log message.
- **Reason**:
  - Previous `np.nanmean(data)` path can degrade when all values are invalid.
  - `Inf` values were not normalized.
- **Expected benefit**:
  - More robust import path for imperfect field data.
  - Fewer downstream plot/process failures caused by non-finite values.

### 3) Apply-method history timing fix (UX)
- **Change**: Moved `_push_history()` to execute **after** parameter validation succeeds.
- **Reason**:
  - Previously invalid parameters still pushed history, creating useless undo entries.
- **Expected benefit**:
  - Undo stack now reflects only effective operations.
  - Better user trust in undo/reset behavior.

## Risk Assessment
- No high-risk changes introduced.
- Processing algorithm behavior unchanged.
- Changes are local to temp file management, data sanitization, and command flow order.

## Quick Validation
1. **Syntax check**: `python3 -m py_compile app_qt.py` ✅
2. **Unit tests**: `pytest -q` -> 29 passed, 1 failed.
   - Existing failure appears unrelated to this patch:
   - `tests/test_save_image_cmap_compat.py::test_save_image_accepts_cmap_kwarg_and_saves_file`

## Notes
- Left pre-existing unrelated working tree entries untouched:
  - `sample_data/LineX1origin(30).csv`
  - `sample_data/results/`
