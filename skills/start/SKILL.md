---
name: start
description: 开始一个新的开发项：创建文档目录，撰写 PROMPT.md 和 PLAN.md，确认后再开始写代码
---

用户调用此 skill 表示要开始一个新的开发项。

**前置检查**：若 `AGENTS.md`、`CLAUDE.md` 与 `docs/DEVTREE.md` 都不存在，停下来提示用户先运行 `/bootstrap`，**不要**自己兜底建项目骨架。`/start` 只负责开新一轮开发，不负责项目首次初始化。

**参数处理**：调用时可能附带参数（args），参数有两种形态：

- **issue 驱动**（推荐）：参数是 `#<数字>` 或完整 issue URL：
  - GitHub: `https://github.com/owner/repo/issues/N`
  - GitLab: `https://gitlab.com/<namespace>/<project>/-/issues/N`（自托管把 host 换为对应实例域名）
  - 走「issue 驱动分支」（见下文）
- **自由描述**：参数是对需求的自由文字描述
  - 走「自由描述分支」（与原流程一致）

无参数 → 追问用户本次开发项的需求是什么或对应的 issue 号，拿到后再继续。

**`--no-worktree` 开关**：args 中可附带 `--no-worktree`（与 issue# ／自由描述正交，可与二者同时出现）。默认每轮在独立 git worktree 内开发；带此开关则跳过 worktree 创建、在当前分支直接干。解析需求内容前先把 `--no-worktree` 从 args 中剔除。适用场景：轻量改动 / 探索性 round / 不值得单开 worktree 的小修复。

按照全局 AGENTS.md 中的开发模式，严格遵循「执行前必须先完成 PROMPT.md 和 PLAN.md 的撰写并确认，再开始写代码」：

### 通用流程

1. **远端对齐**（`git fetch` + 撞车检查）。先于建 worktree 和文档执行。**任何一步失败都只提示、不阻断开轮**；**撞车信号任一命中就停下报告、等人类拍板**，别自己决定继续还是放弃。

   - **issue 驱动轮** → **读 `references/remote-align.md`**，按其三步走完（fetch → 三信号查这条是不是已经被做掉了 → 命中就停下报告）。
   - **自由描述轮** → 没有可查的 issue、撞车检查整体不适用，只跑一条 `git fetch origin` 把远端信号取回来供第 2 步编号用（无 `origin` 或 fetch 失败 → 打印一行原因、按本地三源算，继续开轮），不必读该文件。
2. **确定轮次编号 N**：以下五源中已占编号取并集，最大值 + 1；均为空从 0 开始：
   - 当前 `docs/<N>-*`；
   - 本地在途 `round<N>` / `round<N>-*` 分支；
   - `git worktree list --porcelain` 中其它工作树的 `docs/<N>-*`；
   - `git ls-tree --name-only origin/<主分支>:docs` 下的轮次目录；
   - 远端在途 `origin/round<N>` / `origin/round<N>-*` 分支。
   分支也识别可选 `codex/` 前缀；编号后描述可为历史中文。解析失败或不可达条目跳过。fetch 失败则不使用远端两源，明确说明只按本地三源编号。

3. **确定本轮中文描述**：issue 驱动 → 复用第 1 步已拉到的 issue 详情，从 issue 标题提炼简短中文描述；自由描述 → 从描述文字提炼。
4. **创建 worktree**（默认；带 `--no-worktree` 时跳过本步）—— **读 `references/worktree-create.md`** 按其执行（探测主分支 / 防嵌套 / 忽略 worktree 目录 / 撞号复核 / 创建 / 进入 / 告知 / 缺失的 gitignored 依赖怎么补）。两条硬约束先记住：分支名与 worktree 目录名统一为 `round<N>-<英文短描述>` 且**整串纯 ASCII**；**建之前必须复核这个 N 没被本地或远端占走**，占了就重算 N，别靠换个描述词绕开。
5. 在 `docs/` 下创建开发项文件夹 `docs/<N>-<中文描述>/`（worktree 模式下落在新 worktree 内）。
6. 基于参数撰写 `PROMPT.md`（两个分支具体行为见下）。
7. 撰写 `PLAN.md` 并请用户确认（CC 可进入计划模式；Codex 直接写计划并在对话中等待确认，无需模式切换工具） —— 见下方「PLAN 撰写：外部行为断言先实证」小节。
8. 用户确认后再开始写代码。

#### PLAN 撰写：外部行为断言先实证（通用流程第 7 步展开）

涉及数据丢失、拒绝条件、错误与副作用的关键外部行为假设，能用短小沙盘核实的先核实。记录结论、证据与可复现步骤，再据此设计。服务地址、凭据来源等只有用户知道且无权威来源的信息，不能靠试探补齐。用户明确的需求与查证结果不一致时，说明影响并确认方向。

### issue 驱动分支

参数命中 `#数字` 或上述任一平台的 issue URL 时：

1. **拉 issue 详情**（**与通用流程第 1 步「远端对齐」是同一次调用，不要调两遍**）：调 helper（自动按 `git remote get-url origin` 走 GitHub 或 GitLab）：

   ```bash
   python3 $HOME/.coding-agent/scripts/platform_issue.py issue-view <N>
   ```

   如参数是完整 URL，先从中提取 N。**本轮若需要往该 issue 补材料（spike 结论、实测数据），走 `issue-comment --issue <N> --body-file <F>`，别直调 `gh issue comment`。**

   helper stdout 是归一 json（GitHub 风格字段）：`number` / `title` / `body` / `url` / `labels` / `state` / `stateReason` —— 两端的字段名差异已在 helper 内抹平，本 SKILL 直接按这些名字读。**schema 与 `state` / `stateReason` 的取值语义，单一真源是 `scripts/platform_issue.md`，此处不复述**；本步只需记住一条结论：**判不出状态一律算 `open`**，失败方向定死在「照常开轮」。

2. **PROMPT.md 顶部**写一段引用块（让未来的人或 AI 一眼看到来源）：

   ```markdown
   > 来自 [#<N> <issue 标题>](<issue URL>)
   > Labels: `type:X` `area:Y` `priority:Z`
   ```

3. **PROMPT.md 主体**：把 issue body 内容作为「背景 / 需求」段的起点，AI 据此扩写完整的 PROMPT.md（可能基于 issue body 增补：约束、范围、待决问题等）。如 issue body 已足够完整，直接复用为主要内容。
4. 文件夹命名：从 issue 标题提炼简短中文描述，规则：`docs/<编号>-<中文描述>/`

### 自由描述分支

参数是文字描述时（非 issue 引用）：流程同原版。AI 基于参数撰写 PROMPT.md，文件夹命名从描述提炼。

> 提示：自由描述分支适合「轻量改动 / 探索性 round / 不需要长期追踪的开发项」。**长期可追踪的开发项推荐先 `/backlog` 创 issue，再 `/start <issue#>`**。
>
> 需求本身还模糊、要先讨论出方案 → 先走 `/design`，别硬开轮。若本轮落地的是某份 `docs/design/<主题>/DESIGN.md` 的一部分，在 `PROMPT.md` 顶部引用它（`> 依据方案 [<主题>](../design/<主题>/DESIGN.md)`）。
