# GPR_GUI Step 6 报告（可维护性 + 可观测性）

## 变更点

1. **抽离坐标决策逻辑**：新增 `GPRGuiQt._resolve_plot_extent_and_labels(valid_data, bounds)`，统一返回：
   - `extent`
   - `xlabel`
   - `ylabel`
2. **保持兼容**：`_resolve_plot_extent` 仍保留，改为调用新函数，避免潜在调用点被破坏。
3. **简化绘制主流程**：`plot_data` 改为使用 `plot_config = _resolve_plot_extent_and_labels(...)`，减少散落判断。
4. **轴标签应用收敛**：`_apply_axis_labels` 改为接收 `labels` 配置，避免读取全局状态的重复 if/else。
5. **渲染签名回归矩阵补齐**：新增 `tests/test_plot_signature_matrix.py`，覆盖“应重绘/应跳过重绘”的关键开关组合（首次渲染、签名不变、UI 变更、数据版本变更、无数据）。
6. **坐标/标签回归测试补齐**：新增 `tests/test_plot_extent_labels.py`，覆盖“有头信息+裁剪范围”与“无头信息+无裁剪”的最小分支。
7. **轻量性能埋点（默认关闭）**：新增埋点字段：
   - `self._plot_skip_count`
   - `self._plot_draw_count`
   - `self._last_plot_ms`
8. **debug 开关**：新增 `self._plot_debug_metrics`，由环境变量 `GPR_GUI_PLOT_DEBUG` 控制（`1/true/yes/on` 开启）。默认不输出，不改变默认行为。
9. **埋点输出内容**：
   - 跳过重绘时：累计跳过次数
   - 每次绘制后：单次耗时(ms) + 当前跳过计数

## 验证结果

### 1) 语法编译
- 命令：`python3 -m py_compile app_qt.py`
- 结果：✅ 通过

### 2) 相关测试脚本
- 命令：
  - `python3 tests/test_build_compare_data_pairs.py`
  - `python3 tests/test_draw_image_with_colormap.py`
  - `python3 tests/test_plot_signature_matrix.py`
  - `python3 tests/test_plot_extent_labels.py`
- 结果：✅ 全部通过

### 3) offscreen smoke test
- 命令：`QT_QPA_PLATFORM=offscreen python3 - <<'PY' ... PY`
- 内容：实例化 `QApplication + GPRGuiQt`，构造随机矩阵并调用 `plot_data`
- 结果：✅ 输出 `OK: offscreen smoke`

## 埋点样例

在开启调试开关后（例如 `GPR_GUI_PLOT_DEBUG=1`），日志中会出现类似：

- `[plot-debug] skip redraw: count=3`
- `[plot-debug] draw#5: 27.31 ms, skipped=3`

> 说明：默认关闭，不会污染现有日志；仅在需要定位渲染性能/冗余重绘时启用。

## 风险评估

- **低风险（结构重排）**：extent 与标签决策逻辑收敛后，行为等价性主要由新增分支测试覆盖。
- **可控风险（签名策略）**：本轮未改变签名字段集合，仅补测试与埋点，不引入新的重绘触发条件。
- **运行风险（日志）**：debug 日志默认关闭，生产路径无额外噪声。

## 回滚点

按提交粒度可独立回滚：
1. `refactor/gui`: 仅重构 extent/labels 决策与调用方式
2. `test/gui`: 仅测试矩阵与 helper 测试
3. `perf/gui`: 仅性能埋点与 debug 输出

## 下轮建议

1. 将 `_build_plot_ui_signature` 结构化（命名字段）并补“字段变化->重绘”参数化测试，提升可读性。
2. 将 `_plot_debug_metrics` 暴露为 UI 侧开发选项（仅开发模式可见），便于无需环境变量快速调试。
3. 增加“连续操作场景”统计（例如批量滑条变更）并计算 skip/draw 比例，辅助判断防抖阈值（当前 30ms）是否最优。
