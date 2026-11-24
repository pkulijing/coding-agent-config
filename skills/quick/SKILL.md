---
name: quick
description: 局部小改自主调查、验证、review 并提交，支持无人交互、可选分支或工作树，免编号及计划文件
---

用户调用此 skill 表示要走**轻量开发流**：一个很小的需求（如改一个小函数、修个笔误、调一处配置），不值得引入 `/start` + `/finish` 的轮次记录与收尾流程，只要在 commit message 里把「改了啥、为什么」说清楚即可。

## 前置判断：这个需求真的适合 `/quick` 吗

调用即授权本次局部小改。在当前执行模式中先查真实入口、已有行为与受影响测试，确定简短步骤和验证方式。无需启动 Plan 模式或请求计划批准；若客户端已在原生 Plan 模式，遵守其执行约束，只返回当前可完成的规划结果。

需要跨模块重构、存在实质方向分歧或需要正式轮次跟踪时，返回「超出 /quick 范围」并说明理由，结束本次调用。由调用方决定是否改走 /start；自动化可据此跳过或报告。

## 参数解析

args 可含以下项（`--worktree` 已包含独立分支，不能与 `--branch` 重复创建），解析后剩余文字即本次小改动的需求描述：

- **`--worktree`**：按 [轻量 worktree](references/worktree.md) 建独立工作树和 `codex/quick/<ascii 短描述>` 分支；不建开发文档，提交后保留工作树与分支供审阅。
- **`--branch`**：切一个轻量分支 `codex/quick/<ascii 短描述>`（**不建 worktree**），改完 commit 留在该分支等用户手动合 / 提 PR。默认不带 = 在当前分支直接改。
- **`#<issue 号>` 或 issue URL**：两层用途——① **拉 issue 详情用于理解本次要改什么**，进工作上下文指导改动（这样你传 `#N` 就不必再口述一遍需求）；② issue 号进收尾 commit 的 `Closes #N`。**详情只进上下文、不落成文档**（简易流不留档）；可传多个。
- **剩余文字**：需求描述。

**拉 issue 详情**（仅当传了 `#N` / URL）：走 helper `python3 $HOME/.coding-agent/scripts/platform_issue.py issue-view <N>`（按 `git remote get-url origin` 自动判定 GitHub / GitLab），从返回的 `title` / `body` 理解要改什么。传多个则逐个拉。URL 形态先从中提取 N。

无描述**且**未传 `#N`（即既无口述需求、又无 issue 可拉）且无法从对话上下文推断要改什么 → 交互时询问需求；无人交互时返回缺少需求并结束。

## Step 1：（可选）隔离工作区

**args 含 `--worktree`**：先执行 [轻量 worktree](references/worktree.md) 的创建流程，再在返回的真实路径内执行后续步骤；跳过下方 `--branch` 和默认分支路径。

**仅当 args 含 `--branch`**：

- 探测主分支：`git symbolic-ref --short refs/remotes/origin/HEAD`（仅剥掉 `origin/` 前缀）；失败则本地探测 `main` / `master`。
- 若已有未提交改动会随切分支带走，交回调用方说明原因；无人交互时结束本次调用。
- `git switch -c codex/quick/<ascii 短描述>`（从当前 HEAD 切，**不建 worktree**）。短描述从需求描述提炼，**命名规格同 `/start`，见 `~/.coding-agent/skills/start/references/worktree-create.md`「短描述规格」条**，此处不复述。

**默认（不带 `--branch`）**：跳过本步，在当前所在分支直接改。若当前分支就是主分支（`master` / `main`），**允许**——简易流小改直提主分支是合理的，但打印一行提示让用户知情（「将在主分支 `<主分支>` 上直接改并提交」），提示后继续执行。

## Step 2：直接实现

按已确定的步骤实施并运行受影响测试或实际入口验证，然后进入提交前 review。小改不建立轮次文档。

- **规则不豁免**：命中语言 / 栈触发条件时照常先 Read 对应 `playbooks/*.md`（Python / 前端 / ROS 2 / shell / lark）—— 简易流省的是「文档仪式」，不是「代码规范」。
- 把「为什么这么改」的关键信息记住，供 Step 3 的 commit message 用（commit message 承载「为什么」，代码本身说清「做了什么」）。
- 若确有必要，可加一行行内注释解释非显然的设计动机（写「当前真相」，不写「本轮 / issue #N」这类演化历史标记）。

## Step 3：收尾 —— 调用 `/commit`

调用 `/commit` 提交（继承其 lint 门禁 / semantic commit message / Co-authored-by trailer，单一真源不重复实现）：

- **若解析出 `#N`**：把 `Closes #N` 作为额外上下文传给 `/commit`，让 message body 自然包含（不嵌入 title）。**关多个 issue 时每个 `#N` 各占一行、各带 `Closes` 关键字**（`Closes #13` / `Closes #20` / …），**绝不写成 `Closes #13 #20`** —— 这条硬规则连同它的代价，单一真源在 `~/.coding-agent/skills/finish/SKILL.md` Step 3。
- **`[round N]` 前缀天然不加**：`/quick` 默认既不建 `round<N>` 分支、也不建编号计划目录 → `/commit` 的两路轮次探测都判不出 N → 走普通 commit、不加前缀。**这是预期行为**（简易流本就不进轮次追踪），无需干预。

## Step 4：轻量收尾提示

打印一行收尾提示，按分支策略分岔：

- **`--worktree`**：输出项目内入口、真实路径、分支与提交；保留供审阅，不自动合入或推送。
- **`--branch`**：「改动已提交到 `codex/quick/<ascii 短描述>` 分支，review 后自行 merge / 提 PR。」
- **默认**：「已提交到当前分支 `<分支名>`，是否 `git push` 由你决定。」（与全局不自动 push 的约定一致。）


## 明确不做（与 `/finish` 的边界）

`/quick` **一概不碰**以下重流程独有的仪式 —— 要这些就走正规 `/start` + `/finish`：

- 不写轮次记录与 ADR
- 不做跨项目可沉淀流程反思、不向 coding-agent-config 提 issue
- 不调 `/devtree`（已冻结）
- 不做 README review & update
- 不主动做 issue 生命周期管理；`/quick` 只在你显式传 `#<issue>` 时顺手在 commit 带 `Closes #N`，不替你去改 issue 状态
- 不自动 rebase / FF merge；`--worktree` 的保留与显式清理按 [轻量 worktree](references/worktree.md)。
