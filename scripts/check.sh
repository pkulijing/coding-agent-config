#!/usr/bin/env bash
# 本仓统一验证入口：本地开发与 PR CI 共用。
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

uv run --frozen pytest
uv run --frozen python scripts/docs_lint.py
uv run --frozen python scripts/context_budget.py check-refs
