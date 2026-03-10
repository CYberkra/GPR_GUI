# GPR_GUI Iteration Step 2 报告

- 时间：2026-03-10
- 基线提交：`34e0d8f`
- 本轮范围：`app_qt.py`（非破坏性小步重构 + warning 清理）

## 1) 变更点

1. 将 `plot_data()` 内部颜色映射分支抽离为私有函数 `._draw_image_with_colormap()`。
2. 将色标绘制分支抽离为私有函数 `._draw_colorbar_if_needed()`。
3. 新增 `._apply_axis_grid()`，统一处理网格显示逻辑。
4. 修复 matplotlib 网格 warning：当网格关闭时不再传入 line props，仅调用 `ax.grid(False)`。
5. `plot_data()` 主流程改为“组织数据对 + 调用私有绘制函数 + 统一轴标签/网格”，复杂度下降。
6. 将渲染签名构建做最小结构化：新增 `._build_plot_ui_signature()`。
7. `._build_plot_signature()` 改为 `(_data_revision,) + _build_plot_ui_signature()`，保持行为一致同时提升可读性与可维护性。

## 2) 收益

- **可维护性提升**：`plot_data()` 由多层 if/else 视觉分支改为委托私有函数，后续扩展 colormap 策略更集中。
- **稳定性提升**：避免 `grid(False)` 场景下传入样式参数导致的 matplotlib warning 噪声。
- **签名逻辑更清晰**：UI 相关绘制签名聚合，便于后续新增绘制开关时定位修改点。
- **行为兼容**：未改动核心业务算法与 I/O，仅做 UI 渲染路径重构与告警清理。

## 3) 风险评估

- 低风险：
  - 绘制逻辑拆分后如后续新增模式未接入私有函数，可能出现 title/cbar 不一致。
  - compare 模式仍沿用“最后一次 im 句柄绘制 colorbar”的行为（与原实现一致）。

## 4) 回滚点

- 单文件回滚：`git checkout -- app_qt.py`
- 若需精确回退本轮：回退到本轮提交前一个 commit（见提交 hash）。

## 5) 验证命令与结果

### A. 语法校验
```bash
python3 -m py_compile app_qt.py
```
结果：**通过**（无输出）。

### B. Offscreen GUI smoke test
```bash
QT_QPA_PLATFORM=offscreen python3 - <<'PY'
import numpy as np
from PyQt6.QtWidgets import QApplication
from app_qt import GPRGuiQt
app = QApplication([])
w = GPRGuiQt()
x = np.linspace(0, 8*np.pi, 128)
y = np.linspace(0, 4*np.pi, 256)
xx, yy = np.meshgrid(x, y)
data = np.sin(xx)*np.exp(-yy/20) + 0.1*np.random.randn(*xx.shape)
w.data = data
w.original_data = data.copy()
w._set_compare_snapshots([{"label":"原始","data":data},{"label":"当前","data":data}])
w.plot_data(data)
w.close()
app.quit()
print('offscreen_smoke_ok')
PY
```
结果：**通过**，输出 `offscreen_smoke_ok`。

## 6) 变更文件

- `app_qt.py`
- `reports/gui_iteration_step2.md`
