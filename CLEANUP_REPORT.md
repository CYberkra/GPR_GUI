# CLEANUP_REPORT

## 1) 清理前后 `git status` 摘要

### 清理前（`git status --porcelain`）
- 已跟踪删除（疑似功能/数据变更，未触碰）：
  - `sample_data/A8-NEW-1.csv`
  - `sample_data/sample_bscan.csv`
  - `sample_data/two.csv`
- 未跟踪项（10 项）：
  - `.venv/`
  - `.venv_winbuild/`
  - `GPR_GUI_Qt.spec`
  - `__pycache__/`
  - `batch_process_demo.py`
  - `build/`
  - `compare_bg_agc.py`
  - `output/`
  - `sample_data/测线main_40dbm_普通飞高.csv`

### 清理后（`git status --porcelain`）
- 已跟踪删除（保留原状）：
  - `sample_data/A8-NEW-1.csv`
  - `sample_data/sample_bscan.csv`
  - `sample_data/two.csv`
- 未跟踪项（4 项）：
  - `.gitignore`
  - `GPR_GUI_Qt.spec`
  - `batch_process_demo.py`
  - `compare_bg_agc.py`

> 结果：未跟踪噪音项显著减少，后续增量提交污染风险下降。

## 2) 已隔离路径列表

隔离根目录：`.local_quarantine/20260310_1525/`

已移动（可回滚）：
- `.venv/`
- `.venv_winbuild/`
- `__pycache__/`
- `build/`
- `output/`
- `sample_data/测线main_40dbm_普通飞高.csv`

## 3) 新增/更新 `.gitignore` 规则

新增文件：`.gitignore`

规则包含：
- Python 缓存：`__pycache__/`, `*.py[cod]`
- 本地虚拟环境：`.venv/`, `.venv_winbuild/`
- 本地构建/输出产物：`build/`, `dist/`, `output/`
- 本地隔离归档：`.local_quarantine/`
- 日志：`*.log`, `logs/`

## 4) 保留未处理项与原因

- `GPR_GUI_Qt.spec`：可能属于打包配置源码，不归类为本地缓存噪音，保留。
- `batch_process_demo.py`：脚本源码，可能是功能/演示代码，保留。
- `compare_bg_agc.py`：脚本源码，可能是分析/算法相关，保留。
- `sample_data/*.csv`（3 个已跟踪删除项）：属于已跟踪内容变更，不做回滚/重置，避免破坏用户当前工作状态。
