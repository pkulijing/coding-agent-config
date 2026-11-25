"""Layer 2 tests: routine GitHub identity boundary & controlled sandbox verification."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load_identity_module():
    spec = importlib.util.spec_from_file_location(
        "check_routine_identity", ROOT / "scripts/check_routine_identity.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def response(stdout="", code=0, stderr=""):
    return subprocess.CompletedProcess([], code, stdout, stderr)


class RoutineIdentityEvaluatorTests(unittest.TestCase):
    def test_evaluate_identity_distinguishes_isolated_shared_and_unknown(self):
        mod = load_identity_module()

        isolated_bot = mod.evaluate_identity("routine-dev[bot]", "pkulijing")
        self.assertEqual(isolated_bot["status"], "isolated")
        self.assertFalse(isolated_bot["canTriggerFfMerge"])

        isolated_user = mod.evaluate_identity("pkulijing-bot", "pkulijing")
        self.assertEqual(isolated_user["status"], "isolated")
        self.assertFalse(isolated_user["canTriggerFfMerge"])

        shared = mod.evaluate_identity("PKULiJing", "pkulijing")
        self.assertEqual(shared["status"], "shared_owner")
        self.assertTrue(shared["canTriggerFfMerge"])

        for actor, owner in (("", "pkulijing"), ("routine-dev[bot]", ""), (None, "pkulijing")):
            with self.subTest(actor=actor, owner=owner):
                unknown = mod.evaluate_identity(actor, owner)
                self.assertEqual(unknown["status"], "unknown")
                self.assertIsNone(unknown["canTriggerFfMerge"])

    def test_cli_require_isolated_gate(self):
        mod = load_identity_module()

        def run_cli(replies, *extra):
            stdout, stderr = io.StringIO(), io.StringIO()
            argv = ["check_routine_identity.py", *extra]
            with patch.object(sys, "argv", argv), patch.object(mod, "_run", side_effect=replies):
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    code = mod.main()
            return code, stdout.getvalue(), stderr.getvalue()

        # Isolated actor passes --require-isolated
        code, out, _ = run_cli(
            [response("pkulijing\n"), response("routine-dev[bot]\n")],
            "--require-isolated",
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["status"], "isolated")

        # Shared owner succeeds in report mode, fails --require-isolated
        code, out, _ = run_cli([response("pkulijing\n"), response("pkulijing\n")])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["status"], "shared_owner")

        code, out, err = run_cli(
            [response("pkulijing\n"), response("pkulijing\n")],
            "--require-isolated",
        )
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["status"], "shared_owner")
        self.assertIn("shared_owner", err)

        # --repo must be passed as positional arg to `gh repo view` (not --repo flag)
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            patch.object(sys, "argv", ["check_routine_identity.py", "--repo", "pkulijing/coding-agent-config"]),
            patch.object(mod, "_run", side_effect=[response("pkulijing\n"), response("routine-dev[bot]\n")]) as run_mock,
        ):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = mod.main()
        self.assertEqual(code, 0)
        self.assertEqual(
            run_mock.call_args_list[0].args[0],
            ["gh", "repo", "view", "pkulijing/coding-agent-config", "--json", "owner", "-q", ".owner.login"],
        )

        # Lookup failure fails closed even without --require-isolated
        code, out, err = run_cli([response(code=1, stderr="auth error")])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["status"], "unknown")
        self.assertIn("auth error", err)


class ControlledMergeIsolationSandboxTests(unittest.TestCase):
    def test_ff_merge_workflow_requires_repository_owner(self):
        wf = (ROOT / ".github/workflows/ff-merge.yml").read_text(encoding="utf-8")
        self.assertIn("github.event.sender.login == github.repository_owner", wf)

        # Mirror the workflow's exact admission predicate against owner vs bot events
        def ff_merge_admits(sender_login, repo_owner, event_name, label_name="", comment_body="", is_pr=True):
            if sender_login != repo_owner:
                return False
            if event_name == "pull_request_target" and label_name == "ff-merge":
                return True
            if event_name == "issue_comment" and is_pr and comment_body.startswith("/ff"):
                return True
            return False

        self.assertTrue(ff_merge_admits("pkulijing", "pkulijing", "pull_request_target", label_name="ff-merge"))
        self.assertTrue(ff_merge_admits("pkulijing", "pkulijing", "issue_comment", comment_body="/ff"))
        self.assertFalse(ff_merge_admits("routine-dev[bot]", "pkulijing", "pull_request_target", label_name="ff-merge"))
        self.assertFalse(ff_merge_admits("routine-dev[bot]", "pkulijing", "issue_comment", comment_body="/ff"))
        self.assertFalse(ff_merge_admits("pkulijing-bot", "pkulijing", "issue_comment", comment_body="/ff"))

    def test_sandbox_bot_can_push_auto_branch_and_open_pr_but_cannot_push_master(self):
        """Controlled bare-repo sandbox with branch-protection pre-receive hook + stub gh."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            origin = tmp_path / "origin.git"
            work = tmp_path / "work"
            bin_dir = tmp_path / "bin"
            bin_dir.mkdir()
            gh_log = tmp_path / "gh.log"

            env = {
                **os.environ,
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_CONFIG_SYSTEM": "/dev/null",
                "GIT_AUTHOR_NAME": "Test",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test",
                "GIT_COMMITTER_EMAIL": "test@example.com",
                "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
            }

            subprocess.run(["git", "init", "--bare", "--initial-branch=master", str(origin)], check=True, env=env, capture_output=True)
            subprocess.run(["git", "clone", str(origin), str(work)], check=True, env=env, capture_output=True)
            (work / "README.md").write_text("init\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(work), "add", "README.md"], check=True, env=env, capture_output=True)
            subprocess.run(["git", "-C", str(work), "commit", "-m", "init"], check=True, env=env, capture_output=True)
            subprocess.run(["git", "-C", str(work), "push", "origin", "master"], check=True, env=env, capture_output=True)

            # Simulate GitHub Ruleset on master: only owner or github-actions[bot] may update refs/heads/master
            hook = origin / "hooks/pre-receive"
            hook.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "while read -r old new ref; do\n"
                "  if [ \"$ref\" = \"refs/heads/master\" ] && [ \"${SIM_GIT_ACTOR:-}\" != \"pkulijing\" ] && [ \"${SIM_GIT_ACTOR:-}\" != \"github-actions[bot]\" ]; then\n"
                "    echo \"protected branch master: actor '${SIM_GIT_ACTOR:-unknown}' denied\" >&2\n"
                "    exit 1\n"
                "  fi\n"
                "done\n",
                encoding="utf-8",
            )
            hook.chmod(hook.stat().st_mode | stat.S_IXUSR)

            # Stub gh CLI that allows pr create for bot actor and logs invocations
            stub_gh = bin_dir / "gh"
            stub_gh.write_text(
                "#!/usr/bin/env bash\n"
                f"printf '%s\\n' \"$*\" >> {gh_log}\n"
                "if [ \"$1\" = \"pr\" ] && [ \"$2\" = \"create\" ]; then\n"
                "  echo 'https://github.com/pkulijing/coding-agent-config/pull/999'\n"
                "  exit 0\n"
                "fi\n"
                "exit 1\n",
                encoding="utf-8",
            )
            stub_gh.chmod(stub_gh.stat().st_mode | stat.S_IXUSR)

            # Bot creates a commit on a feature branch
            subprocess.run(["git", "-C", str(work), "checkout", "-b", "auto/dev-20261125-isolation"], check=True, env=env, capture_output=True)
            (work / "change.txt").write_text("ok\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(work), "add", "change.txt"], check=True, env=env, capture_output=True)
            subprocess.run(["git", "-C", str(work), "commit", "-m", "feat: bot change"], check=True, env=env, capture_output=True)

            bot_env = {**env, "SIM_GIT_ACTOR": "routine-dev[bot]"}

            # 1) Direct push to master by bot is rejected
            push_master = subprocess.run(
                ["git", "-C", str(work), "push", "origin", "HEAD:refs/heads/master"],
                env=bot_env,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(push_master.returncode, 0)
            self.assertIn("protected branch master", push_master.stderr)

            # 2) Push to auto/* branch by bot succeeds
            push_branch = subprocess.run(
                ["git", "-C", str(work), "push", "origin", "HEAD:refs/heads/auto/dev-20261125-isolation"],
                env=bot_env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(push_branch.returncode, 0, push_branch.stderr)

            # 3) Opening PR via gh succeeds
            pr_create = subprocess.run(
                ["gh", "pr", "create", "--base", "master", "--head", "auto/dev-20261125-isolation", "--title", "test", "--body", "test"],
                env=bot_env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(pr_create.returncode, 0, pr_create.stderr)
            self.assertIn("/pull/999", pr_create.stdout)


if __name__ == "__main__":
    unittest.main()
