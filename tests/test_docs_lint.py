"""验证文档产出闭集的机械检查（scripts/docs_lint.py）。"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "docs_lint.py"

GOOD_ROUND = """# 示例轮次

> 读者：接手这条分支的人 · 这轮要解决什么
> 来源：[#12 示例](https://example.com/issues/12)
> 完成标准：`pytest` 通过。
"""

GOOD_ADR = """# 0001 示例决策

> 读者：要改这块的人 · 为什么不是另一条路

## 背景

历史原因。

## 决策

选 A 不选 B。

## 后果

代价是 C。
"""

GOOD_DESIGN = """# 示例主题

> 读者：要落地这个方案的人 · 当初为什么这么定
> 状态：讨论中（2026-11-19）

## 目标与非目标
"""


def load_module():
    spec = importlib.util.spec_from_file_location("docs_lint", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_round_file_passes(tmp_path):
    write(tmp_path, "docs/70-示例.md", GOOD_ROUND)
    assert load_module().check(tmp_path) == []


def test_round_file_missing_reader(tmp_path):
    write(tmp_path, "docs/70-示例.md", GOOD_ROUND.replace("> 读者：接手这条分支的人 · 这轮要解决什么\n", ""))
    problems = load_module().check(tmp_path)
    assert len(problems) == 1
    assert "读者" in problems[0]


def test_round_file_missing_source_and_done(tmp_path):
    write(tmp_path, "docs/70-示例.md", "# 示例轮次\n\n> 读者：x · y\n")
    problems = load_module().check(tmp_path)
    assert any("来源" in p for p in problems)
    assert any("完成标准" in p for p in problems)


def test_round_file_too_long(tmp_path):
    body = GOOD_ROUND + "\n" + "\n".join(f"补充 {i}" for i in range(20)) + "\n"
    write(tmp_path, "docs/70-示例.md", body)
    problems = load_module().check(tmp_path)
    assert any("15 行" in p for p in problems)


def test_adr_passes(tmp_path):
    write(tmp_path, "docs/adr/0001-示例.md", GOOD_ADR)
    assert load_module().check(tmp_path) == []


def test_adr_bad_filename(tmp_path):
    write(tmp_path, "docs/adr/1-示例.md", GOOD_ADR)
    problems = load_module().check(tmp_path)
    assert any("四位" in p for p in problems)


def test_adr_missing_section(tmp_path):
    write(tmp_path, "docs/adr/0001-示例.md", GOOD_ADR.replace("## 后果", "## 影响"))
    problems = load_module().check(tmp_path)
    assert any("后果" in p for p in problems)


def test_adr_too_long(tmp_path):
    body = GOOD_ADR + "\n" + "\n".join(f"补充 {i}" for i in range(40)) + "\n"
    write(tmp_path, "docs/adr/0001-示例.md", body)
    problems = load_module().check(tmp_path)
    assert any("40 行" in p for p in problems)


def test_design_passes(tmp_path):
    write(tmp_path, "docs/design/示例.md", GOOD_DESIGN)
    assert load_module().check(tmp_path) == []


def test_design_bad_status(tmp_path):
    write(tmp_path, "docs/design/示例.md", GOOD_DESIGN.replace("讨论中", "草稿中"))
    problems = load_module().check(tmp_path)
    assert any("状态" in p for p in problems)


def test_design_missing_status(tmp_path):
    write(tmp_path, "docs/design/示例.md", GOOD_DESIGN.replace("> 状态：讨论中（2026-11-19）\n", ""))
    problems = load_module().check(tmp_path)
    assert any("状态" in p for p in problems)


def test_design_discussion_log_is_exempt_from_status(tmp_path):
    """讨论历史文件只需出生登记，不要求状态行。"""
    write(tmp_path, "docs/design/示例-discussion.md", "# 示例 · 讨论记录\n\n> 读者：续聊的人 · 上次讨论到哪\n")
    assert load_module().check(tmp_path) == []


def test_legacy_round_dirs_are_ignored(tmp_path):
    """存量 docs/<N>-*/ 目录不进入新规则范围。"""
    write(tmp_path, "docs/42-旧轮次/PROMPT.md", "# 没有读者行的旧文档\n")
    write(tmp_path, "docs/42-旧轮次/SUMMARY.md", "# 旧总结\n")
    assert load_module().check(tmp_path) == []


def test_cli_reports_path_and_exit_code(tmp_path):
    write(tmp_path, "docs/70-示例.md", "# 无读者行\n")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "docs/70-示例.md" in result.stdout
    assert "读者" in result.stdout


def test_cli_clean_exit_code(tmp_path):
    write(tmp_path, "docs/70-示例.md", GOOD_ROUND)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


def test_this_repo_is_clean():
    """仓库自身的文档持续满足规则。"""
    assert load_module().check(REPO) == []


def pad(text, total):
    lines = text.splitlines()
    assert total >= len(lines)
    return "\n".join(lines + [f"- 备注 {i}" for i in range(total - len(lines))]) + "\n"


def test_round_exactly_max_lines_passes(tmp_path):
    body = pad(GOOD_ROUND, 15)
    assert len(body.splitlines()) == 15
    write(tmp_path, "docs/70-示例.md", body)
    assert load_module().check(tmp_path) == []


def test_adr_exactly_max_lines_passes(tmp_path):
    body = pad(GOOD_ADR, 40)
    assert len(body.splitlines()) == 40
    write(tmp_path, "docs/adr/0001-示例.md", body)
    assert load_module().check(tmp_path) == []


@pytest.mark.parametrize("status", ["讨论中", "已定稿", "已搁置"])
def test_design_accepts_all_statuses(tmp_path, status):
    write(tmp_path, "docs/design/示例.md", GOOD_DESIGN.replace("讨论中", status))
    assert load_module().check(tmp_path) == []


def test_duplicate_adr_numbers_are_reported(tmp_path):
    write(tmp_path, "docs/adr/0002-a.md", GOOD_ADR.replace("0001", "0002"))
    write(tmp_path, "docs/adr/0002-b.md", GOOD_ADR.replace("0001", "0002"))
    problems = load_module().check(tmp_path)
    assert any("重复" in p for p in problems)


def test_frozen_devtree_is_allowed(tmp_path):
    """冻结的历史快照不适用新形态规则。"""
    write(tmp_path, "docs/DEVTREE.md", "# 开发树\n")
    assert load_module().check(tmp_path) == []


def test_stray_top_level_doc_is_reported(tmp_path):
    write(tmp_path, "docs/notes.md", "# 随手记\n\n> 读者：我 · 备忘\n")
    problems = load_module().check(tmp_path)
    assert any("闭集" in p for p in problems)


def test_nested_adr_uses_adr_rules(tmp_path):
    """嵌套 ADR 也走 ADR 规则；把 rglob 退化成 glob 时这条会红。"""
    write(
        tmp_path,
        "docs/adr/sub/0003-a.md",
        GOOD_ADR.replace("0001", "0003").replace("## 后果", "## 影响"),
    )
    problems = load_module().check(tmp_path)
    assert any("后果" in p for p in problems)


def test_cli_positional_file(tmp_path):
    """FILE 模式只查给定文件：故意选全库扫描不覆盖的存量目录，删掉该分支这条会红。"""
    bad = write(tmp_path, "docs/42-旧轮次/PLAN.md", "# 无读者行\n")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path), str(bad)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "读者" in result.stdout


def test_cli_file_mode_counts_only_given_files(tmp_path):
    write(tmp_path, "docs/70-示例.md", GOOD_ROUND)
    adr = write(tmp_path, "docs/adr/0001-示例.md", GOOD_ADR)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path), str(adr)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "1 份文档通过" in result.stdout


def test_cli_missing_file_reports_instead_of_traceback(tmp_path):
    write(tmp_path, "docs/70-示例.md", GOOD_ROUND)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path), str(tmp_path / "docs/nope.md")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "文件不存在" in result.stdout
    assert "Traceback" not in result.stderr


def test_missing_docs_dir_reports_instead_of_passing(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path / "不存在")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "docs/" in result.stdout


def test_adr_requires_slug_and_md_suffix(tmp_path):
    write(tmp_path, "docs/adr/0001-.md", GOOD_ADR)
    problems = load_module().check(tmp_path)
    assert any("四位数字" in p for p in problems)


def test_design_assets_are_ignored(tmp_path):
    write(tmp_path, "docs/design/assets/flow.md", "# 流程图源\n")
    assert load_module().check(tmp_path) == []


def test_nested_stray_doc_is_reported(tmp_path):
    write(tmp_path, "docs/misc/notes.md", "# 笔记\n")
    problems = load_module().check(tmp_path)
    assert any("闭集" in p for p in problems)
