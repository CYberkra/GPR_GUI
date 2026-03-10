# Windows 体验包发布前清单（Preflight）

- 日期：2026-03-11 01:17 (Asia/Shanghai)
- 仓库：`/home/baiiy1/.openclaw/workspace/repos/GPR_GUI`
- 目标产物：`dist/GPR_GUI_Qt_win_20260311_93a82fb.exe`

## 1) 产物存在性 / 大小 / 时间戳

- 存在性：✅ 存在
- 文件大小：`102,815,917 bytes`（约 98.1 MiB）
- 修改时间：`2026-03-11 01:15:18 +08:00`

命令记录：

```bash
stat -c '%n|%s|%y' dist/GPR_GUI_Qt_win_20260311_93a82fb.exe
# dist/GPR_GUI_Qt_win_20260311_93a82fb.exe|102815917|2026-03-11 01:15:18.249423400 +0800
```

## 2) PE 验证日志存在性与关键字段

- 验证日志：`dist/GPR_GUI_Qt_win_20260311_93a82fb_pe_verify.txt`
- 存在性：✅ 存在
- 文件大小：`202 bytes`
- 修改时间：`2026-03-11 01:15:21 +08:00`

关键字段（原文）：

- `magic_check=True`
- `tool_method=none`
- `tool_check=False`
- `pe_verify_passed=True`

结论：✅ PE 基础校验通过（`pe_verify_passed=True`）。

## 3) 版本标识与 commit 对齐

- `dist/RELEASE_VERSION.txt`：`win_20260311_93a82fb`
- 当前仓库 HEAD（short）：`93a82fb`
- 对齐结果：✅ 对齐（release suffix 与 git short hash 一致）

补充：验证日志中的 artifact 路径也对应同名产物 `..._93a82fb.exe`。

## 4) 用户回机后最短验证步骤（Smoke Test）

> 目标：最短路径确认“能启动、能导入、能处理、能导出”。

1. 双击运行：`dist/GPR_GUI_Qt_win_20260311_93a82fb.exe`
2. 进入 GUI 后点击 **Import CSV**，选择一个可用 CSV（建议本机准备一份小样本）。
3. 选择任一处理方法（如 dewow / agcGain），保持默认参数后执行处理。
4. 确认界面有结果图像更新，并成功输出结果文件（CSV/PNG）。
5. 关闭并再次启动一次，确认二次启动正常。

通过标准：

- 无崩溃、无阻断报错；
- 至少一次处理成功；
- 至少一份输出文件生成成功。

---

## Preflight 总结

本次目标产物 `dist/GPR_GUI_Qt_win_20260311_93a82fb.exe` 在“文件存在、PE 校验、版本与 commit 对齐”三个发布前关键项均通过，达到可交付给用户做回机体验验证的状态。
