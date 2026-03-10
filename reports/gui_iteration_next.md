# GPR GUI 下一轮迭代（有限重构）报告

## 1) 变更清单（最小必要）
- 修改文件：`app_qt.py`
- 新增报告：`reports/gui_iteration_next.md`
- 本轮未做目录迁移、未引入新依赖、未触碰核心算法实现语义。

## 2) 有限重构点（GUI层）

### 2.1 提取公共数据准备路径（渲染触发路径）
- 改动：新增 `_prepare_view_data(data)`，统一处理 `nan_to_num -> preprocess -> crop -> display downsample`。
- 使用位置：
  - `plot_data()` 主视图渲染
  - 双视图对比 snapshot 渲染
- 价值：去除重复逻辑，降低 `plot_data` 分支复杂度，保证主视图与对比视图处理一致。

### 2.2 提取公共参数解析函数（参数校验路径）
- 改动：新增 `_parse_int_edit(edit, default)`，统一解析输入框中的整数（支持空值与浮点文本兜底）。
- 使用位置：
  - `_downsample_data`
  - `_downsample_for_display`
  - `load_csv` 快速预览目标行数估算
- 价值：减少重复 `try/except` 代码，输入异常时行为一致、可预期。

### 2.3 渲染触发去重与状态版本管理（事件/渲染路径）
- 改动：新增 `_data_revision`、`_last_plot_signature`、`_mark_data_changed()`、`_build_plot_signature()`。
- 行为：`_do_refresh_plot()` 在签名未变化时跳过重复绘制。
- 版本递增触发点：`load_csv`、`undo_last`、`reset_original`、worker 完成写回 `final_data`。
- 价值：减少 UI 控件频繁触发下的无效重绘。

### 2.4 对比快照更新时阻断组合框信号（事件处理路径）
- 改动：`_set_compare_snapshots()` 中对左右 `QComboBox` 使用 `QSignalBlocker`。
- 并在 `_refresh_plot()` 增加 `_compare_syncing` 保护。
- 价值：避免 clear/add/setCurrentIndex 过程中触发多次冗余 `_refresh_plot`。

## 3) 性能与稳定性增强（至少2项）

### 增强 #1：重复绘制抑制（性能）
- 改前问题：
  - UI 多控件状态变化（尤其 compare 组合框更新）会触发短时间内多次 `_refresh_plot`，即使图像状态未变化也会重复进入绘制。
- 改后行为：
  - 通过 `plot signature` 对渲染输入状态做比较；状态未变化时跳过绘制。
- 预期收益：
  - 降低 CPU 消耗与 matplotlib 重绘开销，提升交互顺滑度。

### 增强 #2：批量更新 compare 下拉框时信号阻断（性能+稳定性）
- 改前问题：
  - 更新 compare snapshot 时 `clear/addItem/setCurrentIndex` 会触发多次 `currentIndexChanged`，导致冗余刷新，状态时序复杂。
- 改后行为：
  - 在更新周期内阻断信号 + `_compare_syncing` 保护，更新完成后恢复正常触发。
- 预期收益：
  - 降少抖动式重绘，降低状态竞争引发的偶发显示不一致风险。

### 增强 #3：整数输入解析统一兜底（稳定性）
- 改前问题：
  - 多处重复解析逻辑，空字符串/异常输入处理分散，行为可能不一致。
- 改后行为：
  - 统一走 `_parse_int_edit`，异常时回落 default，不中断主流程。
- 预期收益：
  - 提升参数输入容错，减少边界输入导致的流程中断。

## 4) 验证

### 4.1 静态/语法检查
- 命令：
  - `python3 -m py_compile app_qt.py`
- 结果：通过（无报错）。

### 4.2 最小运行验证（关键入口）
- 命令：
  - `QT_QPA_PLATFORM=offscreen python3 - <<'PY' ...`（创建 `QApplication` + `GPRGuiQt`，注入随机矩阵并执行 `plot_data`）
- 结果摘要：
  - 输出 `GUI_SMOKE_OK (128, 64)`，关键入口可初始化，核心 GUI 渲染流程不报错。
  - 观察到既有 matplotlib warning：`grid(false, line properties supplied)`，本轮未改语义，仅记录。

## 5) 提交前最小检查（rule #20）
- `git status --short`：仓库存在历史脏状态（与本轮无关），包括 sample_data 删除与若干未跟踪文件。
- 关键功能自检：已完成语法检查 + GUI 最小启动/渲染 smoke test。
- 本轮变更文件清单：
  - `app_qt.py`
  - `reports/gui_iteration_next.md`
- 环境噪音控制：提交时仅暂存上述 2 个文件，不纳入无关删除/未跟踪文件。

## 6) 风险、回滚点、产物路径
- 风险：
  - 渲染签名包含多项 UI 状态；若未来新增影响渲染的控件但未纳入签名，可能出现“应重绘但被跳过”。
- 回滚点：
  - 可单文件回滚：`git checkout <commit>^ -- app_qt.py`
  - 或整提交回滚：`git revert <commit_hash>`
- 产物路径：
  - 报告：`reports/gui_iteration_next.md`
  - 代码：`app_qt.py`
