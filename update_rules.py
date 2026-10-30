"""一次下载，同时更新原始快照和两份 3x-ui 路由文件。

运行方法：python update_rules.py
离线更新：python update_rules.py --input sources/Custom_Clash.yaml
只读校验：python update_rules.py --input sources/Custom_Clash.yaml --check

程序不会执行 Git 命令；自动提交由 GitHub Actions 工作流负责。
"""

import argparse
from pathlib import Path
import sys

import yaml

from convert_clash import DEFAULT_SOURCE, build_output, read_source, write_atomic


ROOT = Path(__file__).resolve().parent


def prepare_files(raw: bytes) -> dict[str, str]:
    """两种模式都转换并校验成功后才允许写盘，防止半成品被发布。

    快照采用 UTF-8，保留源文件的换行；SHA256 对应下载到的原始字节。
    """
    remote, _, _ = build_output(raw)
    inline, _, _ = build_output(raw, inline=True)
    return {
        "sources/Custom_Clash.yaml": raw.decode("utf-8"),
        "Custom_Clash_3xui.yaml": remote,
        "Custom_Clash_3xui_inline.yaml": inline,
    }


def update_files(files: dict[str, str], root: Path, check: bool = False) -> list[str]:
    """比较实际字节，仅写入变化文件；check 模式完全不修改文件。

    所有内容已在 prepare_files 校验。单文件原子替换；意外磁盘错误时，
    工作流会停止且不会提交，因此不会发布未完成的这一批更新。
    """
    changed = []
    for name, content in files.items():
        path = root / name
        expected = content.encode("utf-8")
        if not path.exists() or path.read_bytes() != expected:
            changed.append(name)
    if check:
        return changed
    for name in changed:
        write_atomic(root / name, files[name])
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=DEFAULT_SOURCE, help="HTTPS 地址或本地 YAML 路径")
    parser.add_argument("--check", action="store_true", help="只读检查；存在需更新文件时返回 1")
    args = parser.parse_args()
    try:
        files = prepare_files(read_source(args.input))
        changed = update_files(files, ROOT, check=args.check)
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"更新失败：{error}", file=sys.stderr)
        return 1
    if not changed:
        print("源快照与两份规则均为最新，无需更新。")
        return 0
    if args.check:
        print("以下文件与转换结果不一致：", file=sys.stderr)
    else:
        print("已更新以下文件：")
    for name in changed:
        print(name)
    return 1 if args.check else 0


if __name__ == "__main__":
    raise SystemExit(main())
