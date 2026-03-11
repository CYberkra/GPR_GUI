# Legacy Migration Integration Report

## 变更概览
已在 `GPR_GUI` 中完成 legacy 迁移链路的最小集成，新增了 `legacy/` 模块目录、`legacy_migration.py` 入口，并在 GUI 增加“legacy 模式（测试）”开关。

## 新增模块
- `legacy/legacy_tools.py`
  - 从 legacy `tools` 脚本迁移 `read_param` / `read_gpr_csv_arrays`
  - 增加 `ensure_legacy_workdirs`（按当前项目相对路径创建目录）
- `legacy/legacy_kir.py`
  - 迁移 `shot2RecTime1` / `migrate`
  - 新增 `process_kir` 作为最小 Kirchhoff 处理主入口
- `legacy/legacy_imagesc.py`
  - 提供 `process_kir_images`：归一化后输出 png（`<csv_dir>/results/*_Kir.png`）
- `legacy/legacy_rtm.py`
  - 保留 RTM GPU 入口，当前为 TODO（依赖 cupy/numba + FDTD 链路）

## 统一入口
- `legacy_migration.py`
  - `run(params, csv_path)`
  - 最小串联：`CSV 读取 -> Kirchhoff -> 输出图片`
  - `MIG_Method=RTM*` 时显式抛出 TODO

## GUI 集成
文件：`app_qt.py`
- 新增复选框：`legacy 模式（测试）`
- 执行 `kirchhoff_migration` 时，若开启该开关：
  - 走 `legacy_migration.run(params, csv_path)`
  - 优先使用 `params['formatString']`，否则回退到当前导入的 `self.data_path`
- 未开启时保持原本本地 Kirchhoff 路径不变

## 依赖
最小运行依赖：
- `numpy`
- `pandas`
- `scipy`
- `matplotlib`

RTM TODO 依赖（尚未接通）：
- `cupy`
- `numba[cuda]`
- legacy `FDTD` 相关模块（`gridinterp/padgrid/updatafwd/updatabwd`）

## 运行方式
1. 启动 GUI：
   - `python app_qt.py`
2. 导入符合 legacy 头格式的 CSV（前 4 行元信息）。
3. 方法选择 `7. 迁移（Kirchhoff）`。
4. 勾选 `legacy 模式（测试）`。
5. 点击“应用所选方法”。
6. 结果图默认输出到：`<CSV同目录>/results/*_Kir.png`。

## 已知限制
1. 当前仅打通 CSV -> Kirchhoff 最小链路；RTM 保留 TODO。
2. `legacy_imagesc` 为最小替代实现，未完整覆盖原脚本全部 interface/topo/hei 后处理细节。
3. legacy CSV 读取要求固定 4 行头格式，不兼容纯矩阵 CSV。
4. RTM 仍依赖外部 FDTD 链路与 GPU 环境，当前阶段不建议在 GUI 中启用。
