#!/usr/bin/env bash
# 两端 PostToolUse：尽力自动修复，最终门禁仍由 /commit 执行。
# 仅解析编辑事件中的路径，绝不执行 tool_input.command。
set -u

PAYLOAD=$(cat)
EVENT_CWD=$(printf '%s' "$PAYLOAD" | jq -r '.cwd // empty' 2>/dev/null) || exit 0
[ -d "$EVENT_CWD" ] || EVENT_CWD="$PWD"

while IFS= read -r FILE; do
    [ -n "$FILE" ] || continue
    case "$FILE" in
        /*) ;;
        *) FILE="$EVENT_CWD/$FILE" ;;
    esac
    [ -f "$FILE" ] || continue
    # 从目标文件所在项目启动工具，避免绝对路径编辑另一工作树时使用会话主树的配置。
    PROJECT_DIR=$(git -C "$(dirname "$FILE")" rev-parse --show-toplevel 2>/dev/null) || PROJECT_DIR="$(dirname "$FILE")"
    case "$FILE" in
        *.py)
            # 分步编辑期间保留尚未使用的 import，F401 留给提交门禁。
            (cd "$PROJECT_DIR" && uv run --quiet ruff check --fix --unfixable F401 --quiet "$FILE") >/dev/null 2>&1
            (cd "$PROJECT_DIR" && uv run --quiet ruff format "$FILE") >/dev/null 2>&1
            ;;
        *.md)
            command -v prettier >/dev/null 2>&1 && \
                (cd "$PROJECT_DIR" && prettier --write --log-level warn "$FILE") >/dev/null 2>&1
            ;;
    esac
done < <(printf '%s' "$PAYLOAD" | jq -r '
    if (.tool_input.file_path | type) == "string" then
        [.tool_input.file_path]
    elif .tool_name == "apply_patch" and (.tool_input.command | type) == "string" then
        [.tool_input.command | split("\n")[]
         | select(test("^\\*\\*\\* (Add File|Update File|Move to): "))
         | sub("^\\*\\*\\* (Add File|Update File|Move to): "; "")]
    else [] end | unique[]
' 2>/dev/null)
exit 0
