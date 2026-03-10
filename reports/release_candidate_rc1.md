# GPR GUI Release Candidate (RC1) 收口报告

- 生成时间：2026-03-11 01:46 (Asia/Shanghai)
- 仓库：`/home/baiiy1/.openclaw/workspace/repos/GPR_GUI`
- RC 标识：`v0.2.0-rc1+b3dc9b7`
- 基线提交：`b3dc9b7` (`perf/gui: optimize prepare-view/downsample path and publish d11d12 tuning report`)
- 决策结论：**NO-GO（条件化放行）**

---

## 1) 关键改动汇总

### Week1（D1-D7）
- 环境与基线：建立回归样本基线、offscreen smoke 入口与稳定化（`b7e1091`, `bd5a301`, `3d43668`）。
- 渲染链路质量：重构绘图辅助路径与标签/extent 逻辑，补齐回归测试矩阵（`61c714b`, `ccb0981`, `a304399`, `93ba870`）。
- 错误体验：增强 CSV/参数/worker 异常信息可解释性（`85ea1d3`）。

### Week2（D8-D12）
- 版本可见性与预发布：GUI 显示 release+commit，产物打包与 preflight 报告落地（`794d094`, `93a82fb`, `bcf6da4`）。
- 参数预设体系：引入 preset v1，并补齐 apply/switch 回归测试（`085fd9d`, `8fe0055`）。
- 可观测与性能：新增轻量 observability panel；完成 prepare-view/downsample 低风险优化与 D11-D12 性能报告（`cac09fd`, `b3dc9b7`）。

---

## 2) 预发布检查（Preflight + 关键测试入口）

## 2.1 Windows 产物 preflight
执行：

```bash
python3 tools/preflight_check.py --repo-root . --artifact dist/GPR_GUI_Qt.exe --json
python3 tools/preflight_check.py --repo-root . --artifact dist/GPR_GUI_Qt_win_20260311_93a82fb.exe --json
```

结果摘要：
- `dist/GPR_GUI_Qt.exe`
  - `artifact_exists=true`
  - `verify_log_exists=false`（缺同名 `_pe_verify.txt`）
  - `release_version=win_20260311_93a82fb`
  - `git_short_head=b3dc9b7`
  - `commit_aligned=false`
- `dist/GPR_GUI_Qt_win_20260311_93a82fb.exe`
  - `artifact_exists=true`
  - `verify_log_exists=true`
  - `pe_verify_passed=True`
  - 但 `commit_aligned=false`（当前 HEAD 已推进到 `b3dc9b7`，产物仍对应 `93a82fb`）

结论：**当前 HEAD 对应的 Windows 可发布产物未完成版本对齐，preflight 未通过。**

补齐步骤（必须）：
1. 在当前 HEAD (`b3dc9b7`) 重新执行 Windows 打包流程（`tools/build_windows_exe.ps1`）。
2. 生成并保留同名 PE 验证日志（`*_pe_verify.txt`），确保 `pe_verify_passed=True`。
3. 更新 `dist/RELEASE_VERSION.txt` 为当前产物版本（suffix 与 `b3dc9b7` 对齐）。
4. 再次运行 `tools/preflight_check.py`，需达到 `commit_aligned=true` 且硬性检查全绿。

## 2.2 关键测试入口校验

### Smoke（关键路径）
执行：

```bash
QT_QPA_PLATFORM=offscreen python3 scripts/smoke_offscreen.py --json-out reports/gui_step8_smoke_result.json
```

结果：**PASS**
- `startup/load_sample/core_process_once/plot_refresh/shutdown` 全部 `true`
- 输出：`reports/gui_step8_smoke_result.json`

### 关键回归
执行：

```bash
pytest -q tests/test_gui_presets_v1.py tests/test_error_message_ux_v1.py tests/test_observability_panel.py
pytest -q tests/test_prepare_view_metrics.py tests/test_render_data_pairs.py
```

结果：**10 passed**（7 + 3）

---

## 3) 已知风险

1. **发布产物与代码提交不对齐（阻断）**：当前可用 exe 与 HEAD 不一致，无法声明“源码=可执行”可追溯性。  
2. **`dist/GPR_GUI_Qt.exe` 缺同名 PE 验证日志（阻断）**：无法满足 preflight 硬门槛。  
3. **工作区存在未收敛改动**（非阻断但高操作风险）：发布窗口内需避免误打包/误提交。

---

## 4) 回滚策略

- 代码回滚：若 RC 后发现问题，优先 `git revert` 回滚 D11-D12 变更提交（建议从 `b3dc9b7`、`cac09fd` 起按范围回退）。
- 产物回滚：回退到上一版已通过 preflight 且对齐的包（`93a82fb` 对应包）作为临时体验包。
- 文档回滚：保留本 RC 报告，新增补充章记录回滚触发条件与处置时点。

---

## 5) 验证清单（Release Checklist）

- [x] 关键路径 smoke（offscreen）通过
- [x] 关键回归（presets/error UX/observability/prepare-view/render）通过
- [ ] 当前 HEAD 的 Windows 包生成完成
- [ ] PE 验证日志齐备且 `pe_verify_passed=True`
- [ ] `RELEASE_VERSION.txt` 与 HEAD short hash 对齐
- [ ] `tools/preflight_check.py` 硬性检查全通过
- [ ] 终版 RC 标签更新为 GO

---

## 6) 发布决策建议

- **当前建议：NO-GO**
- **条件化放行标准（全部满足后可转 GO）：**
  1. 重新构建 `b3dc9b7` 对应 Windows 产物；
  2. preflight 硬检查全通过（含 verify log、`pe_verify_passed=True`、`commit_aligned=true`）；
  3. 在新产物上复跑一次 smoke（可复用当前脚本）。

> 结论：功能与回归面已具备 RC 水平，但“产物-提交对齐”尚未达发布门槛，因此本轮判定 NO-GO。
