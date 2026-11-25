"""验证 review-loop 按平台拆分与扁平编队契约。"""

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVIEW_LOOP = ROOT / "skills/review-loop"
PLATFORMS = ("codex", "cc", "dsh", "antigravity")


class ReviewLoopSplitTests(unittest.TestCase):
    def test_platform_references_exist_and_are_routed_from_skill(self):
        skill_text = (REVIEW_LOOP / "SKILL.md").read_text(encoding="utf-8")
        for platform in PLATFORMS:
            rel = f"references/{platform}.md"
            target = REVIEW_LOOP / rel
            self.assertTrue(target.is_file(), f"missing {rel}")
            self.assertIn(rel, skill_text, f"{rel} not routed from SKILL.md")
            content = target.read_text(encoding="utf-8")
            self.assertIn("> 读者：", content, f"{rel} missing reader header")

    def test_review_orchestrator_removed_from_agents_and_toml_configs(self):
        self.assertFalse((ROOT / "agents/review-orchestrator.md").exists())
        for name in ("codex-review.toml", "dsh-review.toml", "antigravity-review.toml"):
            parsed = tomllib.loads((ROOT / "agents" / name).read_text(encoding="utf-8"))
            self.assertNotIn("orchestrator", parsed, name)
            self.assertIn("reviewer", parsed, name)
            self.assertIn("deep_reviewer", parsed, name)

    def test_no_stale_review_orchestrator_references_in_active_files(self):
        targets = [
            *sorted((ROOT / "skills").glob("*/SKILL.md")),
            *sorted((REVIEW_LOOP / "references").glob("*.md")),
            *sorted((ROOT / "agents").glob("*.md")),
            *sorted((ROOT / "agents").glob("*.toml")),
            ROOT / "AGENTS.md",
            ROOT / "README.md",
        ]
        for path in targets:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("review-orchestrator", text, f"stale reference in {path.relative_to(ROOT)}")
        routine_dev = (ROOT / "skills/routine-dev/SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("orchestrator", routine_dev, "stale orchestrator mention in skills/routine-dev/SKILL.md")


if __name__ == "__main__":
    unittest.main()
