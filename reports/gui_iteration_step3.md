# GUI Iteration Step 3 Report

## 基线
- 基线提交：`efa007d`
- 迭代方式：小步、非破坏性重构（不改变主架构）

## 变更点
1. 在 `app_qt.py` 新增 `_build_compare_data_pairs(display_data)`：
   - 将 compare 模式中“左右数据对构建”的逻辑从 `plot_data()` 抽离。
   - 保留原始行为：索引越界保护、单快照回退到 `[0, 0]`、按快照调用 `_prepare_view_data()`。
2. `plot_data()` 里改为调用 `_build_compare_data_pairs()`：
   - 根据 `data_pairs` 数量决定 2x1（compare）或 1x1（single）子图布局。
   - 渲染流程与标题/坐标轴/网格逻辑保持不变。
3. 新增轻量测试脚本：`tests/test_draw_image_with_colormap.py`：
   - 覆盖 `_draw_image_with_colormap()` 3 个关键分支：
     - chatgpt style clip 分支
     - symmetric 分支
     - percentile bounds 分支
   - 使用无 pytest 依赖的可运行脚本模式，`python3` 直接执行。

## 验证
- 语法检查：
  - `python3 -m py_compile app_qt.py` ✅
- 分支测试：
  - `python3 tests/test_draw_image_with_colormap.py` ✅
- Offscreen smoke：
  - `QT_QPA_PLATFORM=offscreen python3 - <<'PY' ...`（实例化 `GPRGuiQt` 并关闭）✅

## 风险评估
- 低风险：
  - compare 数据对构建逻辑只是搬移与复用，行为保持一致。
- 已知边界：
  - 新增测试偏“函数级/分支级”，未覆盖完整 GUI 事件链。
  - `_draw_image_with_colormap()` 的 default 分支未单独覆盖（可在下轮补一条）。

## 回滚点
- 回滚目标文件：
  - `app_qt.py`
  - `tests/test_draw_image_with_colormap.py`
- 回滚方式：
  - 直接回退当前提交即可恢复到 Step3 前状态。

## 下轮建议
1. 为 `_draw_image_with_colormap()` 补充 default fallback 分支测试（`_get_percentile_bounds -> None`）。
2. 在 compare 模式增加“同索引对比”与“空快照防御”测试，进一步锁定回归风险。
3. 若改动窗口允许，可将 extent/坐标标签计算抽为单独 helper（例如 `_resolve_plot_extent_and_labels()`），减少 `plot_data()` 复杂度。
