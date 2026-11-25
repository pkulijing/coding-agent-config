"""Tests for scripts/check_routine_boundaries.py (pure rules, PR integrity, and git diff sandbox)."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load_boundaries_module():
    path = ROOT / "scripts/check_routine_boundaries.py"
    spec = importlib.util.spec_from_file_location("check_routine_boundaries", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git_env():
    return {
        **os.environ,
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }


def git_run(repo: Path, *args: str):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        env=git_env(),
        capture_output=True,
        text=True,
    )


class PathClassificationTests(unittest.TestCase):
    def test_allowed_whitelist_paths(self):
        mod = load_boundaries_module()
        allowed = [
            "GLOBAL_AGENTS.md",
            "README.md",
            "./README.md",
            "playbooks/python.md",
            "docs/77-test/PLAN.md",
            "skills/commit/SKILL.md",
            "skills/review-loop/references/angles.md",
            "templates/MECHANICS.md",
            "templates/python-uv/pyproject.toml",
            "scripts/check_routine_boundaries.py",
            "hooks/pre-commit.sh",
        ]
        for p in allowed:
            with self.subTest(path=p):
                res = mod.classify_path(p)
                self.assertEqual(res["status"], "allowed", res)

    def test_outside_whitelist_including_shared_registry_and_nested_playbook(self):
        mod = load_boundaries_module()
        outside = [
            "AGENTS.md",
            "CLAUDE.md",
            "pyproject.toml",
            "tests/test_routine_boundaries.py",
            "playbooks/references/python-runtime.md",
            "playbooks/notes.txt",
            "playbooks/.md",
            "scheduler/install.sh",
        ]
        for p in outside:
            with self.subTest(path=p):
                res = mod.classify_path(p)
                self.assertEqual(res["status"], "outside_whitelist", res)

    def test_redlines_override_whitelist_and_resist_case_variants(self):
        mod = load_boundaries_module()
        redlines = [
            "skills/routine-dev/SKILL.md",
            "skills/routine-dev/references/security-boundary.md",
            "SKILLS/ROUTINE-DEV/SKILL.md",
            "agents/codex-review.toml",
            "Agents/dsh-review.toml",
            "install.sh",
            "INSTALL.SH",
            ".github/workflows/ff-merge.yml",
            ".GITHUB/labels.yml",
        ]
        for p in redlines:
            with self.subTest(path=p):
                res = mod.classify_path(p)
                self.assertEqual(res["status"], "redline", res)

    def test_invalid_paths_are_rejected_fail_closed(self):
        mod = load_boundaries_module()
        invalid = [
            "",
            "/etc/passwd",
            "skills/../install.sh",
            "docs/../../.github/workflows/ff-merge.yml",
            "skills/routine-dev/",
            "skills//commit/SKILL.md",
            "skills\\routine-dev\\SKILL.md",
            "docs/bad\x00name.md",
            ".",
            "..",
        ]
        for p in invalid:
            with self.subTest(path=p):
                res = mod.classify_path(p)
                self.assertEqual(res["status"], "invalid", res)


class OpenPrIntegrityTests(unittest.TestCase):
    def test_envelope_complete_aggregates_all_schemas_and_renames(self):
        mod = load_boundaries_module()
        payload = {
            "complete": True,
            "prs": [
                {
                    "number": 10,
                    "changedFiles": 2,
                    "files": [
                        {"path": "README.md"},
                        {"path": "docs/new.md", "previousPath": "docs/old.md"},
                    ],
                },
                {
                    "number": 12,
                    "changed_files": 2,
                    "files": [
                        {"filename": "skills/a/SKILL.md", "previous_filename": "skills/old/SKILL.md"},
                        "templates/MECHANICS.md",
                    ],
                },
            ],
        }
        file_map, errors = mod.parse_open_prs(payload)
        self.assertEqual(errors, [])
        self.assertEqual(file_map["README.md"], [10])
        self.assertEqual(file_map["docs/new.md"], [10])
        self.assertEqual(file_map["docs/old.md"], [10])
        self.assertEqual(file_map["skills/a/SKILL.md"], [12])
        self.assertEqual(file_map["skills/old/SKILL.md"], [12])
        self.assertEqual(file_map["templates/MECHANICS.md"], [12])

    def test_incomplete_or_truncated_pr_inputs_fail_closed(self):
        mod = load_boundaries_module()
        bad_cases = [
            ("envelope complete false", {"complete": False, "prs": []}, None),
            ("envelope missing complete", {"prs": []}, None),
            ("envelope complete truthy string", {"complete": "true", "prs": []}, None),
            ("raw list without pr_limit", [], None),
            ("raw list hits pr_limit", [{"number": 1, "files": []}, {"number": 2, "files": []}], 2),
            ("pr missing files field", {"complete": True, "prs": [{"number": 5}]}, None),
            ("pr files is null", {"complete": True, "prs": [{"number": 5, "files": None}]}, None),
            (
                "pr files truncated by changedFiles",
                {"complete": True, "prs": [{"number": 5, "changedFiles": 3, "files": [{"path": "README.md"}]}]},
                None,
            ),
            (
                "pr filesTruncated flag",
                {"complete": True, "prs": [{"number": 5, "filesTruncated": True, "files": [{"path": "README.md"}]}]},
                None,
            ),
            (
                "pr filesComplete false",
                {"complete": True, "prs": [{"number": 5, "filesComplete": False, "files": [{"path": "README.md"}]}]},
                None,
            ),
            (
                "unrecognized file object",
                {"complete": True, "prs": [{"number": 5, "files": [{"other": "README.md"}]}]},
                None,
            ),
        ]
        for label, payload, pr_limit in bad_cases:
            with self.subTest(case=label):
                _, errors = mod.parse_open_prs(payload, pr_limit=pr_limit)
                self.assertTrue(errors, f"expected fail-closed error for {label}")

    def test_raw_list_below_limit_succeeds(self):
        mod = load_boundaries_module()
        payload = [{"number": 7, "changedFiles": 1, "files": [{"path": "README.md"}]}]
        file_map, errors = mod.parse_open_prs(payload, pr_limit=100)
        self.assertEqual(errors, [])
        self.assertEqual(file_map, {"README.md": [7]})


class CliAndGitSandboxTests(unittest.TestCase):
    def run_cli(self, mod, argv):
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            code = mod.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_expected_paths_mode_detects_shared_file_conflict_and_outside_registry(self):
        mod = load_boundaries_module()
        with tempfile.TemporaryDirectory() as tmp:
            prs_file = Path(tmp) / "prs.json"
            prs_file.write_text(
                json.dumps(
                    {
                        "complete": True,
                        "prs": [
                            {"number": 42, "changedFiles": 1, "files": [{"path": "README.md"}]},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            # Allowed & non-conflicting passes
            code, out, err = self.run_cli(
                mod,
                ["--open-prs", str(prs_file), "--path", "skills/commit/SKILL.md", "--path", "templates/MECHANICS.md"],
            )
            self.assertEqual(code, 0, err)
            report = json.loads(out)
            self.assertTrue(report["ok"])

            # Shared file conflict (README.md) + non-whitelisted shared registry (AGENTS.md) fails with exit 1
            code, out, _ = self.run_cli(
                mod,
                ["--open-prs", str(prs_file), "--path", "README.md", "--path", "AGENTS.md"],
            )
            self.assertEqual(code, 1)
            report = json.loads(out)
            self.assertFalse(report["ok"])
            self.assertEqual(report["prConflicts"], [{"path": "README.md", "prs": [42]}])
            self.assertEqual(len(report["outsideWhitelist"]), 1)
            self.assertEqual(report["outsideWhitelist"][0]["normalized"], "AGENTS.md")

    def test_missing_open_prs_file_fails_with_exit_2(self):
        mod = load_boundaries_module()
        code, out, err = self.run_cli(
            mod,
            ["--open-prs", "/nonexistent/open-prs.json", "--path", "README.md"],
        )
        self.assertEqual(code, 2)
        report = json.loads(out)
        self.assertFalse(report["ok"])
        self.assertTrue(report["errors"])
        self.assertTrue(err)

    def _init_sandbox_repo(self, root: Path):
        repo = root / "repo"
        repo.mkdir()
        git_run(repo, "init", "--initial-branch=master")
        for rel, content in [
            ("README.md", "init\n"),
            ("skills/routine-dev/SKILL.md", "redline\n"),
            ("skills/demo/SKILL.md", "demo\n"),
            ("docs/shared.md", "shared\n"),
            ("install.sh", "#!/bin/sh\n"),
        ]:
            target = repo / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        git_run(repo, "add", ".")
        git_run(repo, "commit", "-m", "base")
        return repo

    def test_git_diff_catches_rename_out_of_redline_and_special_filenames(self):
        mod = load_boundaries_module()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = self._init_sandbox_repo(tmp_path)
            prs_file = tmp_path / "prs.json"
            prs_file.write_text(json.dumps({"complete": True, "prs": []}), encoding="utf-8")

            # Rename redline file into allowed path: --name-only would miss the old redline path!
            git_run(repo, "checkout", "-b", "rename-redline")
            git_run(repo, "mv", "skills/routine-dev/SKILL.md", "skills/demo/moved.md")
            git_run(repo, "commit", "-m", "move redline")

            code, out, _ = self.run_cli(
                mod,
                ["--repo", str(repo), "--git-diff-base", "master", "--open-prs", str(prs_file)],
            )
            self.assertEqual(code, 1)
            report = json.loads(out)
            self.assertFalse(report["ok"])
            redline_paths = [item["normalized"] for item in report["redlineViolations"]]
            self.assertIn("skills/routine-dev/SKILL.md", redline_paths)

            # Special filenames (spaces, Chinese, quotes, brackets, glob *) under allowed dir pass cleanly
            git_run(repo, "checkout", "master")
            git_run(repo, "checkout", "-b", "special-names")
            special_names = [
                "docs/中文 空格 [v1] 'quote'.md",
                "docs/star*name?.md",
            ]
            for rel in special_names:
                (repo / rel).write_text("special\n", encoding="utf-8")
            git_run(repo, "add", ".")
            git_run(repo, "commit", "-m", "add special names")

            code, out, err = self.run_cli(
                mod,
                ["--repo", str(repo), "--git-diff-base", "master", "--open-prs", str(prs_file)],
            )
            self.assertEqual(code, 0, err)
            report = json.loads(out)
            self.assertTrue(report["ok"])
            self.assertEqual(sorted(report["checkedPaths"]), sorted(special_names))

            # Ensure helper did not modify repository status
            status = git_run(repo, "status", "--porcelain").stdout
            self.assertEqual(status, "")

    def test_git_diff_catches_delete_and_rename_conflict_with_open_pr(self):
        mod = load_boundaries_module()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = self._init_sandbox_repo(tmp_path)
            prs_file = tmp_path / "prs.json"
            prs_file.write_text(
                json.dumps(
                    {
                        "complete": True,
                        "prs": [
                            {"number": 88, "changedFiles": 1, "files": [{"path": "docs/shared.md"}]},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            # 1) Rename docs/shared.md -> docs/renamed.md must still conflict with PR #88
            git_run(repo, "checkout", "-b", "rename-conflict")
            git_run(repo, "mv", "docs/shared.md", "docs/renamed.md")
            git_run(repo, "commit", "-m", "rename shared")

            code, out, _ = self.run_cli(
                mod,
                ["--repo", str(repo), "--git-diff-base", "master", "--open-prs", str(prs_file)],
            )
            self.assertEqual(code, 1)
            report = json.loads(out)
            self.assertEqual(report["prConflicts"], [{"path": "docs/shared.md", "prs": [88]}])

            # 2) Delete install.sh (redline) must be caught
            git_run(repo, "checkout", "master")
            git_run(repo, "checkout", "-b", "delete-redline")
            git_run(repo, "rm", "install.sh")
            git_run(repo, "commit", "-m", "delete install.sh")

            code, out, _ = self.run_cli(
                mod,
                ["--repo", str(repo), "--git-diff-base", "master", "--open-prs", str(prs_file)],
            )
            self.assertEqual(code, 1)
            report = json.loads(out)
            redline_paths = [item["normalized"] for item in report["redlineViolations"]]
            self.assertIn("install.sh", redline_paths)

    def test_paths_file_null_separated_and_json_and_bad_git_ref(self):
        mod = load_boundaries_module()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            prs_file = tmp_path / "prs.json"
            prs_file.write_text(json.dumps({"complete": True, "prs": []}), encoding="utf-8")

            # NUL-separated paths file preserves embedded newlines in filenames
            paths_z = tmp_path / "paths.z"
            paths_z.write_bytes(b"docs/line1\nline2.md\x00skills/commit/SKILL.md\x00")
            code, out, err = self.run_cli(
                mod,
                ["--open-prs", str(prs_file), "--paths-file", str(paths_z), "-z"],
            )
            self.assertEqual(code, 0, err)
            report = json.loads(out)
            self.assertEqual(report["checkedPaths"], ["docs/line1\nline2.md", "skills/commit/SKILL.md"])

            # --paths-json with redline path fails with exit 1
            paths_json = tmp_path / "paths.json"
            paths_json.write_text(json.dumps(["agents/codex-review.toml"]), encoding="utf-8")
            code, out, _ = self.run_cli(
                mod,
                ["--open-prs", str(prs_file), "--paths-json", str(paths_json)],
            )
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out)["redlineViolations"][0]["normalized"], "agents/codex-review.toml")

            # Invalid git ref fails closed with exit 2
            repo = self._init_sandbox_repo(tmp_path)
            code, out, _ = self.run_cli(
                mod,
                ["--repo", str(repo), "--git-diff-base", "nonexistent-ref", "--open-prs", str(prs_file)],
            )
            self.assertEqual(code, 2)
            self.assertTrue(json.loads(out)["errors"])

            # Empty diff (master...master) passes with exit 0
            code, out, err = self.run_cli(
                mod,
                ["--repo", str(repo), "--git-diff-base", "master", "--open-prs", str(prs_file)],
            )
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out)["checkedPaths"], [])

    def test_unhashable_paths_json_and_non_utf8_inputs_fail_closed_cleanly(self):
        mod = load_boundaries_module()
        script = ROOT / "scripts/check_routine_boundaries.py"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            prs_file = tmp_path / "prs.json"
            prs_file.write_text(json.dumps({"complete": True, "prs": []}), encoding="utf-8")

            # 1) Unhashable element in --paths-json must not raise TypeError
            bad_paths_json = tmp_path / "bad_paths.json"
            bad_paths_json.write_text(json.dumps([{"path": "README.md"}, ["README.md"]]), encoding="utf-8")
            code, out, _ = self.run_cli(
                mod,
                ["--open-prs", str(prs_file), "--paths-json", str(bad_paths_json)],
            )
            self.assertEqual(code, 1)
            report = json.loads(out)
            self.assertFalse(report["ok"])
            self.assertEqual(len(report["invalidPaths"]), 2)

            # 2) Non-UTF-8 bytes in --paths-file (-z) must fail closed with exit 2 and valid UTF-8 JSON (real subprocess)
            non_utf8_paths = tmp_path / "non_utf8.z"
            non_utf8_paths.write_bytes(b"docs/\xff.md\x00")
            proc = subprocess.run(
                [sys.executable, str(script), "--open-prs", str(prs_file), "--paths-file", str(non_utf8_paths), "-z"],
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            self.assertEqual(proc.returncode, 2, proc.stderr)
            report = json.loads(proc.stdout)
            self.assertFalse(report["ok"])
            self.assertTrue(report["errors"])

            # 3) Non-UTF-8 bytes in --open-prs must fail closed with exit 2 and valid JSON (not uncaught UnicodeDecodeError)
            non_utf8_prs = tmp_path / "non_utf8_prs.json"
            non_utf8_prs.write_bytes(b"\xff\xfe")
            code, out, err = self.run_cli(
                mod,
                ["--open-prs", str(non_utf8_prs), "--path", "README.md"],
            )
            self.assertEqual(code, 2, err)
            report = json.loads(out)
            self.assertFalse(report["ok"])
            self.assertTrue(report["errors"])

            # 4) --path accepts multiple values after one flag as well as repeated flags
            code, out, err = self.run_cli(
                mod,
                ["--open-prs", str(prs_file), "--path", "README.md", "docs/a.md"],
            )
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out)["checkedPaths"], ["README.md", "docs/a.md"])


if __name__ == "__main__":
    unittest.main()
