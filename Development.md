# 开发说明

## 环境与依赖

项目使用 Python，GitHub Actions 使用 Python 3.12。运行时依赖见 `requirements.txt`，不需要额外环境变量。

在项目根目录执行：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

以下命令均在项目根目录执行，`python` 应指向已安装依赖的环境；Windows 可替换为 `.venv/Scripts/python.exe`。

## 生成与校验

无需编译构建。根据已保存的上游快照更新两份配置：

```powershell
python update_rules.py --input sources/Custom_Clash.yaml
python update_rules.py --input sources/Custom_Clash.yaml --check
```

不传 `--input` 时从代码中的默认 HTTPS 上游地址下载，同时更新快照。默认合并根目录的 `custom_rules.yaml`，可通过 `--custom-rules` 指定其他文件。

单独生成远程或内联版本：

```powershell
python convert_clash.py --input sources/Custom_Clash.yaml
python convert_clash.py --input sources/Custom_Clash.yaml --inline
```

分类逻辑位于 `convert_clash.py`，两种输出共用同一逻辑。修改转换逻辑后应重新生成两份 YAML；不要仅手动修改生成文件，否则后续自动更新会覆盖。

## 测试

本地存在 `tests/` 时运行：

```powershell
python -m unittest discover -s tests -v
```

按项目约定，`tests/`（含测试源码）被 Git 忽略，新的检出不包含这些本地测试。任何检出均可运行上述 `--check` 命令验证快照与生成文件是否一致。转换器还会检查策略组引用、循环引用和规则目标，但不替代 Mihomo 的完整配置校验。

## 排错与自动更新

- 依赖缺失：在实际运行脚本的 Python 环境中重新安装 `requirements.txt`。
- 下载失败：检查网络或使用 `--input sources/Custom_Clash.yaml` 离线生成。
- 规则目标未知：检查自定义规则中的策略组名称是否与生成配置完全一致。
- `--check` 返回 1：按输出提示重新生成不一致的文件，再检查差异。
- 分组没有节点：检查面板是否合并了真实节点，以及名称末尾是否严格匹配大写 `WNTT`。

`.github/workflows/update-rules.yml` 负责定时和相关文件推送后的更新，生成并校验后提交快照及两份 YAML。开发修改本身需要自行提交；脚本不会执行 Git 命令。
