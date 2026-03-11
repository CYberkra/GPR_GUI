# Hotfix Report: `Cross index must be 1 dimensional` on CSV import

## 背景
- 问题文件：`main_40dbm_普通飞高.csv`
- 报错：`ValueError: Cross index must be 1 dimensional`
- 影响路径：CSV 导入后快速预览/显示降采样链路（`load_csv -> _downsample_data/_downsample_for_display -> plot_data`）

## 根因
1. `_downsample_axis_linear()` 在“不需要降采样”时返回 `slice(None)`。
2. 当另一维需要降采样时会得到数组索引（`ndarray[int]`）。
3. 若把 `slice` 与 `np.ix_` 混用（如 `np.ix_(slice(None), idx)`），NumPy 会抛出 `Cross index must be 1 dimensional`。
4. 该模式在大样本 CSV（单维需降采样、另一维不降采样）时更容易触发。

## 修复点
1. 在 `app_qt.py` 新增统一安全索引器：`GPRGuiQt._select_2d(data, row_idx, col_idx)`。
2. 规则：
   - 任一维是 `slice` → 直接 `data[row_idx, col_idx]`；
   - 两维都为数组索引 → 归一化为 1D 后再 `data[np.ix_(...)]`。
3. 将 `_downsample_data()` 与 `_downsample_for_display()` 都改为复用 `_select_2d()`，消除重复逻辑并统一行为。

## 回归测试
### 新增测试
- `tests/test_downsample_slice_ix_regression.py`
  - `test_select_2d_mixed_slice_and_array_indices`
  - `test_downsample_data_handles_slice_plus_array_without_cross_index_error`

### 已执行验证命令
```bash
python3 tests/test_downsample_slice_ix_regression.py
python3 tests/test_plot_signature_matrix.py
python3 tests/test_plot_extent_labels.py
python3 scripts/smoke_offscreen.py
pytest -q tests
```

### 结果
- `pytest -q tests`：`27 passed`
- `scripts/smoke_offscreen.py`：`PASS`
- CSV 导入关键链路（load -> preview/downsample -> plot）在离屏 smoke 中通过。

## 风险评估
- 低风险：
  - 仅影响 2D 索引选择路径；
  - 不改变降采样索引生成策略（仍由 `_downsample_axis_linear` 决定）。
- 已通过矩阵回归与 smoke 覆盖主要导入/绘图链路。

## 回滚点
- 主要回滚文件：`app_qt.py`
- 回滚策略：
  1. 回退当前 hotfix commit；或
  2. 手工恢复 `_downsample_data/_downsample_for_display` 为先前实现（不建议）。

## Windows 打包（可选）
- 当前会话为 Linux/WSL，未执行 Windows EXE 重打。
- 最短打包步骤（Windows PowerShell）：
```powershell
cd <repo>\GPR_GUI
python -m venv .venv_build
.\.venv_build\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install pyinstaller PyQt6 numpy pandas matplotlib scipy
powershell -ExecutionPolicy Bypass -File tools\build_windows_exe.ps1
```
- 建议产物命名加 shortsha，例如：`GPR_GUI_Qt_hotfix_<shortsha>.exe`，并在 release note 标记本次 cross-index hotfix。
