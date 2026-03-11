# Kirchhoff stage1+2 状态核对报告

## 最终结论
**部分完成（已修复并补提）**

- **stage1（参数接入）**：此前仅有“默认值/导入/日志”层面提交，核心计算路径接入在工作区未提交状态；现已补齐并提交。
- **stage2（插值+权重升级）**：此前未在已推送提交中落地；现已补齐并提交。

## 证据与提交链路

1. `ef9b430`（已在主线历史）
   - Merge isolated Kirchhoff/depth updates 到主分支。
2. `9c0830e`（`origin/main` 已推送）
   - 主要完成 tzt 默认参数导入、UI 展示、日志记录；并未完整完成 stage2 计算升级。
3. `2064eda`（已推送）
   - 完成 stage1 计算路径接入：`M-depth/T/len/weight/Contrast` + `topo_cor/hei_cor/interface` 进入 Kirchhoff 实算。
4. `5b477b4`（已推送，本次补提）
   - 完成 stage2：走时采样由整数索引升级为线性插值；叠加采用偏移相关权重（taper + 几何衰减）升级。

## 关键变更摘要

- **stage1 参数接入（真实生效）**
  - `T`：限制有效时间窗（`ny_eff`）
  - `M-depth`：限制成像深度（`depth_eff`）
  - `len`：映射到 `dx_scale` 影响道间距
  - `weight`：作为迁移叠加增益
  - `Contrast`：输出整体对比增益
  - `topo_cor/hei_cor/interface`：分别控制地形基线修正/深度增益修正/界面梯度增强
- **stage2 升级**
  - 由整数 `t_idx` 采样升级为**线性插值采样**（减少走时离散误差）
  - 叠加权重升级为**偏移 taper + 几何衰减**的组合权重（替代原单一常数权重）

## 用户可执行验证命令（<=3条）

1. `cd /home/baiiy1/.openclaw/workspace/repos/GPR_GUI && git log --oneline --decorate -n 8`
2. `cd /home/baiiy1/.openclaw/workspace/repos/GPR_GUI && git show --name-only --oneline HEAD`
3. `cd /home/baiiy1/.openclaw/workspace/repos/GPR_GUI && python3 -m py_compile app_qt.py`
