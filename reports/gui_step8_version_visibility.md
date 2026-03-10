# Step8：GUI 内显示版本标识（release+commit）

## 变更概述

本轮做了非破坏性小改动，目标是让 GUI 在可见位置展示版本标识，并保证启动阶段可读取版本来源。

### 1) 新增版本解析逻辑（`app_qt.py`）
- 新增 `_read_first_existing_text(paths)`：按顺序读取第一个存在的版本文件文本。
- 新增 `_get_git_short_sha(base_dir)`：通过 `git rev-parse --short HEAD` 获取短 commit。
- 新增 `build_version_string(app_name="GPR_GUI")`：拼接最终版本字符串。

### 2) 版本来源优先级
当前优先级如下：
1. `BASE_DIR/dist/RELEASE_VERSION.txt`
2. `../dist/RELEASE_VERSION.txt`
3. `BASE_DIR/RELEASE_VERSION.txt`
4. `BASE_DIR/VERSION`
5. 若都不存在：回退 `dev-YYYYMMDD + git short sha`

最终格式：
- 命中文件：`GPR_GUI <release> (<shortsha>)`
- 回退模式：`GPR_GUI dev-<YYYYMMDD> (<shortsha>)`

### 3) GUI 可见位置显示
- 窗口标题改为版本字符串（`self.setWindowTitle(self.version_text)`）。
- 右侧状态栏区域新增 `self.version_label`，持续显示版本字符串。
- Info 区域启动时追加日志：`Version: <version_text>`。

### 4) 启动输出版本字符串（便于自动化验证）
- `main()` 中新增：`print(f"[GPR_GUI] version={version_text}")`。
- 同时状态栏 message 展示 `Theme + version`。

## 最小验证

### A. 语法检查
命令：
```bash
python3 -m py_compile app_qt.py
```
结果：通过。

### B. 启动时读取并拼接版本字符串
命令：
```bash
python3 - <<'PY'
import app_qt
print(app_qt.build_version_string('GPR_GUI'))
PY
```
结果示例：
```text
GPR_GUI win_20260311_93a82fb (3d43668)
```
说明：已命中 `dist/RELEASE_VERSION.txt`，并成功拼接当前 git short sha。

### C. offscreen 启动一次并记录版本输出
命令：
```bash
timeout 5s env QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 python3 app_qt.py > /tmp/gpr_gui_offscreen_step8.log 2>&1
head -n 5 /tmp/gpr_gui_offscreen_step8.log
```
结果关键行：
```text
[GPR_GUI] version=GPR_GUI win_20260311_93a82fb (3d43668)
```
说明：offscreen 下可在启动日志中观察到版本字符串。`timeout` 结束为预期（GUI 事件循环常驻）。

## 风险评估

- 风险等级：低。
- 影响面：仅 `app_qt.py` 的 UI 展示与启动日志，不触及处理算法主流程。
- 兼容性：当 git 不可用时回退为 `nogit`，仍可启动。

## 回滚点

若需要回滚，仅还原本次对 `app_qt.py` 的改动（版本读取/显示/打印逻辑）即可；不涉及数据处理核心逻辑。