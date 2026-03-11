# migration_default_from_tzt

## 变更点

1. 在 `app_qt.py` 中扩展 `kirchhoff_migration` 参数面板：
   - 保留现有执行参数：`dx/dt/v/aperture`
   - 新增并默认填入 tzt 参数：`SFCW/freq/len/M-depth/T/num_cal/formatString/MIG_Method/interface/topo_cor/hei_cor/Drill/Contrast/weight/ini_model/gpu_index`

2. 新增“导入 tzt 为迁移默认”入口：
   - UI 按钮：`导入 tzt 为迁移默认`
   - 支持从 `.tzt/.txt/.cfg` 读取 `key value` 样式参数
   - 导入后写入 `_method_param_overrides["kirchhoff_migration"]`，作为 GUI 迁移默认配置

3. 新增迁移默认配置日志机制：
   - 执行 Kirchhoff 前记录“应用参数/存档参数(仅记录)”
   - 执行后在日志和 Record 中追加 `migration-config={...}` 快照
   - 对当前尚未参与计算的字段（如 `interface/topo_cor/hei_cor`）进行可视化保留与日志落地，不影响现有功能

4. 批处理默认参数来源改为 `_resolve_method_params`：
   - 批处理会使用当前 GUI 默认/导入后的迁移配置，而不是硬编码 `params.default`

---

## 已覆盖参数

- 执行参数（会进入 Kirchhoff 方法调用）：
  - `dx`
  - `dt`
  - `v`
  - `aperture`

- 迁移默认配置参数（UI可见、可存储、执行时写日志/报告记录）：
  - `SFCW`
  - `freq`
  - `len`
  - `M-depth`
  - `T`
  - `num_cal`
  - `formatString`
  - `MIG_Method`
  - `interface`
  - `topo_cor`
  - `hei_cor`
  - `Drill`
  - `Contrast`
  - `weight`
  - `ini_model`
  - `gpu_index`

---

## 未覆盖/仅记录参数说明

当前 `method_kirchhoff_migration` 实际计算仍主要使用 `dx/dt/v/aperture`。
以下字段已实现“UI显示 + 默认存储 + 执行日志/Record记录”，但**尚未接入数值计算路径**：

- `SFCW`
- `freq`
- `len`
- `M-depth`
- `T`
- `num_cal`
- `formatString`
- `MIG_Method`
- `interface`
- `topo_cor`
- `hei_cor`
- `Drill`
- `Contrast`
- `weight`
- `ini_model`
- `gpu_index`

---

## 下一步建议

1. 若需与原 tzt 处理链一致，建议在 `method_kirchhoff_migration` 内逐步接入：
   - `topo_cor/hei_cor/interface` 的分支逻辑
   - `M-depth/T/len` 对时间-深度采样网格的控制
   - `Contrast/weight` 的后处理增益或权重策略

2. 增加“迁移默认配置导出/保存”功能（JSON/tzt），实现跨会话持久化。

3. 增加自动化测试：
   - tzt 解析测试
   - 导入后参数回填测试
   - Kirchhoff 执行日志包含关键字段测试
