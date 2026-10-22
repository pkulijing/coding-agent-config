"""共享资源引用与项目指令正文迁移的预算回归测试。"""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/context_budget.py"
SPEC = importlib.util.spec_from_file_location("context_budget_migration", SCRIPT)
cb = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cb)


class TestContextMigration(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "GLOBAL_AGENTS.md").write_text("全局规则", encoding="utf-8")

    def write(self, relative, text):
        destination = self.root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")

    def test_agents_body_is_counted_once_without_compatibility_wrapper(self):
        self.write("AGENTS.md", "项目规则正文")
        self.write("CLAUDE.md", "@AGENTS.md\n")
        report = cb.measure(self.root)
        self.assertEqual({entry.path for entry in report.entries},
                         {"GLOBAL_AGENTS.md", "AGENTS.md"})
        self.assertEqual(report.resident_chars, len("全局规则项目规则正文"))
        self.assertTrue(all(entry.category == "resident" for entry in report.entries))

    def test_legacy_project_keeps_claude_body(self):
        self.write("CLAUDE.md", "原有规则")
        self.assertEqual(cb.instruction_paths(self.root), ["GLOBAL_AGENTS.md", "CLAUDE.md"])

    def test_agents_only_project_is_counted(self):
        self.write("AGENTS.md", "项目规则")
        self.assertEqual(cb.instruction_paths(self.root), ["GLOBAL_AGENTS.md", "AGENTS.md"])

    def test_shared_resource_prefixes_resolve_to_repository_files(self):
        expected = ["skills/demo/SKILL.md", "scripts/helper.md", "templates/MECHANICS.md",
                    "playbooks/python.md", "agents/reviewer.md", "GLOBAL_AGENTS.md"]
        for prefix in ("~/.coding-agent/", "$HOME/.coding-agent/"):
            text = " ".join(f"`{prefix}{relative}`" for relative in expected[:-1])
            text += f" `{prefix}global-repo/GLOBAL_AGENTS.md`"
            with self.subTest(prefix=prefix):
                self.assertEqual(cb.extract_refs(text), expected)

    def test_unknown_home_resources_are_not_treated_as_repository_files(self):
        self.assertEqual(cb.extract_refs("`~/.coding-agent/settings.json`"), [])

    def test_shared_missing_agent_reference_is_reported(self):
        self.write("AGENTS.md", "读取 `~/.coding-agent/agents/absent.md`")
        self.assertEqual([(entry.source, entry.ref) for entry in cb.check_refs(self.root)],
                         [("AGENTS.md", "agents/absent.md")])

    def test_history_uses_agents_body_and_ignores_compatibility_wrapper(self):
        tracked = "GLOBAL_AGENTS.md\nAGENTS.md\nCLAUDE.md\nskills/demo/SKILL.md\n"
        with patch.object(cb, "_git", return_value=tracked):
            self.assertEqual(cb._paths_at_ref(self.root, "base"),
                             ["GLOBAL_AGENTS.md", "AGENTS.md", "skills/demo/SKILL.md"])

    def test_body_migration_is_not_artificial_budget_growth(self):
        body = "项目规则正文"
        self.write("AGENTS.md", body)
        self.write("CLAUDE.md", "@AGENTS.md\n")
        old = {"GLOBAL_AGENTS.md": "全局规则", "CLAUDE.md": body}
        with patch.object(cb, "_git", return_value="\n".join(old)), \
                patch.object(cb, "file_at_ref", side_effect=lambda root, ref, rel: old[rel]):
            report = cb.delta(self.root, "base")
        self.assertEqual(report.old_chars, report.new_chars)
        self.assertEqual(report.growth_ratio, 0)

    def test_cli_uses_current_repository_root_without_root_argument(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "measure", "--json"],
                                cwd=ROOT, capture_output=True, text=True, check=True)
        paths = {entry["path"] for entry in json.loads(result.stdout)["entries"]}
        self.assertIn("AGENTS.md", paths)
        self.assertNotIn("CLAUDE.md", paths)


if __name__ == "__main__":
    unittest.main()
