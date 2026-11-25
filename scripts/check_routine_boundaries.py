#!/usr/bin/env python3
"""check_routine_boundaries.py — read-only file boundary & open-PR conflict checker for routine-dev.

Evaluates either explicit expected paths (triage/batching) or an actual git diff range
(`git diff --name-status -z <base>...<head>`, pre-PR final check) against:
1. Four redlines (override whitelist, always forbidden, case-insensitive defense):
   - `skills/routine-dev/**`
   - `agents/**`
   - `install.sh`
   - `.github/**`
2. Closed whitelist (exact case):
   - `GLOBAL_AGENTS.md`, `README.md`
   - `playbooks/*.md` (top-level markdown only)
   - `docs/**`, `skills/**`, `templates/**`, `scripts/**`, `hooks/**`
3. Open PR file union (fail-closed on missing, truncated, or unverified PR inputs).

Exit codes:
  0 — all paths allowed and no open-PR conflicts
  1 — boundary violation (redline, outside whitelist, invalid path) or PR conflict
  2 — incomplete/malformed input or underlying read-only git/IO error
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys

EXIT_OK = 0
EXIT_VIOLATION = 1
EXIT_ERROR = 2

EXACT_WHITELIST = frozenset({"GLOBAL_AGENTS.md", "README.md"})
RECURSIVE_WHITELIST_DIRS = frozenset({"docs", "skills", "templates", "scripts", "hooks"})

REDLINE_PREFIXES = (
    ("skills/routine-dev", "skills/routine-dev/**"),
    ("agents", "agents/**"),
    (".github", ".github/**"),
)
REDLINE_EXACT = (
    ("install.sh", "install.sh"),
)


def normalize_repo_path(raw):
    """Normalize a repo-relative POSIX path; reject unsafe or malformed paths fail-closed."""
    if not isinstance(raw, str):
        return None, "path must be a string"
    if raw == "":
        return None, "empty path"
    if "\x00" in raw:
        return None, "path contains NUL byte"
    if "\\" in raw:
        return None, "path contains backslash separator"
    if raw.startswith("/"):
        return None, "absolute path is not allowed"
    if len(raw) >= 2 and raw[1] == ":" and raw[0].isalpha():
        return None, "drive-qualified path is not allowed"

    path = raw
    while path.startswith("./"):
        path = path[2:]

    if path == "" or path.endswith("/"):
        return None, "empty or directory path is not allowed"

    parts = path.split("/")
    for part in parts:
        if part in ("", ".", ".."):
            return None, f"unsafe path segment {part!r}"

    return path, None


def classify_path(path):
    """Classify a single repo path into allowed / redline / outside_whitelist / invalid."""
    norm, err = normalize_repo_path(path)
    if err is not None:
        return {
            "path": path,
            "normalized": None,
            "status": "invalid",
            "rule": err,
        }

    lower = norm.lower()
    for exact_lower, rule in REDLINE_EXACT:
        if lower == exact_lower:
            return {
                "path": path,
                "normalized": norm,
                "status": "redline",
                "rule": rule,
            }
    for prefix_lower, rule in REDLINE_PREFIXES:
        if lower == prefix_lower or lower.startswith(prefix_lower + "/"):
            return {
                "path": path,
                "normalized": norm,
                "status": "redline",
                "rule": rule,
            }

    if norm in EXACT_WHITELIST:
        return {
            "path": path,
            "normalized": norm,
            "status": "allowed",
            "rule": norm,
        }

    parts = norm.split("/")
    if len(parts) == 2 and parts[0] == "playbooks" and parts[1].endswith(".md") and parts[1] != ".md":
        return {
            "path": path,
            "normalized": norm,
            "status": "allowed",
            "rule": "playbooks/*.md",
        }

    if len(parts) >= 2 and parts[0] in RECURSIVE_WHITELIST_DIRS:
        return {
            "path": path,
            "normalized": norm,
            "status": "allowed",
            "rule": f"{parts[0]}/**",
        }

    return {
        "path": path,
        "normalized": norm,
        "status": "outside_whitelist",
        "rule": "not in allowed whitelist",
    }


def _extract_pr_file_paths(item, pr_number, idx):
    """Extract normalized path(s) from a PR file entry (supports GraphQL, REST/MCP, and strings)."""
    raw_paths = []
    if isinstance(item, str):
        raw_paths.append(item)
    elif isinstance(item, dict):
        primary = item.get("path") if "path" in item else item.get("filename")
        if not isinstance(primary, str) or not primary:
            return [], f"PR #{pr_number} files[{idx}] missing valid 'path' or 'filename'"
        raw_paths.append(primary)
        for prev_key in ("previousPath", "previous_filename"):
            if prev_key in item and item[prev_key] is not None:
                prev_val = item[prev_key]
                if not isinstance(prev_val, str) or not prev_val:
                    return [], f"PR #{pr_number} files[{idx}] has invalid '{prev_key}'"
                raw_paths.append(prev_val)
    else:
        return [], f"PR #{pr_number} files[{idx}] must be a string or object"

    normalized = []
    for raw in raw_paths:
        norm, err = normalize_repo_path(raw)
        if err is not None:
            return [], f"PR #{pr_number} files[{idx}] invalid path {raw!r}: {err}"
        normalized.append(norm)
    return normalized, None


def parse_open_prs(data, *, pr_limit=None):
    """Aggregate open PR file union with fail-closed completeness checks."""
    errors = []
    if pr_limit is not None and (isinstance(pr_limit, bool) or not isinstance(pr_limit, int) or pr_limit <= 0):
        return {}, ["--pr-limit must be a positive integer"]

    if isinstance(data, dict):
        if data.get("complete") is not True:
            errors.append("open PR envelope must explicitly set 'complete': true")
        prs = data.get("prs")
        if not isinstance(prs, list):
            errors.append("open PR envelope must contain a 'prs' list")
        if errors:
            return {}, errors
    elif isinstance(data, list):
        if pr_limit is None:
            return {}, ["raw open PR array requires --pr-limit (or wrap in {'complete': true, 'prs': [...]})"]
        if len(data) >= pr_limit:
            return {}, [
                f"open PR count ({len(data)}) reached --pr-limit ({pr_limit}); list may be truncated"
            ]
        prs = data
    else:
        return {}, ["open PR input must be a JSON object envelope or JSON array"]

    file_to_prs = {}
    for idx, entry in enumerate(prs):
        if not isinstance(entry, dict):
            errors.append(f"PR entry [{idx}] must be an object")
            continue
        number = entry.get("number")
        if isinstance(number, bool) or not isinstance(number, int):
            errors.append(f"PR entry [{idx}] missing integer 'number'")
            continue

        if entry.get("filesTruncated") is True or entry.get("files_truncated") is True:
            errors.append(f"PR #{number} reports truncated files list")
            continue
        if entry.get("filesComplete") is False or entry.get("files_complete") is False:
            errors.append(f"PR #{number} reports incomplete files list")
            continue

        if "files" not in entry or not isinstance(entry["files"], list):
            errors.append(f"PR #{number} missing required 'files' list")
            continue
        files = entry["files"]

        for count_key in ("changedFiles", "changed_files"):
            if count_key in entry and entry[count_key] is not None:
                declared = entry[count_key]
                if isinstance(declared, bool) or not isinstance(declared, int) or declared < 0:
                    errors.append(f"PR #{number} has invalid '{count_key}' value")
                elif declared > len(files):
                    errors.append(
                        f"PR #{number} files list truncated: got {len(files)} of {declared} ({count_key})"
                    )

        for f_idx, f_item in enumerate(files):
            paths, err = _extract_pr_file_paths(f_item, number, f_idx)
            if err is not None:
                errors.append(err)
                continue
            for p in paths:
                file_to_prs.setdefault(p, set()).add(number)

    if errors:
        return {}, errors
    return {p: sorted(nums) for p, nums in sorted(file_to_prs.items())}, []


def _decode_utf8_token(token, label):
    try:
        return token.decode("utf-8"), None
    except UnicodeDecodeError as exc:
        return None, f"{label} is not valid UTF-8: {exc}"


def parse_git_diff_name_status_z(raw_bytes):
    """Parse `git diff --name-status -z` bytes into structured entries covering old & new paths."""
    if not raw_bytes:
        return [], []
    tokens = raw_bytes.split(b"\x00")
    if tokens and tokens[-1] == b"":
        tokens.pop()

    entries = []
    errors = []
    i = 0
    while i < len(tokens):
        status, err = _decode_utf8_token(tokens[i], "git diff status token")
        i += 1
        if err is not None:
            errors.append(err)
            break
        if not status:
            errors.append("unexpected empty status token in git diff output")
            break
        code = status[0]
        if code in ("R", "C"):
            if i + 1 >= len(tokens):
                errors.append(f"truncated rename/copy record for status {status!r}")
                break
            old_path, old_err = _decode_utf8_token(tokens[i], f"git diff old path ({status})")
            new_path, new_err = _decode_utf8_token(tokens[i + 1], f"git diff new path ({status})")
            i += 2
            if old_err or new_err:
                errors.extend(e for e in (old_err, new_err) if e)
                break
            entries.append({"status": status, "paths": [old_path, new_path]})
        else:
            if i >= len(tokens):
                errors.append(f"truncated diff record for status {status!r}")
                break
            path, path_err = _decode_utf8_token(tokens[i], f"git diff path ({status})")
            i += 1
            if path_err:
                errors.append(path_err)
                break
            entries.append({"status": status, "paths": [path]})
    return entries, errors


def read_git_diff_paths(base_ref, head_ref="HEAD", repo=None):
    """Read changed paths (including rename old/new and deletions) via read-only git diff -z."""
    if not base_ref or base_ref.startswith("-"):
        return [], [f"invalid --git-diff-base ref: {base_ref!r}"]
    if not head_ref or head_ref.startswith("-"):
        return [], [f"invalid --git-diff-head ref: {head_ref!r}"]

    cmd = ["git"]
    if repo:
        cmd += ["-C", str(repo)]
    cmd += ["diff", "--name-status", "-z", f"{base_ref}...{head_ref}", "--"]
    try:
        proc = subprocess.run(cmd, capture_output=True)
    except FileNotFoundError:
        return [], ["git command not found"]
    except OSError as exc:
        return [], [f"failed to run git diff: {exc}"]

    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip() or "unknown git diff error"
        return [], [f"git diff failed (exit {proc.returncode}): {detail}"]

    entries, errors = parse_git_diff_name_status_z(proc.stdout)
    if errors:
        return [], errors

    paths = []
    for entry in entries:
        paths.extend(entry["paths"])
    return paths, []


def evaluate_boundaries(paths, file_to_prs):
    """Evaluate a sequence of paths against whitelist, redlines, and open PR file map."""
    seen = set()
    checked_paths = []
    redline_violations = []
    outside_whitelist = []
    invalid_paths = []
    pr_conflicts = []
    seen_conflict_paths = set()

    for raw in paths:
        res = classify_path(raw)
        key = (
            res["normalized"]
            if res["normalized"] is not None
            else ("__invalid__", type(raw).__qualname__, repr(raw))
        )
        if key in seen:
            continue
        seen.add(key)

        norm = res["normalized"]
        if norm is not None:
            checked_paths.append(norm)

        status = res["status"]
        if status == "redline":
            redline_violations.append(res)
        elif status == "outside_whitelist":
            outside_whitelist.append(res)
        elif status == "invalid":
            invalid_paths.append(res)

        if norm is not None and norm in file_to_prs and norm not in seen_conflict_paths:
            seen_conflict_paths.add(norm)
            pr_conflicts.append({"path": norm, "prs": file_to_prs[norm]})

    ok = not (redline_violations or outside_whitelist or invalid_paths or pr_conflicts)
    return {
        "ok": ok,
        "checkedPaths": checked_paths,
        "openPrFileCount": len(file_to_prs),
        "redlineViolations": redline_violations,
        "outsideWhitelist": outside_whitelist,
        "invalidPaths": invalid_paths,
        "prConflicts": pr_conflicts,
    }


def _load_json_input(source):
    try:
        if source == "-":
            raw = sys.stdin.read()
        else:
            raw = Path(source).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"failed to read {source!r}: {exc}"
    try:
        return json.loads(raw), None
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON in {source!r}: {exc}"


def _load_paths_file(source, null_separated=False):
    try:
        if source == "-":
            raw_bytes = sys.stdin.buffer.read()
        else:
            raw_bytes = Path(source).read_bytes()
    except OSError as exc:
        return [], f"failed to read paths file {source!r}: {exc}"

    if null_separated:
        tokens = raw_bytes.split(b"\x00")
        if tokens and tokens[-1] == b"":
            tokens.pop()
        paths = []
        for idx, token in enumerate(tokens):
            decoded, err = _decode_utf8_token(token, f"paths file {source!r} entry [{idx}]")
            if err is not None:
                return [], err
            paths.append(decoded)
        return paths, None

    text, err = _decode_utf8_token(raw_bytes, f"paths file {source!r}")
    if err is not None:
        return [], err
    return [line for line in text.splitlines() if line != ""], None


def build_parser():
    p = argparse.ArgumentParser(prog="check_routine_boundaries.py", description=__doc__)
    p.add_argument(
        "--open-prs",
        required=True,
        help="Path to open PR JSON file (or '-' for stdin). Required fail-closed input.",
    )
    p.add_argument(
        "--pr-limit",
        type=int,
        default=None,
        help="Pagination limit used when fetching a raw PR array; fails closed if count >= limit.",
    )
    p.add_argument(
        "--path",
        action="extend",
        nargs="+",
        default=[],
        help="Expected repo-relative file path(s) to check (repeatable).",
    )
    p.add_argument(
        "--paths-file",
        default=None,
        help="File containing expected repo-relative paths (newline-separated, or NUL with -z).",
    )
    p.add_argument(
        "-z",
        "--null",
        action="store_true",
        help="Treat --paths-file as NUL-separated instead of newline-separated.",
    )
    p.add_argument(
        "--paths-json",
        default=None,
        help="JSON file containing an array of expected repo-relative path strings.",
    )
    p.add_argument(
        "--git-diff-base",
        default=None,
        help="Base git ref for read-only `git diff --name-status -z <base>...<head>` check.",
    )
    p.add_argument(
        "--git-diff-head",
        default="HEAD",
        help="Head git ref for --git-diff-base (default: HEAD).",
    )
    p.add_argument(
        "--repo",
        default=None,
        help="Git repository directory for --git-diff-base (default: current directory).",
    )
    return p


def _emit_error(mode, errors):
    report = {
        "ok": False,
        "mode": mode,
        "checkedPaths": [],
        "openPrFileCount": 0,
        "redlineViolations": [],
        "outsideWhitelist": [],
        "invalidPaths": [],
        "prConflicts": [],
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    for msg in errors:
        sys.stderr.write(f"error: {msg}\n")
    return EXIT_ERROR


def main(argv=None):
    args = build_parser().parse_args(argv)

    has_explicit = bool(args.path or args.paths_file or args.paths_json)
    has_git_diff = args.git_diff_base is not None
    mode = "git-diff" if has_git_diff else "paths"

    if has_explicit and has_git_diff:
        return _emit_error(mode, ["cannot combine --git-diff-base with explicit path arguments"])
    if not has_explicit and not has_git_diff:
        return _emit_error(mode, ["must specify --git-diff-base or at least one of --path/--paths-file/--paths-json"])

    stdin_sources = sum(
        1 for s in (args.open_prs, args.paths_file, args.paths_json) if s == "-"
    )
    if stdin_sources > 1:
        return _emit_error(mode, ["stdin ('-') cannot be used for more than one input"])

    pr_data, pr_load_err = _load_json_input(args.open_prs)
    if pr_load_err is not None:
        return _emit_error(mode, [pr_load_err])

    file_to_prs, pr_errors = parse_open_prs(pr_data, pr_limit=args.pr_limit)
    if pr_errors:
        return _emit_error(mode, pr_errors)

    if has_git_diff:
        paths, diff_errors = read_git_diff_paths(args.git_diff_base, args.git_diff_head, repo=args.repo)
        if diff_errors:
            return _emit_error(mode, diff_errors)
    else:
        paths = list(args.path)
        if args.paths_file is not None:
            file_paths, pf_err = _load_paths_file(args.paths_file, null_separated=args.null)
            if pf_err is not None:
                return _emit_error(mode, [pf_err])
            paths.extend(file_paths)
        if args.paths_json is not None:
            json_paths, pj_err = _load_json_input(args.paths_json)
            if pj_err is not None:
                return _emit_error(mode, [pj_err])
            if not isinstance(json_paths, list):
                return _emit_error(mode, ["--paths-json must contain a JSON array of path strings"])
            paths.extend(json_paths)

    result = evaluate_boundaries(paths, file_to_prs)
    report = {"mode": mode, **result, "errors": []}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["ok"]:
        sys.stderr.write(
            "boundary check failed: "
            f"redline={len(report['redlineViolations'])}, "
            f"outside_whitelist={len(report['outsideWhitelist'])}, "
            f"invalid={len(report['invalidPaths'])}, "
            f"pr_conflicts={len(report['prConflicts'])}\n"
        )
        return EXIT_VIOLATION
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
