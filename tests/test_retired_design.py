"""在隔离 HOME 里部署两次，覆盖共享、旧 Codex 和第三方入口。"""

import os
import subprocess
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("owner", ["shared", "checkout", "foreign", "directory"])
def test_retired_design(tmp_path, owner):
    home = tmp_path / "home"
    root = home / ".agents/skills"
    legacy = home / ".codex/skills"
    targets = {
        "shared": home / ".coding-agent/skills/design",
        "checkout": REPO / "skills/design",
        "foreign": tmp_path / "vendor/skills/design",
    }
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    (vendor / "install.sh").touch()
    (vendor / "GLOBAL_AGENTS.md").touch()
    for parent in (root, legacy):
        parent.mkdir(parents=True)
        link = parent / "design"
        if owner == "directory":
            link.mkdir()
        else:
            link.symlink_to(targets[owner])
    for _ in range(2):
        subprocess.run(
            ["bash", "-c", 'source "$1/install.sh"; deploy_skills "$2" "$3"',
             "test", str(REPO), str(root), str(legacy)],
            env={"HOME": str(home), "PATH": os.environ["PATH"], "CCG_INSTALL_LIB_ONLY": "1"},
            check=True, capture_output=True,
        )
        for link in (root / "design", legacy / "design"):
            if owner == "foreign":
                assert link.readlink() == targets[owner]
            elif owner == "directory":
                assert link.is_dir() and not link.is_symlink()
            else:
                assert not os.path.lexists(link)
        assert (root / "quick").is_symlink()
