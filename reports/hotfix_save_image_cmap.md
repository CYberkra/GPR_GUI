# Hotfix Report: save_image cmap TypeError

## 背景
运行 GUI 批处理/导出流程时，调用 `save_image(..., cmap=...)` 报错：
`TypeError: save_image() got an unexpected keyword argument 'cmap'`

## 根因定位（触发栈）
调用方（均会传 `cmap`）：
- `app.py` `_save_outputs()` 中调用 `save_image(..., cmap=self._get_colormap())`（约第 931 行）
- `app_qt.py` `_save_outputs()` 中调用 `save_image(..., cmap=self._get_colormap())`（约第 2119 行）

不匹配点：
- 公共保存函数 `read_file_data.py::save_image` 的签名与调用方不一致时（旧版本/打包产物中常见），会在收到 `cmap` 关键字时报 `TypeError`。

## 最小修复
文件：`read_file_data.py`

将 `save_image` 签名增强为兼容形式：
- `def save_image(..., cmap='gray', **imshow_kwargs)`
- 保持现有 `cmap` 参数语义不变
- 允许额外 `imshow` kwargs（向后/向前兼容）
- 当 `imshow_kwargs` 中也有 `cmap` 且显式参数仍是默认 `gray` 时，优先采用 kwargs 内的 `cmap`

这样可避免不同调用风格/历史代码路径下的关键字不兼容报错，同时不改变当前主调用链行为。

## 回归测试
新增：`tests/test_save_image_cmap_compat.py`
- 用例：`save_image(data, out_png, title='regression', cmap='viridis')`
- 断言：不抛异常且成功落盘（文件存在且大小 > 0）

## 验证结果
1. 回归测试：
- 命令：`pytest -q tests/test_save_image_cmap_compat.py`
- 结果：`1 passed`

2. 最小运行验证（直达保存路径）：
- 调用 `save_image(..., cmap='jet', time_range=..., distance_range=...)`
- 输出：`output/_hotfix_save_image_smoke.png`
- 结果：文件成功生成，未再出现 `TypeError`

## 风险评估
- 低风险：仅扩展 `save_image` 入参兼容性，默认行为保持一致。
- 额外 kwargs 仅透传给 `matplotlib.pyplot.imshow`，对既有调用无破坏。

## 回滚方案
若需回滚：
1. `git revert <this_commit>`
2. 或将 `read_file_data.py` 中 `save_image` 恢复到原签名/实现。
