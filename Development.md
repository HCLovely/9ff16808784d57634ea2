# 开发说明

## 环境与目录

Python 3.10+，依赖固定为 `PyYAML==6.0.3`。当前已在 Windows / Python 3.12.13 下验证。安装与虚拟环境命令见 README；不需要环境变量、构建步骤或打包服务。

- `convert_clash.py`：HTTPS/本地输入、转换、引用校验、原子写入及命令行入口。
- `update_rules.py`：一次读取源数据，校验后批量更新快照和两份规则；支持只读 `--check`。
- `.github/workflows/update-rules.yml`：定时、手动和相关源码推送触发的更新工作流。
- `.gitattributes`：保留 YAML 实际字节，避免 Windows 换行转换造成摘要或输出不一致。
- `sources/Custom_Clash.yaml`：本次下载的原始模板快照，用于离线复现。
- `Custom_Clash_3xui.yaml`：可交给面板的输出。
- `Custom_Clash_3xui_inline.yaml`：可直接粘贴到面板的版本，补上动态 `PROXY`。
- `tests/test_converter.py`：本地回归测试。按项目要求，整个测试源码目录被 Git 忽略，但保留在磁盘上，不会默认随提交交付。

## 转换约束

远程路由通过与面板已生成的配置合并获得实际节点，远程版保持 `PROXY` 不被覆盖；内联版因策略组整体替换，主动定义使用 `include-all-proxies` 的动态 `PROXY`。不能把节点提供者 `use` 原样传给远程规则校验器。输入中的提供者测速组折叠到 `PROXY`；其余只支持 `select`，未知类型报错。未知静态节点引用也报错，防止依赖被远程白名单丢弃的 `proxies`。

`validate_routing` 对照上游的策略组、规则集和规则目标引用校验实现，并额外检查循环引用。它是针对本转换输出的 Python 校验器，约束比上游更窄，不是上游 Go 校验器或完整 Mihomo 配置检查器。网络读取上限和输出限制为 2 MiB，下载超时 30 秒；面板自身远程抓取超时见 README。

## 验证

在项目根目录执行：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe convert_clash.py --input sources/Custom_Clash.yaml
.\.venv\Scripts\python.exe convert_clash.py --input sources/Custom_Clash.yaml --inline
.\.venv\Scripts\python.exe update_rules.py --input sources/Custom_Clash.yaml --check
```

测试覆盖真实模板的规则与提供者保留、输入不被修改、缺少规则集、未知节点、重复组、循环引用、带 `no-resolve/src` 的目标重映射、规则集代理引用、内联替换后动态节点组的保留、保留组名保护及失败时保留旧输出。

发布前还应人工在实际部署版本的面板中保存配置，并更新 Mihomo 订阅，检查合并后的节点、`PROXY`、策略组、规则、GeoData 和外部规则集。当前未访问用户面板，不能把本地检查描述为实际部署验证。

## 常见开发问题

直接运行系统的 `python` 可能命中 Windows 应用商店占位符，优先用虚拟环境的解释器。缺少 `yaml` 模块时，在同一解释器下执行 `-m pip install -r requirements.txt`。终端中文乱码可将 PowerShell 中的 `$env:PYTHONIOENCODING` 设为 `utf-8`；文件始终以 UTF-8 写入。

## 自动发布

工作流使用 Ubuntu、Python 3.12，以及固定到提交 SHA 的官方 checkout/setup-python Actions。每次运行调用 `update_rules.py` 获取最新上游并完成两种转换，再使用已保存快照进行 `--check` 检查。只有全部步骤通过才暂存三个生成文件、提交并普通推送到默认分支。

`contents: write` 只授权本仓库的内容更新；工作流不使用跨仓库凭据。并发组避免两个更新任务同时执行；如果运行期间有人提交导致远程分支前进，普通推送会失败，不自动 rebase 或强制推送。可审阅后重新运行任务。

本地回归测试源码按项目要求未纳入 Git，不能把工作流配置为运行不存在的 `tests/`。云端运行实际转换、内置引用校验和快照一致性校验。开发者本地另有回归测试，覆盖批量生成、幂等更新和只读检查。源数据大小上限仍为 2 MiB，不会将海量规则集内容打包进输出。

修改转换逻辑后运行 `update_rules.py --input sources/Custom_Clash.yaml`，审阅生成差异，并随程序一起提交。查看 Actions 日志排查下载失败、模板结构变化或仓库写入权限问题。
