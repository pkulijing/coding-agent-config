"""将活跃的 shell 隔离沙盘测试与 helper 自测纳入统一的 pytest 入口。"""

from pathlib import Path
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]

SHELL_SUITES = [
    "tests/test_unlink_legacy.sh",
    "tests/test_worktree_guard.sh",
    ".github/scripts/ff-merge.test.sh",
]


@pytest.mark.parametrize("relative_path", SHELL_SUITES)
def test_shell_sandbox_suite(relative_path):
    script = REPO / relative_path
    result = subprocess.run(
        ["bash", str(script)],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"{relative_path} failed:\n{result.stdout}\n{result.stderr}"


def test_platform_issue_self_test():
    script = REPO / "scripts/platform_issue.py"
    result = subprocess.run(
        [sys.executable, str(script), "--self-test"],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"platform_issue --self-test failed:\n{result.stdout}\n{result.stderr}"
