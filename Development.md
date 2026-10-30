# 开发说明

## 环境和文件

Python 3.10+，依赖见 `requirements.txt`。无需编译，安装和本地运行命令见 README。

- `convert_clash.py`：读取源模板和自定义规则，转换策略组、校验引用及生成确定性 YAML。
- `update_rules.py`：一次下载，校验后更新原始快照和两份规则；`--check` 只读检查一致性。
- `.github/workflows/update-rules.yml`：定时/手动更新及变化提交。
- `tests/`：本地回归测试源码，按项目要求被 Git 忽略，保留在磁盘中。

## 转换与验证

带地区 `filter` 的提供者测速组被移除；未过滤的自动测速组保留。原 `use` 节点注入改为 `include-all-proxies: true`。不向业务组额外加入 `PROXY`，以保留排除地区项后的候选顺序和独立节点选择行为。远程模式保留面板 `PROXY`，内联模式重建动态 `PROXY`。

当前对齐范围是非地区组名称、类型、组间引用顺序、实际节点注入，以及自动测速参数。没有承诺节点名称排序、提供者更新方式、TLS 覆盖参数或 INI 与 YAML 规则集一致。自定义规则原文及顺序保持不变。

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe update_rules.py --input sources/Custom_Clash.yaml
.\.venv\Scripts\python.exe update_rules.py --input sources/Custom_Clash.yaml --check
```

回归测试覆盖候选组与节点注入、自动测速实际节点和参数、缺失测试地址、规则保留、自定义规则优先、未知引用、循环、批量更新幂等及失败保留输出。云端执行转换内置校验与快照一致性校验，不依赖未提交的本地测试目录。

若出现未知组、组循环或测试地址缺失，更新将失败，修复模板或转换器后重跑。动态收集需要 Mihomo 客户端支持；Python 引用校验不替代实际内核加载测试。更改后应重生成两份 YAML，并检查 Actions 结果。
