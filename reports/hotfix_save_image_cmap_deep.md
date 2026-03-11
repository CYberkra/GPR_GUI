# hotfix: save_image cmap 参数错配深入排查报告

## 结论（实际根因）
本次报错并非当前 `GPR_GUI/read_file_data.py` 签名问题，而是**运行时导入了错误的同名模块**：

- 正确模块：`GPR_GUI/read_file_data.py`（已支持 `cmap` 与 `**imshow_kwargs`）
- 错误模块：`../PythonModule/read_file_data.py`（旧实现，不支持 `cmap`）

当 `sys.path` 被污染（或打包/启动路径优先级异常）时，`from read_file_data import save_image` 会命中旧模块，触发：

`TypeError: save_image() got an unexpected keyword argument 'cmap'`

## 根因链路图
```text
GUI 调用 save_image(..., cmap=...)
      |
      v
from read_file_data import save_image   (旧写法，依赖 sys.path 搜索)
      |
      +--> 命中 GPR_GUI/read_file_data.py                -> OK
      |
      +--> 命中 ../PythonModule/read_file_data.py (旧签名) -> TypeError(cmap)
```

## 全仓库定位结果
### save_image 定义
- `read_file_data.py:114`（GPR_GUI 内）
- `../PythonModule/read_file_data.py:36`（同名旧实现，仓库外 sibling，实际可被路径污染命中）

### save_image 调用点（GPR_GUI）
- `app.py:931`
- `app_qt.py:2119`
- `app_enhanced.py:482`
- `compare_bg_agc.py:104, 113`
- `tests/test_save_image_cmap_compat.py:22`

### 导入链（已修复前）
- `app.py` / `app_qt.py` / `app_enhanced.py` / `compare_bg_agc.py`
  - `from read_file_data import ...`（受 `sys.path` 顺序影响）

## 修复方案
### 1) 新增稳定桥接模块，强制加载本仓库 read_file_data
新增 `gpr_io.py`：
- 使用 `importlib.util.spec_from_file_location` 按文件绝对路径加载 `GPR_GUI/read_file_data.py`
- 统一导出 `readcsv/savecsv/save_image/show_image`
- 提供 `runtime_save_image_debug()` 输出模块来源 + 签名

### 2) 统一所有入口导入路径，避免同名混用
将以下文件中的导入改为 `from gpr_io import ...`：
- `app.py`
- `app_qt.py`
- `app_enhanced.py`
- `compare_bg_agc.py`

### 3) 缓存影响处理
执行清理（避免旧 pyc 干扰）：
- 删除仓库下 `__pycache__`
- 删除 `.local_quarantine/**/__pycache__`

## 运行时确认（模块来源 + 签名）
`tools/verify_save_image_runtime.py` 输出示例：

```text
module=gpr_gui_read_file_data file=.../repos/GPR_GUI/read_file_data.py sig=(data, outimagename: str, title: str = '', time_range=None, distance_range=None, cmap='gray', **imshow_kwargs)
```

说明：当前实际调用已锁定到本仓库模块，签名包含 `cmap` 与 `**kwargs`。

## 最小可复现 & 最小可验证
新增脚本：`tools/min_repro_save_image_cmap.py`

功能：
1. **复现历史问题**：模拟 `sys.path` 污染优先命中 `../PythonModule/read_file_data.py`，稳定触发 TypeError。
2. **验证修复有效**：在同样污染路径下，通过 `gpr_io.save_image(..., cmap='viridis')` 正常保存图片。

## 自动化验证
新增测试：`tests/test_save_image_runtime_origin.py`
- 模拟污染路径顺序
- 断言 `gpr_io.save_image` 实际来自 `GPR_GUI/read_file_data.py`
- 断言签名包含 `cmap` 和 `**`

现有回归测试继续通过：`tests/test_save_image_cmap_compat.py`

## 修改文件清单
- `gpr_io.py`（新增）
- `app.py`
- `app_qt.py`
- `app_enhanced.py`
- `compare_bg_agc.py`
- `tools/verify_save_image_runtime.py`（新增）
- `tools/min_repro_save_image_cmap.py`（新增）
- `tests/test_save_image_runtime_origin.py`（新增）
- `reports/hotfix_save_image_cmap_deep.md`（本报告）

## 验证命令（给用户）
1. 查看运行时实际模块与签名：
```bash
python3 tools/verify_save_image_runtime.py
```

2. 一次性复现旧问题并验证修复路径：
```bash
python3 tools/min_repro_save_image_cmap.py
```

3. 跑回归测试：
```bash
pytest -q tests/test_save_image_cmap_compat.py tests/test_save_image_runtime_origin.py
```
