#!/usr/bin/env python3
"""check_routine_identity.py — verify whether the active GitHub actor is isolated from repo owner.

Uses `gh repo view --json owner` and GraphQL `viewer { login }` (which works for both
user PATs and GitHub App installation tokens, unlike REST `/user`). Reports one of:
- `isolated`: active actor differs from repository owner (cannot trigger `ff-merge.yml`)
- `shared_owner`: active actor matches repository owner (credential isolation NOT active)
- `unknown`: lookup failed or metadata missing (fail-closed)
"""

import argparse
import json
import subprocess
import sys

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CLI_MISSING = 4


def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        sys.stderr.write(f"error: command not found: {cmd[0]} (install it and retry)\n")
        sys.exit(EXIT_CLI_MISSING)


def evaluate_identity(actor_login, repo_owner):
    """Pure classification of active GitHub actor against repository owner."""
    actor = actor_login.strip() if isinstance(actor_login, str) else ""
    owner = repo_owner.strip() if isinstance(repo_owner, str) else ""
    if not actor or not owner:
        return {
            "status": "unknown",
            "actor": actor,
            "repoOwner": owner,
            "canTriggerFfMerge": None,
        }
    if actor.lower() == owner.lower():
        return {
            "status": "shared_owner",
            "actor": actor,
            "repoOwner": owner,
            "canTriggerFfMerge": True,
        }
    return {
        "status": "isolated",
        "actor": actor,
        "repoOwner": owner,
        "canTriggerFfMerge": False,
    }


def fetch_repo_owner(repo=None):
    cmd = ["gh", "repo", "view"]
    if repo:
        cmd.append(repo)
    cmd += ["--json", "owner", "-q", ".owner.login"]
    result = _run(cmd)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or "unknown error"
        return "", f"failed to fetch repository owner: {detail}"
    owner = result.stdout.strip()
    if not owner:
        return "", "repository owner lookup returned empty login"
    return owner, None


def fetch_viewer_login():
    cmd = ["gh", "api", "graphql", "-f", "query=query{viewer{login}}", "--jq", ".data.viewer.login"]
    result = _run(cmd)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or "unknown error"
        return "", f"failed to fetch active GitHub viewer: {detail}"
    login = result.stdout.strip()
    if not login:
        return "", "active GitHub viewer lookup returned empty login"
    return login, None


def build_parser():
    p = argparse.ArgumentParser(prog="check_routine_identity.py", description=__doc__)
    p.add_argument(
        "--repo",
        default=None,
        help="Target GitHub repo slug (owner/name); defaults to current repo",
    )
    p.add_argument(
        "--require-isolated",
        action="store_true",
        help="Exit non-zero unless status is `isolated`",
    )
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    owner, owner_err = fetch_repo_owner(args.repo)
    if owner_err:
        report = evaluate_identity("", owner)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.stderr.write(f"error: {owner_err}\n")
        return EXIT_ERROR

    actor, actor_err = fetch_viewer_login()
    if actor_err:
        report = evaluate_identity("", owner)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.stderr.write(f"error: {actor_err}\n")
        return EXIT_ERROR

    report = evaluate_identity(actor, owner)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] == "unknown":
        sys.stderr.write("error: unable to classify GitHub identity (unknown)\n")
        return EXIT_ERROR
    if args.require_isolated and report["status"] != "isolated":
        sys.stderr.write(
            f"error: routine GitHub identity is not isolated (status={report['status']})\n"
        )
        return EXIT_ERROR
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
