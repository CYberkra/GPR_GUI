# GUI Iteration Step 7（继续优化）

## 变更
1. 在 `plot_data` 中继续拆分 compare 分支渲染逻辑，新增私有函数：
   - `GPRGuiQt._render_data_pairs(...)`
2. `plot_data` 现在只负责主流程编排（准备数据、建轴、统一渲染、色标），降低主函数复杂度。
3. compare 模式渲染（标题装配 + 坐标标签 + 网格）迁移到 `_render_data_pairs`，语义保持一致。
4. 增强可观测性（默认关闭，走统一 debug 开关 `GPR_GUI_PLOT_DEBUG`）：
   - 新增 `prepare view` 耗时指标（预处理+裁剪+显示下采样）
   - 新增 `compare render` 耗时指标（仅在双视图 compare 模式下记录）
5. 新增回归测试 `tests/test_render_data_pairs.py`：
   - 覆盖双 panel 场景：验证标题装配、标签设置、返回最后图像对象、compare 指标日志
   - 覆盖单 panel 场景：验证不产生 compare 指标日志
6. 新增回归测试 `tests/test_prepare_view_metrics.py`：
   - 覆盖 `_prepare_view_data` 输出 shape/bounds 及 debug 指标日志格式

## 验证
已执行：
- `python3 -m py_compile app_qt.py` ✅
- 测试脚本：
  - `python3 tests/test_build_compare_data_pairs.py` ✅
  - `python3 tests/test_draw_image_with_colormap.py` ✅
  - `python3 tests/test_plot_extent_labels.py` ✅
  - `python3 tests/test_plot_signature_matrix.py` ✅
  - `python3 tests/test_render_data_pairs.py` ✅
  - `python3 tests/test_prepare_view_metrics.py` ✅

offscreen smoke test：
- `QT_QPA_PLATFORM=offscreen python3 - <<'PY' ...` ❌
- 失败原因：当前环境缺少 `PySide6`（`ModuleNotFoundError: No module named 'PySide6'`）

## 收益
- `plot_data` 进一步聚焦“编排”，compare 分支细节下沉，后续维护与继续拆分风险更小。
- 预处理与 compare 渲染耗时具备可观测性，且默认关闭，不引入运行噪声。
- 新增回归测试直接绑定本轮重构点，降低后续重构回归风险。

## 风险
- 新增指标依赖 `display_data.shape`，若未来允许空数组或非常规对象，需要保持 shape 可用性。
- offscreen smoke 在当前环境未通过（缺 PySide6），需在 GUI 依赖完整环境复验。

## 回滚点
- 回滚提交中的以下改动即可恢复：
  - `app_qt.py` 中 `_render_data_pairs` 及 `_prepare_view_data` 指标日志
  - 两个新增测试文件

## 下轮建议
1. 继续拆分 `plot_data` 内颜色条/布局策略为可测 helper（如 compare 与非 compare 的 layout policy）。
2. 对 debug 指标增加“采样率”或“阈值告警”机制，避免高频重绘时日志过量（虽默认关闭，但开启后可控）。
3. 在 CI 或本地 devcontainer 补齐 PySide6，以固定化 offscreen smoke 验证链路。
