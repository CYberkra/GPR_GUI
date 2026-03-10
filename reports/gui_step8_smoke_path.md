# Step8: GUI关键路径 Smoke Test（offscreen）

## 目标覆盖
最小关键链路（非交互、离屏）：
1. 启动 GUI（`QApplication` + `GPRGuiQt`）
2. 加载样本 CSV（复用 GUI `load_csv` 路径）
3. 执行一次核心处理（默认 `dewow`）
4. 触发并确认绘图刷新（重绘或去重跳过均视为刷新成功）
5. 关闭窗口并退出

---

## 命令
在仓库根目录执行：

```bash
QT_QPA_PLATFORM=offscreen python3 scripts/smoke_offscreen.py
```

可选参数：

```bash
QT_QPA_PLATFORM=offscreen python3 scripts/smoke_offscreen.py \
  --sample sample_data/regression_v1/sample_layered_small.csv \
  --method-key dewow \
  --timeout-sec 30 \
  --json-out reports/gui_step8_smoke_result.json
```

---

## 预期结果
- 终端出现：`RESULT: PASS`
- 生成结构化结果文件：`reports/gui_step8_smoke_result.json`
- JSON 中关键字段：
  - `pass: true`
  - `checkpoints.startup/load_sample/core_process_once/plot_refresh/shutdown` 全为 `true`

示例（摘要）：

```json
{
  "pass": true,
  "checkpoints": {
    "startup": true,
    "load_sample": true,
    "core_process_once": true,
    "plot_refresh": true,
    "shutdown": true
  }
}
```

---

## 常见失败与修复

### 1) `Neither PyQt6 nor PySide6 is importable`
**原因**：Qt 依赖未安装。  
**修复**：
```bash
python3 -m pip install -r requirements-dev.txt
```

### 2) `app_qt.py requires PyQt6`
**原因**：当前 GUI 代码基于 PyQt6 导入。  
**修复**：安装/切换 PyQt6 环境。

### 3) `Sample CSV not found`
**原因**：样本路径不存在。  
**修复**：
- 使用默认样本：`sample_data/regression_v1/sample_layered_small.csv`
- 或传入有效 `--sample` 路径。

### 4) `processing timeout`
**原因**：核心处理线程超时（机器慢、负载高或方法异常）。  
**修复**：
- 增大 `--timeout-sec`（如 60）
- 先单独验证方法是否可运行

### 5) `plot refresh timeout`
**原因**：刷新后签名一致时会走去重分支，不一定触发重绘计数。  
**修复**：脚本已兼容“重绘增量”或“去重跳过增量”任一成功判定；若仍失败，检查事件循环与 Qt 后端。

### 6) CJK 字体缺失 warning（`Glyph ... missing from font(s) DejaVu Sans`）
**说明**：常见于无中文字体环境，通常不影响 smoke 通过。  
**修复（可选）**：安装中文字体（如 Noto Sans CJK）。

---

## 本次验证记录（至少1次成功）
- 执行时间：2026-03-11（Asia/Shanghai）
- 命令：`QT_QPA_PLATFORM=offscreen python3 scripts/smoke_offscreen.py`
- 结果：**PASS**
- 输出摘要：
  - `data_shape`: `[256, 80]`
  - `process_status`: `worker completed`
  - `plot_status`: `refresh dedup skip_count 0 -> 1`
  - 结果文件：`reports/gui_step8_smoke_result.json`
