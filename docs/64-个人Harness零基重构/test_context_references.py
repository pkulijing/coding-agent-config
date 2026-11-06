"""领域 reference 纳入预算与引用检查，不扩展为通用 Markdown 解析器。"""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("context_references", ROOT / "scripts/context_budget.py")
cb = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cb)


class PlaybookReferencesTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def write(self, path, content="规则"):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def test_current_and_historical_paths_use_same_scope(self):
        paths = ["playbooks/python.md", "playbooks/references/python-runtime.md"]
        excluded = ["playbooks/references/deeper/ignored.md", "playbooks/references/data.json"]
        for path in paths + excluded:
            self.write(path)
        self.assertEqual(cb.instruction_paths(self.root), paths)
        with patch.object(cb, "_git", return_value="\n".join(paths + excluded)):
            self.assertEqual(cb._paths_at_ref(self.root, "base"), paths)
        report = cb.measure(self.root)
        self.assertEqual(report.total_chars, 4)
        self.assertTrue(all(entry.category == "lazy" for entry in report.entries))

    def test_moving_prose_to_reference_is_not_a_budget_reduction(self):
        self.write("playbooks/python.md", "入口")
        self.write("playbooks/references/runtime.md", "运行细则")
        old = {"playbooks/python.md": "入口运行细则"}
        with patch.object(cb, "_git", return_value="\n".join(old)), patch.object(
            cb, "file_at_ref", side_effect=lambda root, ref, path: old[path]
        ):
            result = cb.delta(self.root, "base")
        self.assertEqual(result.old_chars, result.new_chars)
        self.assertEqual(result.growth_ratio, 0)

    def test_full_and_shared_home_references_are_checked(self):
        self.write("GLOBAL_AGENTS.md", "`playbooks/references/a.md` `~/.coding-agent/playbooks/references/b.md`")
        self.write("playbooks/references/a.md")
        self.assertEqual(
            [(item.source, item.ref) for item in cb.check_refs(self.root)],
            [("GLOBAL_AGENTS.md", "playbooks/references/b.md")],
        )

    def test_playbook_entry_resolves_relative_reference(self):
        self.write("playbooks/python.md", "`references/runtime.md` `references/absent.md`")
        self.write("playbooks/references/runtime.md")
        self.assertEqual(
            [(item.source, item.ref) for item in cb.check_refs(self.root)],
            [("playbooks/python.md", "references/absent.md")],
        )

    def test_references_are_also_scanned_for_broken_links(self):
        self.write("playbooks/references/runtime.md", "`scripts/missing.py`")
        self.assertEqual(
            [(item.source, item.ref) for item in cb.check_refs(self.root)],
            [("playbooks/references/runtime.md", "scripts/missing.py")],
        )

    def test_json_output_labels_token_estimate(self):
        output = io.StringIO()
        with patch.object(cb, "_repo_root", return_value=self.root), contextlib.redirect_stdout(output):
            self.assertEqual(cb.main(["measure", "--json"]), 0)
        note = json.loads(output.getvalue())["token_estimate_note"]
        self.assertIn("历史", note)
        self.assertIn("非当前模型实测", note)


if __name__ == "__main__":
    unittest.main()
