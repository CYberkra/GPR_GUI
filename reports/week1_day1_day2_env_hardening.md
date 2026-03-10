# Week1 Day1-Day2 环境固化报告（GPR_GUI）

## 目标
- 固化 GPR_GUI 开发/验证环境一致性
- 修复/规避“PySide6 缺失导致 smoke 失败”问题
- 提供可重复的一键环境检查与离屏 smoke 验证入口

## 本次交付文件
1. `requirements-dev.txt`
2. `scripts/env_check.py`
3. `scripts/smoke_offscreen.py`
4. `reports/week1_day1_day2_env_hardening.md`（本报告）

---

## 安装步骤（可复现）
在仓库根目录执行：

```bash
python3 -m pip install -r requirements-dev.txt
```

说明：
- 本机为 WSL 用户态安装（`~/.local/lib/python3.10/site-packages`）
- 若你使用虚拟环境，建议先 `python3 -m venv .venv && source .venv/bin/activate`

---

## 验证命令（标准入口）

```bash
python3 scripts/env_check.py
QT_QPA_PLATFORM=offscreen python3 scripts/smoke_offscreen.py
```

---

## 实际验证记录

### 1) 首轮 `env_check`
- 结果：**PASS with warnings**
- 现象：`pytest` 缺失（可选）
- 影响：不影响 GUI 运行，但影响测试工具完整性

### 2) 首轮 `smoke_offscreen`
- 结果：**FAIL**
- 原因：`ModuleNotFoundError: No module named 'app_qt'`
- 修复：在 `scripts/smoke_offscreen.py` 中显式将 repo root 加入 `sys.path`

### 3) 次轮 `smoke_offscreen`
- 结果：**FAIL**
- 原因：引用了不存在属性 `downsample_check`
- 修复：改为检查真实属性 `display_downsample_var`（并做 `hasattr` 保护）

### 4) 安装开发依赖后复验
执行：
```bash
python3 -m pip install -r requirements-dev.txt
python3 scripts/env_check.py
QT_QPA_PLATFORM=offscreen python3 scripts/smoke_offscreen.py
```

结果：
- `env_check.py`：**PASS**（numpy/pandas/scipy/matplotlib/PyQt6/qt-material/qdarkstyle/pytest 全部 OK）
- `smoke_offscreen.py`：**PASS**（QApplication 初始化、主窗口初始化、核心控件检查通过）

---

## 常见失败与可执行修复

### A. `No module named 'PyQt6'`
```bash
python3 -m pip install -r requirements-dev.txt
```

### B. `No module named 'app_qt'`（从 scripts/ 运行时）
- 已在 `scripts/smoke_offscreen.py` 内置 repo root 注入
- 若你自定义脚本，确保：
```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
```

### C. Qt 插件或显示错误（无图形环境）
- 必须使用 offscreen：
```bash
QT_QPA_PLATFORM=offscreen python3 scripts/smoke_offscreen.py
```
- 可附加：
```bash
MPLBACKEND=QtAgg QT_QPA_PLATFORM=offscreen python3 scripts/smoke_offscreen.py
```

### D. 历史 smoke 依赖 PySide6 但环境只有 PyQt6
- 当前项目 `app_qt.py` 使用 **PyQt6**，不是 PySide6
- 新 smoke 已做后端探测并提供清晰诊断；实际运行仍以 PyQt6 为准

---

## 当前环境结论
- 环境已固化到 `requirements-dev.txt`
- 已提供标准化检查入口 `scripts/env_check.py`
- 已提供离屏 smoke 入口 `scripts/smoke_offscreen.py`
- 在当前机器（WSL2, Python 3.10.12）可稳定通过：
  - `python3 scripts/env_check.py`
  - `QT_QPA_PLATFORM=offscreen python3 scripts/smoke_offscreen.py`
- “PySide6 缺失导致 smoke 失败”问题已通过“改为项目一致的 PyQt6 路线 + 后端诊断 + 离屏标准命令”完成闭环
