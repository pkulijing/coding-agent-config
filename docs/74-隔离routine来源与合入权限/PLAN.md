# Round 74：隔离 routine-dev 的需求来源与人工合入权限

> 读者：本仓维护者 · 需要了解公开仓库无人值守 `routine-dev` 的候选来源过滤与 GitHub 身份/合入权限隔离方案、边界与验证方式
> 来源：[Issue #200 — 隔离 routine-dev 的需求来源与人工合入权限](https://github.com/pkulijing/coding-agent-config/issues/200)

## 目标

为公开仓库上的无人值守 `routine-dev` 建立两层独立防线：

1. **需求来源过滤（Layer 1）**：在 `scripts/platform_issue.py` 与 `skills/routine-dev/` 中强制使用可信结构化作者元数据筛选仓库 owner 创建的候选 issue；作者字段缺失、不可靠、为 bot 或非 owner 时一律 fail-closed 拒收，覆盖本机 helper 与云端 GitHub MCP 入口。
2. **GitHub 身份与人工合入权限隔离（Layer 2）**：提供自动化身份边界检查脚本与最小权限独立身份部署方案（GitHub App 或独立 bot 协作者账号 + `master` 分支保护/Ruleset），并在受控沙盘中验证非 owner 自动化身份可推 `auto/*` 分支与开 PR、不能触发 `.github/workflows/ff-merge.yml` 且不能直推默认分支。真实凭据变更与 Ruleset 启用另行授权，未部署前不声称隔离已生效。

## 关键决策

- **把 owner 作者判定下沉到 `platform_issue.py` 纯函数与 CLI 选项**：与既有 `latest_owner_comment` 一致，不靠模型每次自行解析字段。已核实本机 `gh issue list --json` / `gh issue view --json` 暴露 `author` 而非顶层 `authorAssociation`，因此通过 `gh repo view --json owner` 获取权威仓库 owner（不信任本地 git remote URL），与 `author.login` 做大小写不敏感比对并拒绝 `is_bot == True` 或空值。
- **`issue-list --owner-only` 同时做服务端过滤与本地二次校验**：GitHub 侧向 `gh issue list` 追加 `--author <repo_owner>` 防止大量外部 issue 挤出 `--limit` 分页上限，再在本地对返回结果逐条执行 `classify_issue_author` 复核，保证缺失/畸形元数据 fail-closed。
- **GitLab 侧 `--owner-only` 显式 fail-closed**：本机未安装/未实测 `glab` 的仓库 owner 与 issue 作者结构，调用 `--owner-only` 直接报错返回非零，不静默放行。
- **区分独立非 owner 身份与 owner 名下 Fine-Grained PAT**：owner 个人名下的 Fine-Grained PAT 仍以 `sender.login == repository_owner` 身份认证，且 `pull_requests: write` 允许评论/打标 PR，无法阻断 `ff-merge.yml`。因此隔离方案明确要求使用独立身份（推荐 GitHub App `<app>[bot]`，备选独立 bot 协作者账号）+ `master` 分支保护/Ruleset 禁止直推默认分支。
- **不修改真实线上凭据，但交付可验证的身份预检与受控沙盘**：新增 `scripts/check_routine_identity.py` 检查当前 `gh` 身份与 `repository_owner` 的关系（`isolated` / `shared_owner` / `unknown`），并在 pytest + 沙盘裸仓中验证三项行为契约；文档明确标注部署前隔离尚未在线上生效。

## 实施提纲

1. **Layer 1 — `scripts/platform_issue.py` 与 `scripts/platform_issue.md`**：
   - `build_issue_view_cmd` / `build_issue_list_cmd` 在 GitHub `--json` 字段中加入 `author`；`normalize_issue` 归一输出 `author`（缺失为空字符串），不破坏既有消费方。
   - 新增 `classify_issue_author(raw_issue, repo_owner)`（返回 `"owner" | "non_owner" | "unknown"`）、`filter_owner_issues`、`fetch_repo_owner`；为 `issue-list` 增加 `--owner-only`，为 `issue-view` 增加 `--require-owner`（非 owner/来源不明时返回非零退出码并在 stderr 说明原因）。
   - 更新 `scripts/platform_issue.md` 与 `--self-test`。
2. **Layer 2 — `scripts/check_routine_identity.py` 与部署/边界文档**：
   - 新增 `scripts/check_routine_identity.py`：通过 `gh api user`（或 `gh auth` / `gh repo view --json owner`）比对当前认证身份与目标仓库 owner，输出结构化 JSON 状态（`isolated` / `shared_owner` / `unknown`），并支持 `--require-isolated` 供受控/已隔离环境强校验。
   - 在 `skills/routine-dev/references/security-boundary.md` 增补两层防线说明、平台能力核对（本机/CI 可注入 GitHub App 或独立 bot 凭据，claude.ai Routines 若共用 owner OAuth 则隔离未生效）及最小权限配置步骤（GitHub App + `master` Ruleset）。
3. **更新 `skills/routine-dev/SKILL.md` 与相关文档**：
   - Step 0 / Step 1.1 / 提 PR 前最终复核强制 owner 作者过滤（本机走 `issue-list --no-body --owner-only` 与 `issue-view <N> --with-comments --require-owner`，云端 MCP 核对结构化作者元数据且缺失即拒收）。
   - Step 0 / Step 3 增加身份隔离状态核验与如实报告要求；明示作者筛选不把正文/评论变成可信指令，也不替代权限隔离。
4. **测试与验证**：
   - 新增 `tests/test_issue_owner_filter.py`：用隔离 fixture 覆盖 owner / 非 owner / 来源不明（缺失、空值、畸形、bot）/ 大小写 / repo owner 查询失败 / GitLab fail-closed。
   - 新增 `tests/test_routine_identity.py`：覆盖 `check_routine_identity.py` 各状态分支，并在隔离临时裸仓 + 桩 `gh` 环境中验证：① 独立自动化身份可推送 `auto/*` 分支并创建 PR；② `ff-merge.yml` 准入条件拒绝非 owner 发起的 `ff-merge` label 与 `/ff` 评论；③ 分支保护 `pre-receive` hook 阻止自动化身份直推 `master` 而放行 `auto/*`。
   - 运行 `bash scripts/check.sh`。

## 验收

- `tests/test_issue_owner_filter.py` 覆盖 owner / 非 owner / 来源不明三类输入及 `--owner-only`、`--require-owner` 的 fail-closed 行为。
- `tests/test_routine_identity.py` 在受控沙盘中验证非 owner 自动化身份可推分支提 PR、无法触发 `ff-merge.yml`、无法直推默认分支。
- `bash scripts/check.sh` 全绿（含 `pytest`、`platform_issue.py --self-test`、`docs_lint.py`、`context_budget.py check-refs`）。
- 文档明确说明未完成真实凭据与分支保护部署前，不宣称凭据隔离已在线上生效。
