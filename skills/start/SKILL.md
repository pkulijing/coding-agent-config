---
name: start
description: 正式开发先在原生 Plan 模式调查和讨论，方案获批后才建工作树、保存 PLAN.md 并实施
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

### 先规划并批准

1. 已有同一任务在原生 Plan 模式形成并获用户批准的完整计划，且当前模式允许实施，直接进入下节。否则先核实客户端当前模式。CC 有原生进入工具时调用；Codex、DSH 及其他客户端按实际可用入口切换。需用户操作时提示在当前聊天选择 Plan 模式（支持时输入 `/plan`），停在这里，待实际切换再继续。
2. 规划阶段只调查和讨论。issue 驱动时先读取需求（见下文）。从真实入口追踪当前行为、已有实现和相关测试；涉及数据丢失、拒绝条件或副作用的关键外部假设，用隔离的短小实验核实。需求未收敛可逐步讨论，能查清的信息自行调查。
3. 提交完整原生计划。摘要先说明现状、拟改行为、关键取舍和怎样验证，再给实施提纲。用户反馈修改就继续规划；只讨论或搁置则停在聊天里。用户批准当前版本或选择客户端实施按钮，且客户端已允许执行后进入实施。退出模式本身不能作为批准。

### 批准后开轮

1. **远端对齐**（`git fetch` + 撞车检查）。先于建 worktree 和轮次记录执行。**任何一步失败都只提示、不阻断开轮**；**撞车信号任一命中就停下报告、等人类拍板**，别自己决定继续还是放弃。

   - **issue 驱动轮** → **读 `references/remote-align.md`**，按其三步走完（fetch → 三信号查这条是不是已经被做掉了 → 命中就停下报告）。
   - **自由描述轮** → 没有可查的 issue、撞车检查整体不适用，只跑一条 `git fetch origin` 把远端信号取回来供第 2 步编号用（无 `origin` 或 fetch 失败 → 打印一行原因、按本地三源算，继续开轮），不必读该文件。
2. **确定轮次编号 N**：以下五源中已占编号取并集，最大值 + 1；均为空从 0 开始：
   - 当前 `docs/<N>-*`（目录和旧单文件都算）；
   - 本地在途 `round<N>` / `round<N>-*` 分支；
   - `git worktree list --porcelain` 中其它工作树的 `docs/<N>-*`；
   - `git ls-tree --name-only origin/<主分支>:docs` 下的轮次条目；
   - 远端在途 `origin/round<N>` / `origin/round<N>-*` 分支。
   分支也识别可选 `codex/` 前缀；编号后描述可为历史中文。解析失败或不可达条目跳过。fetch 失败则不使用远端两源，明确说明只按本地三源编号。

3. **确定本轮中文描述**：issue 驱动 → 复用第 1 步已拉到的 issue 详情，从 issue 标题提炼简短中文描述；自由描述 → 从描述文字提炼。
4. **创建 worktree**（默认；带 `--no-worktree` 时跳过本步）—— **读 `references/worktree-create.md`** 按其执行（含 Codex 托管创建后建立项目内软链接入口）。项目内入口名为 `round<N>-<英文短描述>`，分支同名（Codex 加 `codex/` 前缀），且**整串纯 ASCII**；**建之前必须复核这个 N 没被本地或远端占走**，占了就重算 N，别靠换个描述词绕开。
5. 在本轮工作树将批准的完整计划保存到 `docs/<N>-<中文主题>/PLAN.md`。标题下写 `> 读者：<谁> · <什么问题>` 和 `> 来源：<issue 链接或需求来源>`，正文包含 `## 目标`、`## 关键决策`（含理由）、`## 实施提纲`、`## 验收`。保留批准版的具体范围、取舍和验收场景；将文件随代码提交。每个正式轮次只创建这一份过程文档。

6. 按批准版实施。若发现必须改变已批准的用户可见行为，向用户说明影响、确认调整，再同步更新同一份计划。
7. 进入实施时，Codex 更新当前会话标题：先检查 `~/.coding-agent/scripts/codex_session_title.py` 可读、`uv` 可用且 `uv run --script <脚本路径> --help` 可执行，再运行 `uv run --script <脚本路径> start --round <N> --description '<本轮中文描述>'`，标题为 `r<N>-<中文描述>`。描述按 shell 参数正确转义；非 Codex 不调用。脚本使用 `CODEX_THREAD_ID` 定位当前会话；调用失败明确报告，不阻断开发，不改聊天记录兜底。仅生成方案时不改名。

### issue 驱动分支

参数命中 `#数字` 或上述任一平台的 issue URL 时：

1. **拉 issue 详情**（规划阶段读取需求；批准后在远端对齐步骤重新读取当前状态和关闭原因）：调 helper（自动按 `git remote get-url origin` 走 GitHub 或 GitLab）：

   ```bash
   python3 $HOME/.coding-agent/scripts/platform_issue.py issue-view <N>
   ```

   如参数是完整 URL，先从中提取 N。**进入实施后，若已获授权向该 issue 补材料（spike 结论、实测数据），走 `issue-comment --issue <N> --body-file <F>`，别直调 `gh issue comment`。**

   helper stdout 是归一 json（GitHub 风格字段）：`number` / `title` / `body` / `url` / `labels` / `state` / `stateReason` —— 两端的字段名差异已在 helper 内抹平，本 SKILL 直接按这些名字读。**schema 与 `state` / `stateReason` 的取值语义，单一真源是 `scripts/platform_issue.md`，此处不复述**；本步只需记住一条结论：**判不出状态一律算 `open`**，失败方向定死在「照常开轮」。

2. 把 issue 标题与 URL 写进批准版计划的来源行。自由描述任务的来源写「与用户对话」及需求摘要。已有设计稿可作为来源引用。
