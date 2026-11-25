---
name: commit
description: 按照 git 规则自动分析变更并提交代码
---

用户调用此 skill 表示要提交当前的代码变更。按照全局 AGENTS.md 中的 git 规则执行以下步骤：

**提交粒度**：以可独立审阅、回退和说明目的的交付单元提交。独立功能、修复、隔开的交付、必要部署与验收记录可分别提交；同一次可连续完成的收尾先汇齐适用文档，不把“已获授权”“准备合入”等对话状态各做一次提交。影响判断的新事实、已发布或被引用的记录、审计与恢复点可独立保留，不机械限制一轮提交数。优先避免产生新碎片；普通提交不因此自动 amend、squash 或改写已发布/共享历史，历史整理仍须核对范围、备份与授权。

1. 运行 `git status` 查看当前变更状态
2. 运行 `git diff` 查看具体变更内容（包括已暂存和未暂存的）
3. 运行 `git log --oneline -5` 了解近期 commit 风格
4. **提交前 review loop**：调 `/review-loop` 对当前工作树跑自动 review 迭代，**迭代到 clean 才继续往下**。判据与降级链**以 `/review-loop` 为单一真源**，本步不复述。两点本步需要知道的：① 它可能以「2 轮未收敛留痕放行」返回，此时会给出一行标注，第 7 步必须原样写进 message body；② **放在 lint 之前**，因为它会自动改代码，须让下一步 lint 覆盖到这些修复。
5. **commit 前 lint 检查**（在 review 修复后执行）：
   - 逐条判定下表，命中几条跑几条：
     - Python + uv: 见到 `pyproject.toml` + `[tool.ruff]` 配置 → `uv run ruff check .`
     - Python（其他）: 见到 `pyproject.toml` 含 ruff/flake8/pylint → 用对应工具
     - Node.js: `package.json` 里有 `scripts.lint` → `npm run lint`（或 `yarn lint` / `pnpm lint`）；monorepo 要覆盖全部包：`npm run lint --workspaces` / `pnpm -r lint`（yarn 的 classic 与 berry 写法不同，用前先查）
     - Rust: `Cargo.toml` → `cargo clippy --all-targets -- -D warnings`
     - Go: `go.mod` → `go vet ./...`
     - 文档形状: 仓库根有 `scripts/docs_lint.py` → `python3 scripts/docs_lint.py`（含单独提交的计划文档）
     - **一条都没命中**（或命中但工具配置缺失）→ **跳过这一步**，继续往下走
   - **本轮引入、修复方式明确且不改变已确认方案的 lint 错误**：自主修复，重跑 lint 和受影响验证；修改后的 diff 须按第 4 步既有 review 契约复审（轮次与上限以 `/review-loop` §6.4 为真源，本步不复述）；review 若再修文件，则重新执行本步。**审查环已停环（满 2 轮或提前振荡）时不自动修**：lint 仍未通过就按失败出口中止提交并报告，不带未审改动进提交。
   - 原有无关问题、归属不明的改动、需要方向性取舍或无法在上述范围内修复的失败：暂停提交，集中报告错误、影响与可选方案，等用户决定；无人值守按调用技能的失败出口处理。
   - 未经用户明示授权，不得用 `--no-verify`、关闭规则或修改检查范围等方式绕过门禁。
6. **探测轮次 N**（决定是否加 `[round N]` 前缀，给跨轮追溯补一层约束）：
   - **主信号**：当前分支名匹配 `^(?:codex/)?round(\d+)(-|$)` → 取第一个捕获组为 N（兼容带或不带 `codex/` 的 round 分支）。
   - **兜底**（`--no-worktree` 等非 round 分支）：看本次变更涉及的文件里有没有 `docs/<N>-*` 路径（计划目录或旧轮次路径；`git diff --cached --name-only` 与 `git status --porcelain` 的并集），命中唯一的 `<N>` 则取之。
   - 两路都判不出 N → **不加前缀**，走普通 commit，不要硬凑。
7. 分析所有变更，生成 commit message：
   - 使用中文
   - 遵循 semantic commit message 规则（如 `feat:`, `fix:`, `refactor:` 等）
   - **若第 6 步探出 N**：在 semantic message 最前面加 `[round N] ` 前缀，形如 `[round 3] feat(skill): 支持 xxx`
   - **若第 4 步 `/review-loop` 以「未收敛留痕」放行**：在 message body 追加其给出的标注行（形如 `Review: 2 轮未收敛，遗留 N 条 finding`，其后紧跟 review-loop 给出的「未收敛遗留」正文），不得省略——这是遗留问题在 `/finish` 前唯一的显式可见性
   - **若第 4 步 `/review-loop` 走了降级路径**（Step 5 的第 ② 或 ③ 档）：在 message body 追加一行标注，**照抄该档在 Step 5 里的措辞**（② 按实际保住的属性报告，不能把已固定的 effort 写成丢失；③ 写「未经独立 context 把关」），**并附降级证据**（那次调用失败的实际表现 / 工具确实不在列表）——只写结论不算数，写不出证据说明本就不该降级
   - 简明扼要，聚焦于「为什么」而非「改了什么」
8. 将相关文件添加到暂存区（优先按文件名添加，避免 `git add -A`）
9. 执行提交，commit message 末尾必须**按当前执行的 Agent** 追加正确的 `Co-authored-by` trailer（详见全局 AGENTS.md「git 规则」）：
   - CC（Claude Code）执行 → `Co-authored-by: Claude <noreply@anthropic.com>`
   - Codex（OpenAI Codex）执行 → `Co-authored-by: OpenAI Codex <noreply@openai.com>`
   - DSH（DeepSeek Harness）执行 → `Co-authored-by: DeepSeek Harness <noreply@localhost>`
   - Antigravity（Google Antigravity）执行 → `Co-authored-by: Google Antigravity <noreply@google.com>`
   - **判据**：你知道自己是哪个 Agent，据此选身份；**不写其他 Agent 的身份**。
10. 运行 `git status` 确认提交成功
