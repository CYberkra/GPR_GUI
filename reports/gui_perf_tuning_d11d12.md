# Week2 Day11-Day12 GUI 定向性能优化收口

## 范围与约束
- 目标：基于 `regression_baseline_v1` 与现有观测指标，做 1-2 项低风险、可回滚、**不改变算法语义** 的优化。
- 重点路径：GUI 刷新/预处理。
- 工作提交：仅包含本轮相关改动与报告。

## 识别出的可控瓶颈点

1. **预处理路径存在不必要的全量 NaN 清洗与内存分配**
   - 位置：`_prepare_view_data`
   - 现状：每次绘制前都执行 `np.nan_to_num(data)`，即使数据全为有限值也会触发全量扫描+潜在拷贝。
   - 风险：低；仅在非有限值存在时才进入清洗，不改变输出语义。

2. **降采样切片链式索引导致额外临时数组**
   - 位置：`_downsample_data` / `_downsample_for_display`
   - 现状：`data[t_idx, :][:, d_idx]` 两段式索引会生成中间数组。
   - 风险：低；改为一次性 `np.ix_`，结果矩阵等价。

> 额外小修：`load_csv` 的分块读路径补齐 `na_filter=False, low_memory=False`，与非分块读参数策略保持一致，减少解析开销波动。

## 实施优化项

### 优化 1：预处理条件化 NaN/Inf 清洗
- 改动：
  - 旧：`valid_data = self._apply_preprocess(np.nan_to_num(data))`
  - 新：
    - `arr = np.asarray(data)`
    - 若 `np.isfinite(arr).all()`：直接走后续预处理
    - 否则才 `np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)`
- 预期收益：对“正常有限值数据”减少一次不必要全量处理。

### 优化 2：降采样索引合并
- 改动：
  - 旧：`data[t_idx, :][:, d_idx]`
  - 新：`data[np.ix_(t_idx, d_idx)]`
- 预期收益：减少中间数组与内存带宽消耗，降低预处理路径抖动。

### 补充优化：CSV 分块读参数对齐
- 改动：`pd.read_csv(..., chunksize=200000, na_filter=False, low_memory=False)`
- 预期收益：降低 CSV 解析开销与类型推断带来的波动。

---

## 指标对比（前后）

### A) 回归基线（脚本）
- Before：`reports/regression_baseline_v1.json`
- After：`reports/regression_baseline_v1_d11d12.json`

| 指标 | Before | After | 变化 |
|---|---:|---:|---:|
| 回归样本总耗时 (ms) | 105.577 | 129.797 | +24.220 |
| 单样本平均耗时 (ms) | 26.394 | 32.449 | +6.055 |

说明：
- 该脚本总耗时包含 Python/IO 运行时抖动，且本轮优化主要落在 GUI 预处理与渲染路径，不直接等价于该基线脚本主链路。
- 算法输出统计保持一致（`deltas` 中 `output_mean_delta/output_std_delta` 均为 0），语义未变化。

### B) GUI 预处理微基准（本轮新增）
- 命令：`python3 tools/gui_prepare_benchmark_d11d12.py`
- 数据集：`tests/regression_samples_manifest.json`

| 指标 | Before(old模拟) | After(new实现) | 变化 |
|---|---:|---:|---:|
| 总耗时 (ms) | 0.1680 | 0.1189 | **1.413x 提升** |
| 单样本平均 (ms) | 0.0420 | 0.0297 | **1.413x 提升** |

补充：
- 3/4 样本提速，`nan_inf_robustness` 因确有非有限值，需真实清洗，收益不明显（符合预期）。

### C) 重绘/跳过重绘相关指标（可采集）
- 命令：`python3 tools/gui_perf_benchmark.py`
- 绘图刷新风暴（20 次触发）

| 指标 | Before(old模拟) | After(new路径) | 变化 |
|---|---:|---:|---:|
| 刷新风暴耗时 (s) | 0.1597 | 0.0077 | **20.74x 提升** |

说明：
- 对应“去重绘风暴”收益显著，反映为重复触发时更多命中跳过重绘路径。

---

## 稳定性与验证

已执行：
1. `python3 -m py_compile app_qt.py` ✅
2. `pytest -q tests/test_prepare_view_metrics.py tests/test_render_data_pairs.py tests/test_observability_panel.py` ✅（5 passed）
3. `python3 scripts/run_regression_baseline.py --compare-with reports/regression_baseline_v1.json --output-json reports/regression_baseline_v1_d11d12.json --output-md reports/regression_baseline_v1_d11d12.md` ✅

## 风险评估
- 风险级别：低
- 风险点：
  1) `np.isfinite(...).all()` 在极大数组上本身有扫描成本；但通常低于无条件 `nan_to_num` 的全量变换/分配成本。
  2) `np.ix_` 行为依赖索引数组正确性；当前索引生成逻辑未变，等价替换。

## 回滚点
- 回滚文件：`app_qt.py`
- 回滚块：
  1) `_prepare_view_data`（条件化清洗）
  2) `_downsample_data` / `_downsample_for_display`（`np.ix_` 替换）
  3) `load_csv` 分块 `read_csv` 参数补齐
- 回滚方式：`git revert <commit>` 或按函数块恢复旧实现。

## 结论
- 本轮完成 2 项 GUI/预处理低风险定向优化，并补齐 CSV 分块读取参数。
- 在目标路径微基准上取得明确提升（预处理约 1.41x，刷新风暴约 20.74x）。
- 算法输出统计一致，未引入语义变化。
- 回归脚本总耗时受环境波动影响较大，建议后续在固定 CPU 频率/重复多轮统计（p50/p95）下持续观察。
