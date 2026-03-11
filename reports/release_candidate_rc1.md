# GPR GUI Release Candidate (RC1) 收口报告

- 更新时间：2026-03-11 10:06 (Asia/Shanghai)
- 仓库：`/home/baiiy1/.openclaw/workspace/repos/GPR_GUI`
- RC 标识：`v0.2.0-rc1+a0bb7cf`
- 基线提交：`a0bb7cf`
- 决策结论：**GO（preflight 已绿 + 本轮 smoke_offscreen PASS 证据已补齐）**

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

执行命令：

```bash
python3 scripts/smoke_offscreen.py --json-out reports/gui_step8_smoke_result.json --timeout-sec 25 --hard-timeout-sec 60
```

本轮复验结果：**PASS**（见 `reports/gui_step8_smoke_result.json` 与 `reports/smoke_unblock_rc_evidence.md`）。

关键字段：

- `timestamp=2026-03-11T10:04:57+08:00`
- `pass=true`
- checkpoints 全部为 `true`
- `metrics.process_status=worker completed`
- `metrics.elapsed_sec=1.9`

---

## 4) RC 结论

- **当前结论：GO**
- **已完成项：** 重打包、PE 校验日志、preflight 对齐检查、smoke_offscreen 本轮 PASS 复验
- **阻塞状态：** 已解除（smoke gate unblocked）

发布建议：可按 RC1 执行发布流程；保留 `reports/smoke_unblock_rc_evidence.md` 作为本轮 gate 证据归档。
