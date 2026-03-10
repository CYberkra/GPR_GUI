# Week1 Day5 - Windows 打包链 v1 固化（可重复构建）

更新时间：2026-03-11
仓库：`repos/GPR_GUI`

## 1) 固化后的构建入口

- 主脚本：`tools/build_windows_exe.ps1`
- 包装脚本：`tools/build_windows_exe_wslbridge.ps1`（透传参数到主脚本，便于统一入口）

### 推荐命令（Windows PowerShell）

```powershell
cd E:\Openclaw\.openclaw\workspace\repos\GPR_GUI
powershell -ExecutionPolicy Bypass -File .\tools\build_windows_exe.ps1
```

可选参数：

```powershell
# 指定路径
powershell -File .\tools\build_windows_exe.ps1 `
  -RepoRoot "E:\Openclaw\.openclaw\workspace\repos\GPR_GUI" `
  -CorePath "E:\Openclaw\.openclaw\workspace\repos\PythonModule_core"

# 跳过依赖安装 / 跳过构建（仅重命名+验证）
powershell -File .\tools\build_windows_exe.ps1 -SkipDependencyInstall
powershell -File .\tools\build_windows_exe.ps1 -SkipBuild
```

## 2) 产物命名标准

脚本中已固化为：

- `GPR_GUI_Qt_win_YYYYMMDD_<shortsha>.exe`

例如（当前提交）：

- `GPR_GUI_Qt_win_20260311_bd5a301.exe`

并同步写入：

- `dist/RELEASE_VERSION.txt`（值：`win_YYYYMMDD_<shortsha>`）

## 3) PE 验证步骤（已脚本化）

构建后自动执行双重校验：

1. **PE 魔数字节校验（强制）**
   - 校验 `MZ` + `PE\0\0` 头（PowerShell 内置实现）
2. **外部工具校验（可选，自动探测）**
   - 优先 `7z l`（匹配 `Type = PE`）
   - 其次 `objdump -f`（匹配 `pei-*` / `file format pe`）
   - 再次 `file`（匹配 `PE32/PE32+`）

验证结果落盘到：

- `dist/GPR_GUI_Qt_win_YYYYMMDD_<shortsha>_pe_verify.txt`

若校验失败，脚本会 `throw` 并退出非 0。

## 4) 依赖清单

脚本默认在 `.venv_winbuild` 中安装：

- `pyinstaller`
- `PyQt6`
- `numpy`
- `pandas`
- `matplotlib`
- `scipy`

并使用 `Python 3.10`（`py -3.10 -m venv`）。

## 5) 本次真实验证与环境限制

### 环境限制

当前执行环境为 Linux/WSL，**未安装 `pwsh/powershell`**，因此无法在本会话直接运行 `.ps1` 完整 Windows 构建流程。

### 已完成的真实验证（基于现有产物）

执行：

```bash
file dist/GPR_GUI_Qt.exe
objdump -f dist/GPR_GUI_Qt.exe | head -n 5
```

结果：

- `dist/GPR_GUI_Qt.exe` 被识别为 `PE32+ executable (GUI) x86-64, for MS Windows`
- `objdump` 识别为 `file format pei-x86-64`

补充发现：

- `dist/GPR_GUI_Qt_exp_20260310_ecdbd5a.exe` 被识别为 **ELF**，不是 PE，说明历史命名中存在“`.exe` 后缀但非 Windows 可执行文件”的混淆风险。
- v1 命名标准与 PE 校验可规避该类问题。

## 6) 失败排查（Troubleshooting）

1. **`Build output not found: dist/GPR_GUI_Qt.exe`**
   - 检查 PyInstaller 是否成功完成
   - 检查 `app_qt.py`、`assets`、`read_file_data.py` 路径

2. **`CorePath not found`**
   - 显式传入 `-CorePath`，确保指向 `PythonModule_core`

3. **PE 验证失败**
   - 打开 `*_pe_verify.txt` 查看工具输出
   - 检查是否误把 Linux/WSL 产物重命名为 `.exe`

4. **Windows 缺少 Python Launcher (`py`)**
   - 安装 Python 3.10 并确保 `py -3.10` 可用
   - 或修改脚本为固定解释器路径

5. **PyInstaller 缺模块 / Qt 插件异常**
   - 保持在 `.venv_winbuild` 内全新安装依赖后重试
   - 如仍异常，补充 hidden-import 或转向 one-dir + windeployqt

## 7) 在 Windows 主机补齐一次完整验证（可执行）

```powershell
cd E:\Openclaw\.openclaw\workspace\repos\GPR_GUI
powershell -ExecutionPolicy Bypass -File .\tools\build_windows_exe.ps1

# 构建完成后查看：
# 1) ARTIFACT=...
# 2) VERIFY_LOG=...
# 3) dist\GPR_GUI_Qt_win_YYYYMMDD_<shortsha>.exe
# 4) dist\GPR_GUI_Qt_win_YYYYMMDD_<shortsha>_pe_verify.txt
```
