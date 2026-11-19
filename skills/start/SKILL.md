---
name: start
description: 开始一个新的开发项：对齐远端与编号、建工作树、落一份 ≤15 行轮次记录，目标明确时直接实施
---

用户调用此 skill 表示要开始一个新的开发项。

**前置检查**：若 `AGENTS.md` 与 `CLAUDE.md` 都不存在，停下来提示用户先运行 `/bootstrap`，**不要**自己兜底建项目骨架。`/start` 只负责开新一轮开发，不负责项目首次初始化。

**参数处理**：调用时可能附带参数（args），参数有两种形态：

- **issue 驱动**（推荐）：参数是 `#<数字>` 或完整 issue URL：
  - GitHub: `https://github.com/owner/repo/issues/N`
  - GitLab: `https://gitlab.com/<namespace>/<project>/-/issues/N`（自托管把 host 换为对应实例域名）
  - 走「issue 驱动分支」（见下文）
- **自由描述**：参数是对需求的自由文字描述
  - 走「自由描述分支」

无参数 → 追问用户本次开发项的需求是什么或对应的 issue 号，拿到后再继续。

**`--no-worktree` 开关**：args 中可附带 `--no-worktree`（与 issue# ／自由描述正交，可与二者同时出现）。默认每轮在独立 git worktree 内开发；带此开关则跳过 worktree 创建、在当前分支直接干。解析需求内容前先把 `--no-worktree` 从 args 中剔除。适用场景：轻量改动 / 探索性 round / 不值得单开 worktree 的小修复。

**本 skill 不写方案文档**：方案在对话里对齐即可，不产出 `PROMPT.md`、`PLAN.md`，也不写分步计划。只有用户要求先看方案、或当前处于计划模式时，才在对话里给出并停在计划。

### 通用流程

1. **远端对齐**（`git fetch` + 撞车检查）。先于建 worktree 和轮次记录执行。**任何一步失败都只提示、不阻断开轮**；**撞车信号任一命中就停下报告、等人类拍板**，别自己决定继续还是放弃。

   - **issue 驱动轮** → **读 `references/remote-align.md`**，按其三步走完（fetch → 三信号查这条是不是已经被做掉了 → 命中就停下报告）。
   - **自由描述轮** → 没有可查的 issue、撞车检查整体不适用，只跑一条 `git fetch origin` 把远端信号取回来供第 2 步编号用（无 `origin` 或 fetch 失败 → 打印一行原因、按本地三源算，继续开轮），不必读该文件。
2. **确定轮次编号 N**：以下五源中已占编号取并集，最大值 + 1；均为空从 0 开始：
   - 当前 `docs/<N>-*`（单文件或历史目录都算）；
   - 本地在途 `round<N>` / `round<N>-*` 分支；
   - `git worktree list --porcelain` 中其它工作树的 `docs/<N>-*`；
   - `git ls-tree --name-only origin/<主分支>:docs` 下的轮次条目；
   - 远端在途 `origin/round<N>` / `origin/round<N>-*` 分支。
   分支也识别可选 `codex/` 前缀；编号后描述可为历史中文。解析失败或不可达条目跳过。fetch 失败则不使用远端两源，明确说明只按本地三源编号。

3. **确定本轮中文描述**：issue 驱动 → 复用第 1 步已拉到的 issue 详情，从 issue 标题提炼简短中文描述；自由描述 → 从描述文字提炼。
4. **创建 worktree**（默认；带 `--no-worktree` 时跳过本步）—— **读 `references/worktree-create.md`** 按其执行（含 Codex 托管创建后建立项目内软链接入口）。项目内入口名为 `round<N>-<英文短描述>`，分支同名（Codex 加 `codex/` 前缀），且**整串纯 ASCII**；**建之前必须复核这个 N 没被本地或远端占走**，占了就重算 N，别靠换个描述词绕开。
5. **落轮次记录** `docs/<N>-<中文描述>.md`（单文件，≤15 行，写在 worktree 内）：

   ```markdown
   # <中文描述>

   > 读者：接手这条分支的人 · 这轮要解决什么、什么算完成
   > 来源：[#N <issue 标题>](<issue URL>)   ← 自由描述轮写「与用户对话」
   > 完成标准：<可验证的一句话>
   ```

   有高代价且非显然的决策时另起 `docs/adr/<NNNN>-<slug>.md`，不在轮次记录里扩写；落 ADR 后在轮次记录补一行 `> 决策：[ADR NNNN](adr/NNNN-<slug>.md)`。**不建 `PROMPT.md` / `PLAN.md` / `SUMMARY.md`**，也不建 `assets/`：可复用材料放项目里的正式位置（`tests/`、`scripts/`、文档正文）。

6. **进实施前先实证关键外部行为断言**：涉及数据丢失、拒绝条件、错误与副作用的关键假设，能用短小沙盘核实的先核实。结论与证据留在对话和代码里，不写进文档。服务地址、凭据来源等只有用户知道且无权威来源的信息，不能靠试探补齐。用户明确的需求与查证结果不一致时，说明影响并确认方向。
7. 进入实施时，Codex 更新当前会话标题：先检查 `~/.coding-agent/scripts/codex_session_title.py` 可读、`uv` 可用且 `uv run --script <脚本路径> --help` 可执行，再运行 `uv run --script <脚本路径> start --round <N> --description '<本轮中文描述>'`，标题为 `r<N>-<中文描述>`。描述按 shell 参数正确转义；非 Codex 不调用。脚本使用 `CODEX_THREAD_ID` 定位当前会话；调用失败明确报告，不阻断开发，不改聊天记录兜底。仅生成方案时不改名。

### issue 驱动分支

参数命中 `#数字` 或上述任一平台的 issue URL 时：

1. **拉 issue 详情**（**与通用流程第 1 步「远端对齐」是同一次调用，不要调两遍**）：调 helper（自动按 `git remote get-url origin` 走 GitHub 或 GitLab）：

   ```bash
   python3 $HOME/.coding-agent/scripts/platform_issue.py issue-view <N>
   ```

   如参数是完整 URL，先从中提取 N。**本轮若需要往该 issue 补材料（spike 结论、实测数据），走 `issue-comment --issue <N> --body-file <F>`，别直调 `gh issue comment`。**

   helper stdout 是归一 json（GitHub 风格字段）：`number` / `title` / `body` / `url` / `labels` / `state` / `stateReason` —— 两端的字段名差异已在 helper 内抹平，本 SKILL 直接按这些名字读。**schema 与 `state` / `stateReason` 的取值语义，单一真源是 `scripts/platform_issue.md`，此处不复述**；本步只需记住一条结论：**判不出状态一律算 `open`**，失败方向定死在「照常开轮」。

2. 把 issue 标题与 URL 写进第 5 步轮次记录的「来源」行；issue body 作为本轮背景进上下文，**不转抄成文档**。body 已足够完整时直接据此实施；有缺口就在实施前集中询问，不靠扩写文档补齐。

### 自由描述分支

参数是文字描述时：「来源」行写「与用户对话」加一句需求摘要，其余同上。

> 提示：自由描述分支适合「轻量改动 / 探索性 round / 不需要长期追踪的开发项」。**长期可追踪的开发项推荐先 `/backlog` 创 issue，再 `/start <issue#>`**。
>
> 需求本身还模糊、要先讨论出方案 → 先走 `/design`，别硬开轮。若本轮落地的是某份 `docs/design/<主题>.md` 的一部分，在轮次记录的「来源」行引用它（`> 依据方案 [<主题>](design/<主题>.md)`）。
