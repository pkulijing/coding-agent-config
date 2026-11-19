#!/usr/bin/env python3
"""docs_lint.py — 文档产出闭集的机械检查。

范围只覆盖新形态文档，存量 `docs/<N>-<中文描述>/` 历史目录不在其内：

    docs/<N>-<中文描述>.md   轮次记录
    docs/adr/<NNNN>-*.md     决策记录（ADR）
    docs/design/*.md         方案（其下 `assets/` 视为资产，不做形状检查）

规则：

    L1  `docs/` 下只允许上述三种形态；`docs/DEVTREE.md` 是冻结的历史快照，保留为白名单
    L2  同一目录内 ADR 编号不得重复
    R1  每份文件有一行 `> 读者：<谁> · <什么问题>`（出生登记）
    R2  轮次记录 ≤15 行，且含 `> 来源：` 与 `> 完成标准：`
    R3  ADR 文件名 `<4 位数字>-<slug>.md`，含 `## 背景` / `## 决策` / `## 后果`，≤40 行
    R4  方案文件含 `> 状态：`，取值 `讨论中` / `已定稿` / `已搁置`；`-discussion.md` 只要求 R1

规则只查形状，不查内容价值：写一句敷衍的「读者」骗过脚本是允许的，脚本的存在
只是让人在出生时被迫回答一次那个问题。

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
ROUND_DIR_RE = re.compile(r"^\d+-")
ROUND_MAX_LINES = 15
ADR_NAME_RE = re.compile(r"^(\d{4})-.+\.md$")
ADR_MAX_LINES = 40
ADR_SECTIONS = ("背景", "决策", "后果")
DESIGN_STATUSES = ("讨论中", "已定稿", "已搁置")
READER_PREFIX = "> 读者："
SOURCE_PREFIX = "> 来源："
DONE_PREFIX = "> 完成标准："
STATUS_PREFIX = "> 状态："

# 冻结的历史快照：开发树索引，按 ADR 0001 保持原样，不再更新也不再要求新形态。
LAYOUT_ALLOWLIST = {"DEVTREE.md"}
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
    if ASSET_DIR in parts:
        return None
    if "adr" in parts:
        return "adr"
    if "design" in parts:
        return "design"
    if ROUND_NAME_RE.match(path.name):
        return "round"
    return None


def _is_legacy(path, docs):
    """存量轮次目录 `<N>-*/`：整棵子树豁免新规则。"""
    try:
        parts = path.relative_to(docs).parts
    except ValueError:
        return False
    return len(parts) > 1 and ROUND_DIR_RE.match(parts[0]) is not None


def check_file(path, root):
    """返回该文件的问题列表，空列表表示通过。"""
    rel = _display(path, root)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    problems = []

    if not _has_line(lines, READER_PREFIX):
        problems.append(f"{rel}: 缺少「{READER_PREFIX}<谁> · <什么问题>」行")

    kind = _kind(path, root)

    if kind == "adr":
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

    targets = []
    for path in sorted(docs.rglob("*.md")):
        if path.name in LAYOUT_ALLOWLIST or _is_legacy(path, docs):
            continue
        if _kind(path, root) in ("adr", "design") or (
            path.parent == docs and ROUND_NAME_RE.match(path.name)
        ):
            targets.append(path)
    return targets


def check(root):
    """返回全库问题列表；空列表表示通过。"""
    root = Path(root)
    docs = root / "docs"
    problems = []

    if not docs.is_dir():
        return problems

    for path in sorted(docs.rglob("*.md")):
        if path.name in LAYOUT_ALLOWLIST or _is_legacy(path, docs):
            continue
        if ASSET_DIR in path.relative_to(docs).parts:
            continue
        if _kind(path, root) in ("adr", "design"):
            continue
        if path.parent == docs and ROUND_NAME_RE.match(path.name):
            continue
        problems.append(
            f"{_display(path, root)}: 不在文档闭集内；轮次记录放 docs/<N>-<中文描述>.md，"
            "其他文档放 docs/adr/ 或 docs/design/"
        )

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
