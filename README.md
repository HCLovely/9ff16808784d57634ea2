# 3x-ui Clash 路由规则

将 Aethersailor 的 OpenClash YAML 转换为 3x-ui 可用的 Clash/Mihomo 路由片段，GitHub Actions 每 6 小时自动更新。

## 使用

在 3x-ui 的 Clash 全局路由规则中填写远程地址，保存后更新客户端订阅：

```text
https://raw.githubusercontent.com/HCLovely/9ff16808784d57634ea2/main/Custom_Clash_3xui.yaml
```

如果直接粘贴文件内容，请使用 [Custom_Clash_3xui_inline.yaml](Custom_Clash_3xui_inline.yaml)。远程版有 29 个组，面板合并后加上原有 `PROXY`，共 30 个；粘贴版主动定义动态 `PROXY`，文件中有 30 个组。必须配合面板完整订阅和 Mihomo 使用，不能作为独立节点配置导入。

## 策略组行为

除地区分组外，对齐上游模板及在线转换的组名、类型、组间候选项顺序和节点注入范围：

- 保留 `♻️ 自动选择`，使用全部实际节点测速，原测试地址、300 秒间隔和 50 毫秒容差保留。
- 模板中原本可直接选择节点的业务组仍可独立选择实际节点，不再共用 `PROXY` 的节点选择状态。
- 原本只允许选择其他组的业务组保持这一限制；直连组保持 `DIRECT`。
- 六个地区测速组仍不保留，从其他组的候选项中移除它们。`PROXY` 是面板兼容组，保留供自定义规则等引用。

`include-all-proxies: true` 用于动态收集面板节点，代替 3x-ui 远程校验禁止的 `use`。节点由 Mihomo 按名称排序，具体顺序可能与在线转换提供者不同；面板提示占位节点也可能被收集。分流规则继续采用 YAML 模板的 46 条规则及 8 个规则集，不将其替换为 INI 模板。

## 自定义规则

编辑 [custom_rules.yaml](custom_rules.yaml) 的 `rules` 列表。自定义规则优先于上游规则，并同步进入远程版和粘贴版。不要直接修改生成文件，否则下次自动更新会覆盖。

## 自动更新与本地运行

Actions 计划北京时间 02:23、08:23、14:23、20:23 检查上游，也可在 Actions 页面手动运行。内容有变化才提交，下载或校验失败不发布。面板缓存刷新后，客户端仍需更新订阅。

本地需要 Python 3.10+：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe update_rules.py
.\.venv\Scripts\python.exe update_rules.py --input sources/Custom_Clash.yaml --check
```

Linux/macOS 使用 `.venv/bin/python`。开发验证方法见 [Development.md](Development.md)。
