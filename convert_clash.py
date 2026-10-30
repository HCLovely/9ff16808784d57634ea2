"""将 OpenClash 模板转换为 3x-ui Clash 全局路由片段。

运行方法：python convert_clash.py
离线转换：python convert_clash.py --input sources/Custom_Clash.yaml
输入是 YAML 文件或 HTTPS 地址；输出不含节点，必须与面板订阅合并使用。
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import yaml


DEFAULT_SOURCE = (
    "https://raw.githubusercontent.com/Aethersailor/Custom_OpenClash_Rules/"
    "refs/heads/main/cfg/yaml/Custom_Clash.yaml"
)
MAX_BYTES = 2 * 1024 * 1024
DEFAULT_CUSTOM_RULES = Path(__file__).resolve().parent / "custom_rules.yaml"
BUILTINS = {"DIRECT", "REJECT", "REJECT-DROP", "REJECT-TINYGIF", "PASS", "GLOBAL"}


def read_custom_rules(path: Path, optional: bool = False) -> list[str]:
    """读取本地自定义规则；默认文件缺失时保持原有行为，显式指定的路径必须存在。

    仅接受 rules 列表，拒绝拼错的字段，避免配置被静默忽略。
    规则目标在与上游配置合并后统一校验。
    """
    if optional and not path.exists():
        return []
    document = yaml.safe_load(read_source(str(path)).decode("utf-8-sig"))
    if not isinstance(document, dict) or set(document) != {"rules"}:
        raise ValueError("自定义配置必须只包含 rules 字段；无规则时使用 rules: []")
    rules = document["rules"]
    if not isinstance(rules, list):
        raise ValueError("自定义 rules 必须为列表")
    for rule in rules:
        if not isinstance(rule, str) or not rule.strip():
            raise ValueError("自定义规则必须为非空字符串")
    return rules


def read_source(source: str) -> bytes:
    """读取 UTF-8 YAML；远程请求设定超时和大小上限，失败时不覆盖旧输出。"""
    if source.startswith("https://"):
        request = Request(source, headers={"User-Agent": "3xui-clash-converter/1.0"})
        with urlopen(request, timeout=30) as response:
            if urlparse(response.url).scheme != "https":
                raise ValueError("远程地址重定向后必须仍为 HTTPS")
            raw = response.read(MAX_BYTES + 1)
    else:
        if "://" in source:
            raise ValueError("远程输入只支持 HTTPS 地址")
        with Path(source).open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("输入超过 2 MiB 限制")
    return raw


def validate_routing(document: dict) -> None:
    """检查面板的主要格式约束，并额外拒绝策略组循环引用。

    远程版的 PROXY 由 3x-ui 注入；内联版只定义动态组，不写入用户节点。
    本校验不下载规则集，也不替代 Mihomo 对具体规则内容的校验。
    """
    if not isinstance(document, dict) or set(document) != {
        "proxy-groups", "rule-providers", "rules"
    }:
        raise ValueError("输出必须只包含 proxy-groups、rule-providers、rules")
    groups = document["proxy-groups"]
    providers = document["rule-providers"]
    rules = document["rules"]
    if not isinstance(groups, list) or not isinstance(providers, dict):
        raise ValueError("策略组必须为列表，规则提供者必须为映射")
    names = set()
    for group in groups:
        if not isinstance(group, dict):
            raise ValueError("策略组必须为映射")
        name = group.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("策略组名称必须为非空字符串")
        if name != name.strip() or name in names or name in BUILTINS:
            raise ValueError(f"策略组名称重复、含首尾空格或占用保留名称：{name}")
        if name == "PROXY" and group != {
            "name": "PROXY", "type": "select", "include-all-proxies": True
        }:
            raise ValueError("显式 PROXY 组必须通过 include-all-proxies 动态引用面板节点")
        if group.get("type") not in {"select", "url-test"} or "use" in group:
            raise ValueError(f"转换后策略组必须为 select/url-test 且不能含 use：{name}")
        if group.get("type") == "url-test":
            if not isinstance(group.get("url"), str) or not group["url"]:
                raise ValueError(f"测速组缺少测试 URL：{name}")
            if not isinstance(group.get("interval"), int) or group["interval"] <= 0:
                raise ValueError(f"测速组必须有正整数 interval：{name}")
        names.add(name)
    known = names | BUILTINS | {"PROXY"}
    edges = {}
    for group in groups:
        if group["name"] == "PROXY":
            edges["PROXY"] = []
            continue
        refs = group.get("proxies", [])
        if not isinstance(refs, list) or (not refs and group.get("include-all-proxies") is not True):
            raise ValueError(f"策略组没有可用候选项：{group['name']}")
        for ref in refs:
            if not isinstance(ref, str) or ref not in known:
                raise ValueError(f"策略组引用未知节点或组：{ref}")
        edges[group["name"]] = [ref for ref in refs if ref in names]

    # 使用递归栈识别间接循环，避免生成能过格式检查却无法正常运行的配置。
    visited = set()
    active = set()

    def visit(name: str) -> None:
        if name in active:
            raise ValueError(f"策略组存在循环引用：{name}")
        if name in visited:
            return
        active.add(name)
        for ref in edges[name]:
            visit(ref)
        active.remove(name)
        visited.add(name)

    for name in names:
        visit(name)
    for name, provider in providers.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(provider, dict):
            raise ValueError("规则提供者必须有非空名称和映射配置")
        via = provider.get("proxy")
        if via is not None and (not isinstance(via, str) or via not in known):
            raise ValueError(f"规则提供者引用未知代理：{via}")
    if not isinstance(rules, list) or not rules:
        raise ValueError("rules 必须为非空列表")
    for rule in rules:
        if not isinstance(rule, str) or not rule.strip():
            raise ValueError("规则必须为非空字符串")
        parts = [part.strip() for part in rule.split(",")]
        if len(parts) < 2:
            raise ValueError(f"无效规则：{rule}")
        if parts[0].upper() == "RULE-SET":
            if len(parts) < 3 or parts[1] not in providers:
                raise ValueError(f"规则引用未定义的规则提供者：{rule}")
        target_index = len(parts) - 1
        while target_index >= 1 and parts[target_index].lower() in {"no-resolve", "src"}:
            target_index -= 1
        if target_index < 1 or parts[target_index] not in known:
            raise ValueError(f"规则引用未知目标：{rule}")


def convert(document: dict, inline: bool = False) -> tuple[dict, list[str]]:
    """保留非地区策略组及独立节点选择能力，移除依赖地区筛选的组。

    使用 Mihomo 的 include-all-proxies 动态收集面板节点，代替远程片段
    禁止使用的 use。带 filter 的提供者测速组视为地区组；无地区过滤
    的自动测速组保留原参数，对实际节点测速，不能只测 PROXY 单个组。
    """
    if not isinstance(document, dict):
        raise ValueError("输入 YAML 顶层必须为映射")
    original_groups = document.get("proxy-groups", [])
    if not isinstance(original_groups, list):
        raise ValueError("输入 proxy-groups 必须为列表")
    names = []
    collapsed = []
    for group in original_groups:
        if not isinstance(group, dict) or not isinstance(group.get("name"), str):
            raise ValueError("输入策略组必须有字符串名称")
        name = group["name"]
        if name == "PROXY":
            raise ValueError("输入模板占用了面板保留组名 PROXY")
        if not name.strip() or name != name.strip() or name in names:
            raise ValueError(f"输入策略组名称为空、重复或含首尾空格：{name}")
        names.append(name)
        if group.get("type") in {"url-test", "fallback", "load-balance"} and group.get("use") and group.get("filter"):
            collapsed.append(name)
        elif group.get("type") not in {"select", "url-test"}:
            raise ValueError(f"不支持转换此策略组类型，请人工检查：{name}")
    groups = []
    for original in original_groups:
        if original["name"] in collapsed:
            continue
        refs = original.get("proxies", [])
        if not isinstance(refs, list):
            raise ValueError(f"输入 proxies 必须为列表：{original['name']}")
        mapped = []
        for ref in refs:
            if not isinstance(ref, str):
                raise ValueError("策略组候选项必须为字符串")
            # 地区分组属于本次明确排除的部分，其余候选组保持原顺序。
            if ref not in collapsed and ref not in mapped:
                mapped.append(ref)
        group = {"name": original["name"], "type": original["type"]}
        if mapped:
            group["proxies"] = mapped
        # 每个业务组分别收集实际节点，可以独立选择，避免共用 PROXY 选择状态。
        if original.get("use"):
            group["include-all-proxies"] = True
        # 自动选择保留测试地址、周期和容差，业务 select 不添加无关测速参数。
        if original["type"] == "url-test":
            for key in ("url", "interval", "tolerance", "lazy", "timeout", "max-failed-times", "expected-status"):
                if key in original:
                    group[key] = copy.deepcopy(original[key])
        groups.append(group)

    rules = copy.deepcopy(document.get("rules", []))
    if not isinstance(rules, list):
        raise ValueError("输入 rules 必须为列表")
    for index, rule in enumerate(rules):
        if not isinstance(rule, str):
            raise ValueError("输入规则必须为字符串")
        parts = rule.split(",")
        target_index = len(parts) - 1
        while target_index >= 1 and parts[target_index].strip().lower() in {"no-resolve", "src"}:
            target_index -= 1
        if target_index >= 1 and parts[target_index].strip() in collapsed:
            parts[target_index] = "PROXY"
            rules[index] = ",".join(parts)
    providers = copy.deepcopy(document.get("rule-providers", {}))
    if not isinstance(providers, dict):
        raise ValueError("输入 rule-providers 必须为映射")
    for provider in providers.values():
        if isinstance(provider, dict) and provider.get("proxy") in collapsed:
            provider["proxy"] = "PROXY"
    result = {"proxy-groups": groups, "rule-providers": providers, "rules": rules}
    # 内联模式会替换整个 proxy-groups，必须主动重新建立动态节点选择组。
    # 远程模式按名称合并，默认保留面板原有的 PROXY 及其候选节点顺序。
    if inline:
        groups.insert(0, {"name": "PROXY", "type": "select", "include-all-proxies": True})
    validate_routing(result)
    return result, collapsed


def write_atomic(path: Path, content: str) -> None:
    """校验全部成功后原子替换目标，避免写入中断破坏已有可用配置。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def build_output(
    raw: bytes, inline: bool = False, custom_rules: list[str] | None = None
) -> tuple[str, dict, list[str]]:
    """从同一份源数据生成确定性的输出；无时间戳，避免无变化的自动提交。"""
    result, collapsed = convert(yaml.safe_load(raw.decode("utf-8-sig")), inline=inline)
    # 自定义规则优先，保留用户填写的顺序；不改动上游快照。
    if custom_rules is not None:
        if not isinstance(custom_rules, list):
            raise ValueError("自定义 rules 必须为列表")
        result["rules"] = custom_rules + result["rules"]
        validate_routing(result)
    header = (
        "# 3x-ui Clash/Mihomo 全局路由片段；请与面板生成的订阅合并使用。\n"
        "# 节点由面板提供；保留业务独立选点和自动测速，移除地区分组。\n"
        f"# 输入 SHA256: {hashlib.sha256(raw).hexdigest()}\n"
    )
    content = header + yaml.safe_dump(result, allow_unicode=True, sort_keys=False, width=120)
    if len(content.encode("utf-8")) > MAX_BYTES:
        raise ValueError("输出超过 3x-ui 远程路由的 2 MiB 限制")
    return content, result, collapsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=DEFAULT_SOURCE, help="HTTPS 地址或本地 YAML 路径")
    parser.add_argument("--output", type=Path, help="输出路径；默认按远程/内联模式选择文件名")
    parser.add_argument("--inline", action="store_true", help="生成可直接粘贴到面板的内联版本")
    parser.add_argument("--custom-rules", type=Path, help="自定义规则路径；默认读取项目根目录 custom_rules.yaml")
    args = parser.parse_args()
    if args.output is None:
        args.output = Path("Custom_Clash_3xui_inline.yaml" if args.inline else "Custom_Clash_3xui.yaml")
    try:
        custom_rules = read_custom_rules(
            args.custom_rules if args.custom_rules is not None else DEFAULT_CUSTOM_RULES,
            optional=args.custom_rules is None,
        )
        raw = read_source(args.input)
        content, result, collapsed = build_output(raw, inline=args.inline, custom_rules=custom_rules)
        write_atomic(args.output, content)
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"转换失败：{error}", file=sys.stderr)
        return 1
    print(f"已生成：{args.output.resolve()}")
    print(f"策略组 {len(result['proxy-groups'])}；规则集 {len(result['rule-providers'])}；规则 {len(result['rules'])}")
    print(f"已移除 {len(collapsed)} 个地区组；自动测速及业务独立选点已保留")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
