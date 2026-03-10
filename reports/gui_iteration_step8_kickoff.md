# GUI Iteration Step8 Kickoff（可维护性/体验继续优化）

- 日期：2026-03-11
- 基线版本：`win_20260311_93a82fb`
- 目标：在不扩大风险的前提下，继续提升可维护性与回归验证效率。

## A. 候选任务（按收益高 -> 低）

### 1) 发布前检查脚本化（高收益）

- 内容：把 artifact/PE/version/commit 对齐检查固化为可复用脚本，避免手工漏项。
- 收益：每次发包都能“一键预检 + 标准化输出”，降低发布事故概率。
- 成本：低（单文件脚本 + 文档命令）。

### 2) GUI 关键路径轻量 smoke 测试（中高收益）

- 内容：补一组最小可运行测试（启动窗口、加载最小 CSV、调用 1 个处理链）并纳入回归。
- 收益：发现“打包后可启动但不可用”的早期故障。
- 成本：中（需处理 PyQt 事件循环与无头环境兼容）。

### 3) 版本信息在 GUI 内可见（中收益）

- 内容：在窗口标题/关于面板显示 `RELEASE_VERSION` 与短 commit。
- 收益：现场排障、截图定位版本更快；减少“跑错包”成本。
- 成本：低到中（UI 文案 + 读取版本文件兜底）。

## B. 本次已落地（小改动 + 可验证）

### 已完成项

新增脚本：`tools/preflight_check.py`

能力：

- 检查目标 artifact 是否存在；
- 输出大小与时间戳；
- 检查同名 PE 验证日志是否存在并提取关键字段；
- 检查 `dist/RELEASE_VERSION.txt` 是否存在；
- 自动比对 `RELEASE_VERSION` 末尾短 hash 与 `git rev-parse --short=7 HEAD`；
- 支持 `--json` 输出，便于后续 CI 或自动化复用；
- 当关键条件不满足时返回非 0 退出码。

### 验证命令

```bash
python3 tools/preflight_check.py --artifact dist/GPR_GUI_Qt_win_20260311_93a82fb.exe --json
```

本地验证结果：

- `artifact_exists=true`
- `verify_log_exists=true`
- `release_version_exists=true`
- `verify_fields.pe_verify_passed=True`
- `commit_aligned=true`

结论：✅ 小改动已可用且可重复验证。

## C. 下一步建议（Step8 执行节奏）

1. 先把 `preflight_check.py` 接入打包流程末尾（构建后自动执行，失败即阻断）。
2. 增加 1 条 GUI 启动级 smoke test（无头环境）。
3. 增加 GUI 版本可见性（标题栏或 About），并截图纳入发布记录。
