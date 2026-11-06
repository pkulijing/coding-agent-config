"""关闭 issue 的 CLI 契约；所有平台与外部响应均显式指定。"""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("platform_issue", ROOT / "scripts/platform_issue.py")
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


def response(data=None, code=0, stderr=""):
    return subprocess.CompletedProcess([], code, json.dumps(data) if data is not None else "", stderr)


class IssueCloseTests(unittest.TestCase):
    def invoke(self, platform, replies, *extra):
        stdout, stderr = io.StringIO(), io.StringIO()
        argv = ["platform_issue.py", "--platform", platform, "issue-close", "42", *extra]
        with patch.object(sys, "argv", argv), patch.object(helper, "_run", side_effect=replies) as run:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = helper.main()
        return result, stdout.getvalue(), stderr.getvalue(), run.call_args_list

    def test_github_default_and_closed_readback(self):
        result, out, err, calls = self.invoke("github", [response(), response({"state": "CLOSED", "stateReason": "COMPLETED"})])
        self.assertEqual(result, 0)
        self.assertIn("closed on github: #42", out)
        self.assertEqual(calls[0].args[0], ["gh", "issue", "close", "42", "--reason", "completed"])
        self.assertIn("stateReason", calls[1].args[0][-1])

    def test_not_planned_and_repo_propagate_to_both_calls(self):
        result, _, _, calls = self.invoke("github", [response(), response({"state": "CLOSED", "stateReason": "NOT_PLANNED"})], "--reason", "not-planned", "--repo", "owner/other")
        self.assertEqual(result, 0)
        self.assertEqual(calls[0].args[0], ["gh", "issue", "close", "42", "--reason", "not planned", "--repo", "owner/other"])
        self.assertEqual(calls[1].args[0][-2:], ["--repo", "owner/other"])

    def test_gitlab_reports_reason_limit(self):
        for reason in ("completed", "not-planned"):
            with self.subTest(reason=reason):
                result, out, err, calls = self.invoke("gitlab", [response(), response({"state": "closed"})], "--reason", reason, "--repo", "group/sub/project")
                self.assertEqual(result, 0)
                self.assertIn("closed on gitlab", out)
                self.assertIn("does not support", err)
                self.assertEqual(calls[0].args[0], ["glab", "issue", "close", "42", "--repo", "group/sub/project"])
                self.assertEqual(calls[1].args[0], ["glab", "issue", "view", "42", "-F", "json", "--repo", "group/sub/project"])

    def test_close_failure_never_reads_or_reports_success(self):
        for platform in ("github", "gitlab"):
            with self.subTest(platform=platform):
                result, out, err, calls = self.invoke(platform, [response(code=7, stderr="permission denied")])
                self.assertEqual(result, 1)
                self.assertEqual(out, "")
                self.assertIn("permission denied", err)
                self.assertEqual(len(calls), 1)

    def test_readback_failure_is_explicitly_unverified(self):
        for platform in ("github", "gitlab"):
            with self.subTest(platform=platform):
                result, out, err, _ = self.invoke(platform, [response(), response(code=1, stderr="offline")])
                self.assertEqual(result, 1)
                self.assertEqual(out, "")
                self.assertIn("verification failed", err)
                self.assertIn("offline", err)

    def test_success_exit_without_closed_state_is_not_success(self):
        for data in ({"state": "OPEN"}, {}, {"status": "error"}, [], None):
            with self.subTest(data=data):
                result, out, err, _ = self.invoke("github", [response(), response(data)])
                self.assertEqual(result, 1)
                self.assertEqual(out, "")
                self.assertIn("verification failed", err)

    def test_already_closed_with_different_reason_is_not_claimed(self):
        result, out, err, _ = self.invoke("github", [response(), response({"state": "CLOSED", "stateReason": "COMPLETED"})], "--reason", "not-planned")
        self.assertEqual(result, 1)
        self.assertEqual(out, "")
        self.assertIn("reason", err)

    def test_gitlab_open_is_not_success(self):
        result, out, err, _ = self.invoke("gitlab", [response(), response({"state": "opened"})])
        self.assertEqual(result, 1)
        self.assertEqual(out, "")
        self.assertIn("verification failed", err)

    def test_unknown_platform_has_no_mutation(self):
        args = helper.build_parser().parse_args(["issue-close", "42"])
        with patch.object(helper, "resolve_platform", return_value="unknown"), patch.object(helper, "_run") as run:
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(helper.cmd_issue_close(args), 2)
        run.assert_not_called()

    def test_invalid_reason_rejected_before_execution(self):
        with patch.object(helper, "_run") as run, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                helper.build_parser().parse_args(["issue-close", "42", "--reason", "invented"])
        run.assert_not_called()

    def test_missing_cli_preserves_existing_exit_code(self):
        args = helper.build_parser().parse_args(["--platform", "github", "issue-close", "42"])
        with patch.object(helper.subprocess, "run", side_effect=FileNotFoundError), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                helper.cmd_issue_close(args)
        self.assertEqual(raised.exception.code, 4)


if __name__ == "__main__":
    unittest.main()
