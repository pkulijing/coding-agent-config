#!/usr/bin/env python3
"""docs_lint.py — 文档产出闭集的机械检查。

本仓自第 71 轮起使用 docs/<N>-<主题>/PLAN.md。检查批准版的读者、来源、
目标、关键决策、实施提纲与验收，并报告同轮多出的 Markdown。历史轮次目录、
旧单文件、设计、ADR 与冻结的开发树继续使用原有兼容规则。

用法：

    python3 scripts/docs_lint.py [--root DIR] [FILE ...]

退出码：0 全部通过；1 有问题、有文件不存在，或没有可检查的 `docs/` 目录。
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

ROUND_NAME_RE = re.compile(r"^\d+-.*\.md$")
ROUND_DIR_RE = re.compile(r"^(\d+)-")
# 本仓启用新格式的首轮；编号属于本仓历史，不作为共享技能的开轮条件。
FIRST_PLAN_ROUND = 71
PLAN_SECTIONS = ("目标", "关键决策", "实施提纲", "验收")
ROUND_MAX_LINES = 15
ADR_NAME_RE = re.compile(r"^(\d{4})-.+\.md$")
ADR_MAX_LINES = 40
ADR_SECTIONS = ("背景", "决策", "后果")
DESIGN_STATUSES = ("讨论中", "已定稿", "已搁置")
READER_PREFIX = "> 读者："
SOURCE_PREFIX = "> 来源："
DONE_PREFIX = "> 完成标准："
STATUS_PREFIX = "> 状态："

# 设计目录下的资产（配图、Mermaid 源等）不参与文档形状检查。
ASSET_DIR = "assets"


def _has_line(lines, prefix):
    return any(line.startswith(prefix) for line in lines)


def _has_heading(text, name):
    return re.search(r"^##\s*" + re.escape(name), text, re.M) is not None


def _status_value(line):
    value = line[len(STATUS_PREFIX):].strip()
    return re.split(r"[（(]", value, maxsplit=1)[0].strip()


def _display(path, root):
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _kind(path, root):
    """按相对路径判定文档类型；嵌套目录也按祖先目录识别。"""
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        parts = path.parts
    if parts and parts[0] == "docs":
        parts = parts[1:]
    if not parts:
        return None
    match = ROUND_DIR_RE.match(parts[0])
    if match:
        if int(match[1]) >= FIRST_PLAN_ROUND:
            return "plan" if parts[1:] == ("PLAN.md",) else "extra"
        if len(parts) > 1:
            return "legacy"
        if ROUND_NAME_RE.fullmatch(path.name):
            return "round"
    if parts == ("DEVTREE.md",) or parts[:2] == ("design", ASSET_DIR):
        return "legacy"
    if parts[0] in ("adr", "design") and len(parts) > 1:
        return parts[0]
    return None


def check_file(path, root):
    """返回该文件的问题列表，空列表表示通过。"""
    rel = _display(path, root)
    kind = _kind(path, root)
    if kind in (None, "extra"):
        return [f"{rel}: 不在文档闭集内；新轮次只允许 docs/<N>-<主题>/PLAN.md"]
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    problems = []

    if not _has_line(lines, READER_PREFIX):
        problems.append(f"{rel}: 缺少「{READER_PREFIX}<谁> · <什么问题>」行")

    if kind == "plan":
        if not _has_line(lines, SOURCE_PREFIX):
            problems.append(f"{rel}: 缺少来源")
        for section in PLAN_SECTIONS:
            if f"## {section}" not in lines:
                problems.append(f"{rel}: 缺少「## {section}」段")
    elif kind == "adr":
        if not ADR_NAME_RE.match(path.name):
            problems.append(f"{rel}: ADR 文件名须为四位数字加短名，形如 0001-xxx.md")
        for name in ADR_SECTIONS:
            if not _has_heading(text, name):
                problems.append(f"{rel}: ADR 缺少「## {name}」段")
        if len(lines) > ADR_MAX_LINES:
            problems.append(f"{rel}: ADR 超过 {ADR_MAX_LINES} 行（当前 {len(lines)} 行）")
    elif kind == "design" and not path.name.endswith("-discussion.md"):
        status_lines = [line for line in lines if line.startswith(STATUS_PREFIX)]
        if not status_lines:
            problems.append(f"{rel}: 缺少「{STATUS_PREFIX}<状态>」行")
        else:
            value = _status_value(status_lines[0])
            if value not in DESIGN_STATUSES:
                problems.append(
                    f"{rel}: 状态「{value}」不在 {' / '.join(DESIGN_STATUSES)} 之内"
                )
    elif kind == "round":
        if not _has_line(lines, SOURCE_PREFIX):
            problems.append(f"{rel}: 缺少「{SOURCE_PREFIX}…」行")
        if not _has_line(lines, DONE_PREFIX):
            problems.append(f"{rel}: 缺少「{DONE_PREFIX}…」行")
        if len(lines) > ROUND_MAX_LINES:
            problems.append(f"{rel}: 轮次记录超过 {ROUND_MAX_LINES} 行（当前 {len(lines)} 行）")

    return problems


def collect(root):
    """收集新形态文档；存量轮次目录、设计资产与冻结快照不在范围内。"""
    docs = Path(root) / "docs"
    if not docs.is_dir():
        return []

    return [p for p in sorted(docs.rglob("*.md")) if _kind(p, root) != "legacy"]


def check(root):
    """全库检查也能发现只有其他文件、尚未创建 PLAN.md 的新轮次。"""
    root = Path(root)
    docs = root / "docs"
    problems = []
    if not docs.is_dir():
        return problems
    for directory in sorted(docs.iterdir()):
        match = ROUND_DIR_RE.match(directory.name)
        if directory.is_dir() and match and int(match[1]) >= FIRST_PLAN_ROUND:
            if not (directory / "PLAN.md").is_file():
                problems.append(f"{_display(directory, root)}: 缺少 PLAN.md")

    adr_dir = docs / "adr"
    if adr_dir.is_dir():
        numbers = [
            ADR_NAME_RE.match(path.name).group(1)
            for path in adr_dir.rglob("*.md")
            if ADR_NAME_RE.match(path.name)
        ]
        for number, count in sorted(Counter(numbers).items()):
            if count > 1:
                problems.append(f"docs/adr/: ADR 编号 {number} 重复 {count} 次，编号必须唯一")

    for path in collect(root):
        problems.extend(check_file(path, root))
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="新形态文档的形状检查")
    parser.add_argument("--root", default=".", help="仓库根，默认当前目录")
    parser.add_argument("files", nargs="*", help="只查指定文件，默认扫全库")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    docs = root / "docs"
    if not docs.is_dir():
        print(f"docs_lint: {root} 下没有 docs/ 目录，无法检查（确认 --root 是否指对）")
        return 1

    if args.files:
        targets = [Path(item).resolve() for item in args.files]
        problems = []
        for path in targets:
            if not path.is_file():
                problems.append(f"{path}: 文件不存在")
        targets = [path for path in targets if path.is_file()]
        for path in targets:
            problems.extend(check_file(path, root))
    else:
        problems = check(root)
        targets = collect(root)

    if problems:
        for problem in problems:
            print(problem)
        return 1
    print(f"docs_lint: {len(targets)} 份文档通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
