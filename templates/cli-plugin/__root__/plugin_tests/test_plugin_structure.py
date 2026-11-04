"""校验本地 CLI 插件的清单、skill 元数据与双端入口；不执行被包装 CLI。"""

import json
import re
import shutil
from pathlib import Path

import pytest
import yaml


class PluginLayout:
    @staticmethod
    def validate(root: Path) -> None:
        root = root.resolve()
        market = json.loads((root / ".claude-plugin/marketplace.json").read_text())
        assert market["name"].strip()
        assert market["owner"]["name"].strip()
        assert market["plugins"], "marketplace 不能没有插件"
        names = set()
        for entry in market["plugins"]:
            assert entry["name"] not in names, "插件名不能重复"
            names.add(entry["name"])
            source = entry["source"]
            assert source.startswith("./"), "此脚手架只校验仓内相对 source"
            plugin = (root / source).resolve()
            assert plugin != root and plugin.is_relative_to(root), "source 必须在仓内"
            manifest = json.loads((plugin / ".claude-plugin/plugin.json").read_text())
            assert manifest["name"] == entry["name"], "两份清单中的插件名必须一致"
            assert not (plugin / ".claude-plugin/skills").exists(), "skills 不能放在清单目录"
            skills = sorted((plugin / "skills").iterdir())
            assert skills, "插件至少应有一个 skill"
            for skill in skills:
                assert skill.is_dir(), "skills 下每个条目应是 skill 目录"
                text = (skill / "SKILL.md").read_text(encoding="utf-8")
                parts = text.split("---", 2)
                assert len(parts) == 3 and not parts[0].strip(), "缺少 frontmatter"
                meta = yaml.safe_load(parts[1])
                assert isinstance(meta, dict), "frontmatter 必须是映射"
                assert meta.get("name") == skill.name, "skill 名应与目录一致"
                assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", meta["name"])
                assert isinstance(meta.get("description"), str) and meta["description"].strip()
                assert parts[2].strip(), "skill 正文不能为空"
                codex = root / ".agents/skills" / skill.name
                assert codex.is_symlink(), "Codex 入口应链接到同一份 skill"
                assert codex.resolve() == skill.resolve(), "Codex 入口断链或指向其他正文"


ROOT = Path(__file__).resolve().parents[1]


def test_plugin_structure() -> None:
    PluginLayout.validate(ROOT)


@pytest.mark.parametrize("damage", ["json", "source", "name", "description", "missing", "link"])
def test_reject_broken_layout(tmp_path: Path, damage: str) -> None:
    root = tmp_path / "project"
    root.mkdir()
    for path in [".claude-plugin", "plugin", ".agents"]:
        shutil.copytree(ROOT / path, root / path, symlinks=True)
    # 先证明对照样本有效，避免把 fixture 自身的失败误判为检出变异。
    PluginLayout.validate(root)
    market_path = root / ".claude-plugin/marketplace.json"
    market = json.loads(market_path.read_text())
    skill = root / "plugin/skills/example-status/SKILL.md"
    if damage == "json":
        market_path.write_text("{")
    elif damage == "source":
        market["plugins"][0]["source"] = "../outside"
        market_path.write_text(json.dumps(market))
    elif damage == "name":
        market["plugins"][0]["name"] = "mismatch"
        market_path.write_text(json.dumps(market))
    elif damage == "description":
        skill.write_text("---\nname: example-status\n---\n正文\n", encoding="utf-8")
    elif damage == "missing":
        skill.unlink()
    elif damage == "link":
        (root / ".agents/skills/example-status").unlink()
    with pytest.raises((AssertionError, ValueError, KeyError, OSError, TypeError)):
        PluginLayout.validate(root)
