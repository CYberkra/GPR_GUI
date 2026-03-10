# GPR GUI Release Candidate (RC1) 收口报告

- 更新时间：2026-03-11 01:58 (Asia/Shanghai)
- 仓库：`/home/baiiy1/.openclaw/workspace/repos/GPR_GUI`
- RC 标识：`v0.2.0-rc1+a0bb7cf`
- 基线提交：`a0bb7cf`
- 决策结论：**NO-GO（剩余阻塞：smoke_offscreen 复验未通过）**

---

## 1) 重打包与产物对齐

已在当前 HEAD (`a0bb7cf`) 完成 Windows 重打包：

- `dist/GPR_GUI_Qt_win_20260311_a0bb7cf.exe`
- `dist/GPR_GUI_Qt_win_20260311_a0bb7cf_pe_verify.txt`

`dist/RELEASE_VERSION.txt` 已更新为：`win_20260311_a0bb7cf`。

---

## 2) Preflight 结果（新产物）

执行：

```bash
python3 tools/preflight_check.py --artifact dist/GPR_GUI_Qt_win_20260311_a0bb7cf.exe --json
```

关键字段：

- `artifact_exists=true`
- `verify_log_exists=true`
- `release_version_exists=true`
- `release_version=win_20260311_a0bb7cf`
- `git_short_head=a0bb7cf`
- `commit_aligned=true`
- `verify_fields.pe_verify_passed=True`

结论：**产物-提交已对齐，preflight 硬门槛通过。**

---

## 3) 关键入口复验（smoke_offscreen）

执行尝试：

```bash
QT_QPA_PLATFORM=offscreen python3 scripts/smoke_offscreen.py --json-out reports/gui_step8_smoke_result.json
```

本次执行在当前环境出现长时间阻塞（未在预期时间内完成并返回 PASS），未形成“本轮可复现 PASS”证据。

> 历史记录中存在一次 PASS（`reports/gui_step8_smoke_result.json`），但其时间早于本轮重打包，不能替代本轮复验证据。

---

## 4) RC 结论

- **当前结论：NO-GO**
- **已完成项：** 重打包、PE 校验日志、preflight 对齐检查
- **剩余阻塞：** `scripts/smoke_offscreen.py` 本轮至少 1 次 PASS 证据缺失

建议在可稳定运行 Qt offscreen 的同构环境（或 Windows 打包环境）补跑 smoke 并留存 PASS 输出后，转为 GO。
