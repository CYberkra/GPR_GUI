# Legacy Migration Integration Report

## 变更概览
已在 `GPR_GUI` 中完成 legacy 迁移链路的最小集成，新增了 `legacy/` 模块目录、`legacy_migration.py` 入口，并在 GUI 增加“legacy 模式（测试）”开关。

本次补充了 RTM 分支接线（可选开关）与依赖补齐：
- 在 `legacy_migration.run` 中接入 RTM 分支（`legacy_enable_rtm=True` 才启用）
- 在 `legacy/legacy_rtm.py` 中实现动态导入与依赖缺失清单报错
- 从 legacy `PythonModule` 同步 RTM 运行链文件到 `tools/rtm_legacy/`

## 新增/更新模块
- `legacy/legacy_tools.py`
  - 从 legacy `tools` 脚本迁移 `read_param` / `read_gpr_csv_arrays`
  - 增加 `ensure_legacy_workdirs`（按当前项目相对路径创建目录）
- `legacy/legacy_kir.py`
  - 迁移 `shot2RecTime1` / `migrate`
  - 新增 `process_kir` 作为最小 Kirchhoff 处理主入口
- `legacy/legacy_imagesc.py`
  - 提供 `process_kir_images`：归一化后输出 png（`<csv_dir>/results/*_Kir.png`）
- `legacy/legacy_rtm.py`（本次重点更新）
  - 新增 `candidate_rtm_roots()`：按优先级搜索 `tools/rtm_legacy` / `legacy` / `../PythonModule`
  - 新增 `discover_missing_rtm_dependencies()`：检查 RTM 依赖链
  - 新增 `_load_legacy_rtm_module()`：动态导入 legacy `RTM.py`
  - `rtm_gpu()`：统一做 GPU 依赖校验 + 文件依赖校验 + 委托调用
- `tools/rtm_legacy/RTM.py`
  - 来源：`/mnt/e/2026_探地雷达VNA/数据处理软件/CaGPR.exe/Release/PythonModule/RTM.py`
- `tools/rtm_legacy/updatafwd.py`
  - 来源：`/mnt/e/2026_探地雷达VNA/数据处理软件/CaGPR.exe/Release/PythonModule/updatafwd.py`
- `tools/rtm_legacy/updatabwd.py`
  - 来源：`/mnt/e/2026_探地雷达VNA/数据处理软件/CaGPR.exe/Release/PythonModule/updatabwd.py`
- `tools/rtm_legacy/FDTD/tools.py`
  - 来源：`/mnt/e/2026_探地雷达VNA/数据处理软件/CaGPR.exe/Release/PythonModule/FDTD/tools.py`
- `tools/rtm_legacy/FDTD/updatabwd.py`
  - 来源：`/mnt/e/2026_探地雷达VNA/数据处理软件/CaGPR.exe/Release/PythonModule/FDTD/updatabwd.py`
- `tools/rtm_legacy/FDTD/__init__.py`
  - 新增：确保 `FDTD.tools` 可作为包导入

## 统一入口
- `legacy_migration.py`
  - `run(params, csv_path)`
  - `MIG_Method=Kir*`：走 Kirchhoff 最小链路
  - `MIG_Method=RTM*`：
    1. 要求 `params['legacy_enable_rtm']=True`
    2. 先做依赖探测，缺失即抛出带清单的 `FileNotFoundError`
    3. 依赖完整时调用 `legacy_rtm.rtm_gpu(...)`

## 依赖状态（RTM）
已就位（来自 CaGPR Release PythonModule）：
- `tools/rtm_legacy/RTM.py`
- `tools/rtm_legacy/updatafwd.py`（包含 `updatafwd_ini`）
- `tools/rtm_legacy/updatabwd.py`（包含 `updatabwd_ini`）
- `tools/rtm_legacy/FDTD/tools.py`
- `tools/rtm_legacy/FDTD/updatabwd.py`
- `tools/rtm_legacy/FDTD/__init__.py`

> 说明：`RTM.py` 的 `from FDTD.tools import ...` 与 `from updatafwd import ...`, `from updatabwd import ...` 依赖已在仓库内可解析。

## GUI 集成
文件：`app_qt.py`
- 新增复选框：`legacy 模式（测试）`
- 执行 `kirchhoff_migration` 时，若开启该开关：
  - 走 `legacy_migration.run(params, csv_path)`
  - 优先使用 `params['formatString']`，否则回退到当前导入的 `self.data_path`
- 未开启时保持原本本地 Kirchhoff 路径不变

## 运行方式
### A. Kirchhoff（可运行）
1. 启动 GUI：`python app_qt.py`
2. 导入符合 legacy 头格式的 CSV（前 4 行元信息）
3. 方法选择 `7. 迁移（Kirchhoff）`
4. 勾选 `legacy 模式（测试）`
5. 点击“应用所选方法”
6. 结果图输出：`<CSV同目录>/results/*_Kir.png`

### B. RTM（已接线 + 依赖已补齐）
1. 设置 `MIG_Method=RTM`
2. 设置 `legacy_enable_rtm=True`
3. 在 `params['rtm']` 中补齐 RTM 所需参数（`v/sig1/coord/t/xprop/zprop/source/data/dz/npml/...`）
4. 运行 `legacy_migration.run(params, csv_path)`
5. 预期：通过 `legacy.legacy_rtm.rtm_gpu` 分发到 `tools/rtm_legacy/RTM.py`

## 已知限制
1. RTM 分支已可导入与调度，但运行仍依赖 GPU/CUDA（`cupy` + `numba.cuda`）环境和完整 RTM 参数集。
2. `legacy_migration.run` 对 RTM 仅做“接线分发”，不负责自动构造 legacy RTM 全参数。
3. 当前图像输出仍复用 `process_kir_images` 最小实现，未完整覆盖原脚本全部 interface/topo/hei 后处理细节。
4. legacy CSV 读取要求固定 4 行头格式，不兼容纯矩阵 CSV。
