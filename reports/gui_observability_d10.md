# Week2 Day10：GUI 可观测性面板化（轻量）

## 改动点
1. 在右侧绘图区域新增 `📈 可观测性` 轻量面板（`QGroupBox`）。
2. 面板提供显示开关（`checkable`），默认关闭（低干扰，不喧宾夺主）。
3. 面板内新增 4 个关键指标展示：
   - 最近绘制耗时
   - 累计绘制次数
   - 累计跳过重绘次数
   - 最近预处理耗时
4. 在已有性能埋点路径上做非侵入绑定：
   - `_do_refresh_plot` 的跳过分支更新跳过计数并刷新面板。
   - `_prepare_view_data` 记录最近预处理耗时并刷新面板。
   - `plot_data` 记录最近绘制耗时、绘制次数并刷新面板。
5. 补充 `_format_metric_ms`（静态方法）统一格式化毫秒显示，空值显示 `--`。
6. 新增 `_last_prepare_ms` 与 `_last_compare_ms` 指标字段（不改变算法语义，仅用于观测）。
7. 为兼容现有 lightweight dummy tests，在调用面板刷新处添加 `hasattr` 保护，避免无 UI dummy 报错。

## 文本示例（代替截图）
面板展开后示例：

- 最近绘制耗时：12.35 ms
- 累计绘制次数：7
- 累计跳过重绘：3
- 最近预处理耗时：4.57 ms

默认启动时面板收起，仅显示标题栏 `📈 可观测性`。

## 验证

### 新增测试
- `tests/test_observability_panel.py`
  1. `test_observability_metrics_binding_updates_labels`
     - 验证指标值与 Label 文本绑定正确。
  2. `test_observability_toggle_does_not_change_refresh_flow`
     - 验证开关切换不影响主流程重绘判定（签名不变时仍走 skip 分支）。

### 回归验证（受影响路径）
执行：

```bash
pytest -q tests/test_observability_panel.py \
         tests/test_plot_signature_matrix.py \
         tests/test_prepare_view_metrics.py \
         tests/test_render_data_pairs.py
```

结果：`6 passed`。

## 风险评估
- 低风险：
  - 仅新增展示层 UI + 指标字段记录；不改算法流程、不改处理结果。
  - 指标刷新为常量级字符串更新，性能影响可忽略。
- 注意点：
  - 若后续希望展示 compare 耗时，目前已有 `_last_compare_ms` 记录，但未在面板显示（本轮按最小目标保留）。

## 回滚点
如需快速回滚本轮改动，可回滚以下文件：
- `app_qt.py`
- `tests/test_observability_panel.py`
- `reports/gui_observability_d10.md`

按 commit 回滚即可完全撤销本轮功能。
