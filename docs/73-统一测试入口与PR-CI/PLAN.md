# 统一本仓测试入口与 PR CI

> 读者：维护 coding-agent-config 的开发者与自动化流程 · 如何在跨平台统一 Python 环境下运行全量回归测试并接入 PR CI
> 来源：[统一本仓测试入口，修复 Python 3.9 兼容性并接入 PR CI](https://github.com/pkulijing/coding-agent-config/issues/199) 及用户在本轮对话批准的修订方案（改用跨平台 uv 托管 Python，放弃兼容 macOS 系统 Python 3.9）

## 目标

为本仓建立单一、可复现的测试与检查入口，在 macOS、Ubuntu 24.04 与 GitHub Actions 上通过 uv 托管的同一 Python 版本运行全部仍有效的回归测试、文档检查和引用检查，并新增只读权限的 `pull_request` CI workflow。

## 关键决策

- **统一使用 uv 托管 Python，不兼容 macOS 系统 Python 3.9**：在 `.python-version` 钉死 `3.14.6`（经核实在当前 uv 下载目录与上游均覆盖 macOS arm64/x86_64 与 Linux x86_64/arm64），在根 `pyproject.toml` 声明 `[tool.uv] python-preference = "only-managed"` 与 `package = false`，并提交 `uv.lock`（使用标准 PyPI 索引源，避免 CI 依赖国内镜像）。不改写其他消费方项目的 Python 版本策略。
- **维护套件集中到 `tests/`，历史 `docs/` 原样保留**：将分散在 `docs/51`–`docs/69` 中仍有效的 10 份 Python 测试与 2 份 shell 沙盘测试迁入 `tests/` 统一维护，修复其相对仓库根路径及过时的调度器任务名（`com.coding-agent-config.auto-update`）与跨平台 UTF-8 locale（`C.UTF-8`）。保留历史 `docs/<N>-*` 目录不变；已退役的 `docs/53-*/test-agents-link.sh`（已删 `deploy_agent`）与 `docs/62-*/test-design-git.sh`（已退役 `/design`）不迁入现行门禁。
- **单一检查入口复用同一套验证**：根 `pyproject.toml` 设 `testpaths = ["tests"]` 防止误收集 `templates/` 测试；`tests/test_shell_suites.py` 将 3 份活跃 shell 沙盘测试（`tests/test_unlink_legacy.sh`、`tests/test_worktree_guard.sh`、`.github/scripts/ff-merge.test.sh`）与 `scripts/platform_issue.py --self-test` 纳入 `uv run --frozen pytest`；`scripts/check.sh` 串起 `pytest`、`docs_lint.py` 与 `context_budget.py check-refs`，本地与 CI 共用。
- **更新本仓活跃调用点为 `uv run`**：`skills/routine-slim/SKILL.md` 的 `context_budget.py check-refs`、`skills/routine-dev/SKILL.md` 的已知测试入口、`AGENTS.md` 与 `README.md` 均切到新的统一测试/检查命令。
- **只读 PR CI，不触碰合入路径**：新增 `.github/workflows/ci.yml`，声明 `permissions: contents: read`，`actions/checkout@v4` 使用 `fetch-depth: 0`（供 `test_context_budget.py` 核对历史标定提交 `38d3441`），运行 `bash scripts/check.sh`。不修改 `.github/workflows/ff-merge.yml`。

## 实施提纲

1. 新增 `.python-version`（`3.14.6`）、最小根 `pyproject.toml`（dev 依赖 `pytest` 与 `websockets==15.0.1`、`testpaths = ["tests"]`、`only-managed`）并用标准 PyPI 索引生成 `uv.lock`。
2. 将 10 份活跃 Python 测试和 2 份活跃 shell 测试迁入 `tests/`，修正仓库根路径、`test_scheduler_install.py` 的现行 label / `basename` / `C.UTF-8` locale，新增 `tests/test_shell_suites.py` 串联 shell 沙盘和 `platform_issue.py --self-test`。
3. 新增可执行入口 `scripts/check.sh` 与只读 workflow `.github/workflows/ci.yml`。
4. 更新 `AGENTS.md`、`README.md`、`skills/routine-dev/SKILL.md` 与 `skills/routine-slim/SKILL.md` 中的测试与 `context_budget.py` 调用入口。
5. 实跑 `bash scripts/check.sh`、`uv run --frozen pytest`，确认不收集 `templates/`、工作树干净、无真实 HOME 或远端副作用。

## 验收

- 在工作树内以 `bash scripts/check.sh` 一次跑通全部维护套件（含所有迁入的 Python 测试、3 份 shell 沙盘、`platform_issue.py --self-test`、`docs_lint.py` 与 `context_budget.py check-refs`），无模板测试误收集，无失败或静默跳过。
- 验证 `uv run --frozen python --version` 解析为 uv 托管的 `Python 3.14.6` 且不受系统 `/usr/bin/python3` 影响。
- 验证 `.github/workflows/ci.yml` 仅声明 `contents: read`、启用 `fetch-depth: 0`、不改动 `ff-merge.yml`，且 YAML 解析合法。
- 所有测试使用临时 HOME、临时仓库和工具桩，运行后主 checkout 与工作树无残留未跟踪文件。
