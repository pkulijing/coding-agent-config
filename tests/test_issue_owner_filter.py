"""Layer 1 tests: owner-author filtering for platform_issue.py."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("platform_issue", ROOT / "scripts/platform_issue.py")
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


def response(data=None, code=0, stderr=""):
    if isinstance(data, str):
        stdout = data
    elif data is not None:
        stdout = json.dumps(data)
    else:
        stdout = ""
    return subprocess.CompletedProcess([], code, stdout, stderr)


class ClassifyIssueAuthorTests(unittest.TestCase):
    def test_owner_exact_and_case_insensitive_match(self):
        self.assertEqual(
            helper.classify_issue_author({"author": {"login": "pkulijing", "is_bot": False}}, "pkulijing"),
            "owner",
        )
        self.assertEqual(
            helper.classify_issue_author({"author": {"login": "PKULiJing"}}, "pkulijing"),
            "owner",
        )

    def test_non_owner_and_bot_rejected(self):
        self.assertEqual(
            helper.classify_issue_author({"author": {"login": "outsider", "is_bot": False}}, "pkulijing"),
            "non_owner",
        )
        self.assertEqual(
            helper.classify_issue_author({"author": {"login": "pkulijing", "is_bot": True}}, "pkulijing"),
            "non_owner",
        )

    def test_missing_or_unreliable_author_metadata_is_unknown(self):
        unknown_cases = [
            {},
            {"author": None},
            {"author": {}},
            {"author": {"login": ""}},
            {"author": {"login": "   "}},
            {"author": "pkulijing"},
        ]
        for raw in unknown_cases:
            with self.subTest(raw=raw):
                self.assertEqual(helper.classify_issue_author(raw, "pkulijing"), "unknown")

    def test_missing_repo_owner_or_unverified_gitlab_is_unknown(self):
        self.assertEqual(
            helper.classify_issue_author({"author": {"login": "pkulijing"}}, ""),
            "unknown",
        )
        self.assertEqual(
            helper.classify_issue_author(
                {"author": {"username": "pkulijing"}},
                "pkulijing",
                platform=helper.PLATFORM_GITLAB,
            ),
            "unknown",
        )


class IssueListOwnerOnlyTests(unittest.TestCase):
    def invoke(self, platform, replies, *extra):
        stdout, stderr = io.StringIO(), io.StringIO()
        argv = ["platform_issue.py", "--platform", platform, *extra]
        with patch.object(sys, "argv", argv), patch.object(helper, "_run", side_effect=replies) as run:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = helper.main()
        return code, stdout.getvalue(), stderr.getvalue(), run.call_args_list

    def test_owner_only_filters_owner_non_owner_and_unknown_fixtures(self):
        raw_issues = [
            {
                "number": 200,
                "title": "owner issue",
                "url": "https://github.com/pkulijing/repo/issues/200",
                "labels": [{"name": "priority:P0"}],
                "updatedAt": "2026-11-25T09:00:00Z",
                "state": "OPEN",
                "author": {"login": "pkulijing", "is_bot": False},
            },
            {
                "number": 201,
                "title": "stranger issue",
                "url": "https://github.com/pkulijing/repo/issues/201",
                "labels": [{"name": "priority:P0"}],
                "updatedAt": "2026-11-25T09:01:00Z",
                "state": "OPEN",
                "author": {"login": "attacker", "is_bot": False},
            },
            {
                "number": 202,
                "title": "missing author issue",
                "url": "https://github.com/pkulijing/repo/issues/202",
                "labels": [{"name": "priority:P0"}],
                "updatedAt": "2026-11-25T09:02:00Z",
                "state": "OPEN",
            },
        ]
        code, out, err, calls = self.invoke(
            "github",
            [response("pkulijing\n"), response(raw_issues)],
            "issue-list",
            "--no-body",
            "--owner-only",
        )
        self.assertEqual(code, 0)
        self.assertEqual(calls[0].args[0], ["gh", "repo", "view", "--json", "owner", "-q", ".owner.login"])
        self.assertIn("--author", calls[1].args[0])
        self.assertIn("pkulijing", calls[1].args[0])
        self.assertIn("author", calls[1].args[0][calls[1].args[0].index("--json") + 1].split(","))
        parsed = json.loads(out)
        self.assertEqual([item["number"] for item in parsed], [200])
        self.assertEqual(parsed[0]["author"], "pkulijing")
        self.assertIn("#201", err)
        self.assertIn("#202", err)

    def test_owner_only_passes_repo_as_positional_arg_to_gh_repo_view(self):
        code, out, _, calls = self.invoke(
            "github",
            [response("other-owner\n"), response([])],
            "issue-list",
            "--owner-only",
            "--repo",
            "other-owner/repo",
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), [])
        self.assertEqual(
            calls[0].args[0],
            ["gh", "repo", "view", "other-owner/repo", "--json", "owner", "-q", ".owner.login"],
        )
        self.assertIn("--repo", calls[1].args[0])
        self.assertIn("other-owner/repo", calls[1].args[0])

    def test_owner_only_fails_closed_when_repo_owner_lookup_fails(self):
        code, out, err, calls = self.invoke(
            "github",
            [response(code=1, stderr="not authenticated")],
            "issue-list",
            "--owner-only",
        )
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("owner", err.lower())
        self.assertEqual(len(calls), 1)

    def test_owner_only_fails_closed_on_gitlab(self):
        code, out, err, calls = self.invoke(
            "gitlab",
            [],
            "issue-list",
            "--owner-only",
        )
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("gitlab", err.lower())
        self.assertEqual(len(calls), 0)

    def test_issue_view_require_owner_accepts_owner_and_rejects_others(self):
        owner_raw = {
            "number": 200,
            "title": "owner issue",
            "body": "desc",
            "url": "https://github.com/pkulijing/repo/issues/200",
            "labels": [],
            "updatedAt": "2026-11-25T09:00:00Z",
            "state": "OPEN",
            "stateReason": "",
            "author": {"login": "pkulijing", "is_bot": False},
        }
        code, out, _, _ = self.invoke(
            "github",
            [response("pkulijing\n"), response(owner_raw)],
            "issue-view",
            "200",
            "--require-owner",
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["author"], "pkulijing")

        for label, bad_raw in (
            ("non_owner", {**owner_raw, "author": {"login": "outsider"}}),
            ("unknown", {k: v for k, v in owner_raw.items() if k != "author"}),
        ):
            with self.subTest(case=label):
                code, out, err, _ = self.invoke(
                    "github",
                    [response("pkulijing\n"), response(bad_raw)],
                    "issue-view",
                    "200",
                    "--require-owner",
                )
                self.assertEqual(code, 1)
                self.assertEqual(out, "")
                self.assertIn(label, err)


if __name__ == "__main__":
    unittest.main()
