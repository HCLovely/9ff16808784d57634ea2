# 3x-ui Clash 全局路由转换

将 Aethersailor 的 OpenClash 配置转换为 3x-ui 可合并到 Clash/Mihomo 订阅的路由片段，并保留可重复运行的 Python 转换程序。

## 直接使用已转换文件

提供两份成品，都包含 28 个业务策略组、8 个规则提供者和 46 条分流规则，不包含服务器节点信息：

| 使用方式 | 文件 | 节点选择组 |
| --- | --- | --- |
| 直接粘贴 YAML 文本（推荐） | [Custom_Clash_3xui_inline.yaml](Custom_Clash_3xui_inline.yaml) | 额外定义动态 `PROXY`，共 29 个组 |
| 将文件托管为远程 HTTPS URL | [Custom_Clash_3xui.yaml](Custom_Clash_3xui.yaml) | 保留面板原有 `PROXY`，文件中有 28 个组 |

1. 在 3x-ui 的订阅设置中启用 Clash 订阅及其全局路由功能。不同版本的菜单文字可能不同；对应配置字段是 `subClashEnable`、`subClashEnableRouting` 和 `subClashRules`。
2. 把 `Custom_Clash_3xui_inline.yaml` 的**完整文本**粘贴到 Clash 全局路由规则输入框，替换原来的远程 URL，然后保存。直接粘贴可绕过面板抓取远程模板的网络问题。
3. 在支持 Mihomo 的客户端中重新更新面板生成的订阅，使用规则模式。在 `PROXY` 组中选择需要的节点。

如果使用远程 URL，公开仓库 `HCLovely/9ff16808784d57634ea2` 发布后，可在同一输入框填写以下直达地址：

```text
https://raw.githubusercontent.com/HCLovely/9ff16808784d57634ea2/main/Custom_Clash_3xui.yaml
```

使用 URL 后，GitHub Actions 的后续更新会保留这个地址。面板按自身缓存策略刷新，客户端还需更新订阅才能获得新规则。本机磁盘路径不能作为面板服务器的远程 URL。

两份文件分开的原因：当前 3x-ui 对远程规则的策略组按名称合并，内联 YAML 则替换整个策略组列表。内联版本使用 Mihomo 的 [`include-all-proxies`](https://wiki.metacubex.one/en/config/proxy-groups/) 收集面板生成的所有节点；不要将不含 `PROXY` 定义的远程版本直接粘贴。动态收集按节点名排序，并可能包括面板注入的流量提示占位节点；请选择实际节点。

这是**订阅客户端的分流规则**，不应粘贴进 Xray 服务端路由 JSON。文件依赖面板注入的 `PROXY` 组，不能单独作为完整客户端配置导入。应使用 Mihomo 订阅；当前上游的旧版 Clash 兼容订阅路径不应用这套自定义路由。

## 为什么原文件不能直接使用

原文件通过 `proxy-providers.provider1` 加载机场节点，且 `url` 只是占位符。策略组里的 `use: [provider1]` 用于引用这些节点。

3x-ui 的远程路由只接纳 `proxy-groups`、`rule-providers`、`rules` 等白名单字段，不接纳远程节点提供者，并明确拒绝策略组里非空的 `use`。因此原文件即使能成功下载，也存在确定的校验冲突。日志中的 `no validated value is cached` 是通用失败信息，也可能由网络、超时等问题触发，单凭该日志不能排除网络原因。

本项目依据 2026-10-30 查询到的上游实现，检查版本为 `c621ba9014a6aa21fd7c9ecf45655e44e24ebf13`：

- [策略组合并及远程格式校验](https://github.com/MHSanaei/3x-ui/blob/c621ba9014a6aa21fd7c9ecf45655e44e24ebf13/internal/sub/clash_service.go)
- [远程获取、超时和缓存校验](https://github.com/MHSanaei/3x-ui/blob/c621ba9014a6aa21fd7c9ecf45655e44e24ebf13/internal/sub/remote_routing.go)
- [原始 OpenClash 模板](https://github.com/Aethersailor/Custom_OpenClash_Rules/blob/main/cfg/yaml/Custom_Clash.yaml)

你的实际安装版本未提供；如果行为不同，应对照该版本的实现核实。

## 转换后的行为

- 删除 `proxy-providers` 和策略组 `use`，节点统一通过 `PROXY` 组选择。远程版保留面板原有组，内联版建立动态组引用面板实际节点。
- 将自动测速及六个地区测速组折叠为 `PROXY`，同步替换引用并去重。业务组保留，可选择代理或直连；多个业务组引用同一个 `PROXY`，其节点选择共享。没有保留原模板的地区筛选、自动测速或按业务独立选择不同实际节点的能力。
- 业务 `select` 组只保留名称、类型和候选组，去掉测速等无关参数。
- 当前快照的 46 条规则原文和先后顺序完整保留，包括最终 `MATCH`、`no-resolve`；8 个规则提供者完整保留。
- 不注入 DNS、TUN、嗅探、端口或 GeoData 下载配置。

原模板使用 `GEOSITE` 和 MRS 规则集，需要客户端支持 Mihomo，并能获取相应 GeoSite/GeoIP 数据及规则提供者 URL。转换不会把这些外部数据嵌入文件，也没有在你的面板或客户端上做实际连通性测试。

## 重新转换或更新

### GitHub Actions 自动更新

工作流为 [Update Clash rules](.github/workflows/update-rules.yml)，每 6 小时检查一次，计划北京时间 **02:23、08:23、14:23、20:23** 运行。GitHub 可能延迟调度；定时任务只在默认分支运行，公开仓库连续 60 天没有活动时可能被自动停用，届时到 Actions 页面重新启用。[GitHub 调度说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

每次更新下载同一份源模板，生成远程版与内联版，通过格式和引用校验后，将源快照及两份规则中的变化提交到仓库。内容不变不产生提交，失败不发布，推送不会强制覆盖远程提交。工作流使用本仓库的 `GITHUB_TOKEN` 和 `contents: write`，不需要额外配置个人 Token。

可在仓库 **Actions → Update Clash rules → Run workflow** 手动运行。转换程序、更新程序、依赖或工作流推送到 `main` 时也会触发更新。这里只更新 GitHub 仓库；你的电脑目录不会被云端自动改写，需要时在工作区干净的情况下运行 `git pull --ff-only`。

如果仓库策略禁止 Actions 写入，或默认分支受保护，自动提交推送会失败，应根据仓库策略允许该工作流写入；运行结果和错误记录在 Actions 页面。

### 本地运行

需要 Python 3.10 或更高版本。以下命令在本项目目录执行；Windows 可将 `python` 换成自己实际安装的 `py -3` 或 `python3.12`。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 推荐：一次下载，同时更新源快照与两份规则
.\.venv\Scripts\python.exe update_rules.py

# 离线检查源快照与两份规则是否一致，不修改文件
.\.venv\Scripts\python.exe update_rules.py --input sources/Custom_Clash.yaml --check

# 从原始 HTTPS 地址下载最新模板并转换
.\.venv\Scripts\python.exe convert_clash.py

# 从最新模板生成适合直接粘贴的版本
.\.venv\Scripts\python.exe convert_clash.py --inline

# 使用随项目保留的原始快照离线转换
.\.venv\Scripts\python.exe convert_clash.py --input sources/Custom_Clash.yaml
.\.venv\Scripts\python.exe convert_clash.py --input sources/Custom_Clash.yaml --inline

# 指定其他本地文件和输出文件
.\.venv\Scripts\python.exe convert_clash.py --input my-template.yaml --output my-routing.yaml
```

Linux/macOS 使用 `.venv/bin/python` 替换 Windows 虚拟环境解释器路径。程序只依赖 `requirements.txt` 中的 PyYAML。`update_rules.py` 同步更新源快照与两份规则；单文件工具 `convert_clash.py` 不改写源快照。输出注释记录输入内容的 SHA256，便于复核来源。

下载或转换校验失败时返回非零退出码，已有输出保持不变。成功生成并检查后，再粘贴到面板或更新自己托管的文件。Python 程序不会操作面板、写入订阅节点或自动推送 Git；只有 Actions 工作流会提交并推送生成文件。

## 排错

- 粘贴文本成功、远程 URL 失败：检查**面板服务器**到托管地址的 HTTPS 连通性、响应内容是否为 YAML，以及是否在上游的 6 秒抓取超时内返回；本机能访问不代表服务器也能访问。
- 客户端提示 `PROXY` 不存在：很可能把路由片段单独作为完整配置导入了。应更新 3x-ui 生成的完整订阅。
- 客户端提示规则集或 GeoData 失败：检查对应外部下载地址、客户端版本及 GeoData；面板格式校验通过不代表这些资源一定可用。
- 转换提示未知组、缺少规则提供者或不支持的组类型：输入模板发生了结构变化，程序会停止，避免静默生成错误配置。

开发和验证方法见 [Development.md](Development.md)。
