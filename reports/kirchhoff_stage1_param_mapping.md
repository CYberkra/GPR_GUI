# Kirchhoff Stage1 参数接入报告

## 目标
将 txt/tzt 迁移参数在 `kirchhoff_migration` 路径中真实生效，保持小步、非破坏性改造。

## 本次改动

### 1) 参数接入计算链路
文件：`app_qt.py`，函数：`method_kirchhoff_migration`

已将以下参数接入：
- `M-depth`：限制迁移有效深度行（`depth_eff`）
- `T`：限制迁移时间窗（`ny_eff`）
- `len`：映射为测线尺度因子，影响横向距离项（`dx_scale`）
- `weight`：迁移叠加权重（累加时乘权）
- `Contrast`：迁移结果对比度线性增益（输出乘系数）

### 2) topo_cor / hei_cor / interface 开关生效
在同一函数内以简化版接入：
- `topo_cor`：启用时执行首样本基线校正（`arr - arr[0:1, :]`）
- `hei_cor`：启用时施加轻量深度增益曲线（0.9~1.0）
- `interface`：启用时对迁移结果做纵向梯度幅值，突出界面

说明：该实现为 stage1 轻量版，明确“影响点”，避免大幅改写算法主干。

### 3) 日志归类更新
`KIRCHHOFF_APPLIED_FIELDS` 现包含：
- `len`, `M-depth`, `T`, `weight`, `Contrast`, `interface`, `topo_cor`, `hei_cor`

`KIRCHHOFF_STORED_ONLY_FIELDS` 保留未接入计算的参数。

### 4) 最小回归测试
新增：`tests/test_kirchhoff_param_mapping_stage1.py`

测试覆盖：
- `T` + `M-depth` 对有效输出行的约束
- `weight` + `Contrast` 的缩放进入计算路径
- `len`/`T`/`M-depth` 被写入返回 metadata（`mapped_params`）

## 兼容性说明
- 默认参数下仍保持 Kirchhoff 主流程（按道累加）
- 新增分支均为可开关、局部影响
- 未改动 core 模块接口和 GUI 参数结构

## 建议后续（stage2）
- 将 `interface/topo_cor/hei_cor` 替换为更贴近业务定义的物理模型
- 将 `M-depth/T/len` 与 time-depth 网格配置统一到可视化坐标链路
