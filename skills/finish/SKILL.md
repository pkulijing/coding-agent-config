---
name: finish
description: 完成当前开发项：撰写 SUMMARY.md、更新开发树与相关 README、关联 issue、提交并收尾 worktree。发现有具体跨项目价值的候选时，经确认提 issue。
---

用户调用此 skill 表示当前开发项已完成，并默认授权清理本轮 worktree、本地开发分支及本轮 backup tag；无需再询问是否清理。明确要求保留的对象除外，未合入成果与未保全资产仍按收尾细则保护。

**参数处理**：先解析下列**收尾开关**及明确的保留指令（如“不要清理”等同 `--no-cleanup`），再将剩余 args 当作用户对本次开发的额外说明（撰写 SUMMARY.md 时融入「局限性」「后续 TODO」「关键设计」等章节；无剩余则按常规总结）。用户最新明确的保留要求优先于默认清理。

**收尾开关**（控制 Step 7，可组合；不带任何开关时，目标为 rebase + FF merge + 默认清理 worktree、分支与 backup tag；合入与 push 仍按各自授权边界执行）：

| 调用 | 7.2 rebase + 备份 tag | 7.3 FF merge | 删 worktree | 删分支 | 删 backup tag |
| --- | --- | --- | --- | --- | --- |
| `/finish`（默认） | ✓ | ✓ | ✓ | ✓ | ✓ |
| `--no-merge` / `--keep-branch` | ✓ | ✗ | ✓ | ✗ | ✗ |
| `--keep-backup` | ✓ | ✓ | ✓ | ✓ | ✗ |
| `--no-cleanup` / “不要清理” | ✓ | ✓ | ✗ | ✗ | ✗ |
| `--no-rebase` | ✗ | ⚠️ 仅当已可 FF | （随其它开关） | （随其它开关） | （随其它开关） |

`--no-merge` 保留分支与备份但默认清理 worktree；`--no-rebase` 只有已可 FF 才能合入。`--no-cleanup` 仅跳过清理，可与其它开关组合，优先保留 worktree、分支与 backup tag；不自动禁止合入。只要求保留某一对象时保留该对象及其必要依赖，继续清理其余可安全删除的本轮对象。

例如保留 worktree 时也保留其正在使用的分支；只保留 backup tag 不妨碍清理已合入的分支与 worktree。

## Step 1 · 撰写 SUMMARY.md

按宪法「总结」部分的要求，在 `docs/` 下当前开发项文件夹中撰写 `SUMMARY.md`（结合 args）。

只有符合 Step 2 的跨项目候选才增加「可沉淀项」段；没有候选时不写占位、不另行询问。

同一次连续收尾先完成适用的 SUMMARY、开发树和 README，再在 Step 6 集中提交；提交粒度沿用 `/commit`。文档记录当时可核实的事实与决定，不提前把尚未完成的合入、推送或部署写成成功，也不为“收到授权”“即将归档”单独提交。提交后出现独立交付或影响判断的新事实时，按其实际价值补充记录。

## Step 2 · 有价值的跨项目候选

优先在来源项目修代码、补测试或记录环境约定。事故发生过、重复发生过或看起来通用，都不自动成为新增全局规则的理由。

### 2.1 候选判据

仅保留能同时说明以下内容的候选：明确的跨项目适用条件；现有工具、测试或规则不能覆盖的价值；具体共享落点；为何不能只留在来源项目。优先修复已有真源，不增加同义规则。用户明确提出的共享偏好可直接作为依据，不强求事故次数。

按减少用户介入的价值排序，最多 3 条。无候选直接结束本步，不要求用户寻找沉淀项。

### 2.2 去向分类

- **跨项目资产** → 跨仓库提 issue 到 coding-agent-config（改共享模板，或新增 skill / hook / 写进宪法）
- **仅当前项目可复用** → 文字建议「在本项目跑 `/backlog` 起本地 issue」，本步**不**替用户 file

### 2.3 自指守卫

**当前仓库就是 coding-agent-config**（`git rev-parse --show-toplevel` == `realpath "$HOME/.coding-agent/global-repo"`）→ 跨项目候选改为建议走**本地 `/backlog`**，不 API 自 file。本步剩余跳过。

### 2.4 逐条确认（外部可见动作，不自动 file）

把候选及适用条件、价值、落点集中呈现，请用户选择要提的条目。未获确认不 file；延后或不提不阻塞 commit。

### 2.5 对确认要提的候选跨仓库 file

1. **派生目标 slug 与 platform**（不硬编码，多设备 / 改名都成立）：

   ```bash
   GLOBAL_DIR="$HOME/.coding-agent/global-repo"
   URL=$(git -C "$GLOBAL_DIR" remote get-url origin)
   SLUG=$(printf '%s' "$URL" | sed -E 's#\.git$##; s#^git@[^:]+:##; s#^https?://[^/]+/##')
   case "$URL" in *github.com*) PLAT=github ;; *gitlab*) PLAT=gitlab ;; *) PLAT="" ;; esac
   ```

   目录不存在 / `URL` 取不到 / `PLAT` 空 → 跳过 file，提示「无法定位 coding-agent-config，候选已记在 SUMMARY 可沉淀项段」，**不阻塞 finish**。

2. **选并校验三轴 label**：`type:*` + `priority:P2`（沉淀项默认排队）+ `area:*`（读 `$GLOBAL_DIR/.github/labels.yml` 选最贴的一个）。**三轴是硬要求**，且选完必须对**目标仓库**校验三个 label 都真实存在：

   ```bash
   python3 "$HOME/.coding-agent/scripts/platform_issue.py" --platform "$PLAT" label-list --repo "$SLUG"
   ```

   只从该列表挑，不在列表的不要硬塞（为什么必须校验、以及硬塞失败后的补救路径，见 `scripts/platform_issue.md`「三轴 label 硬约束」）。

3. **写临时 body**（`/tmp/distill-<n>.md`）：来源项目与轮次、适用条件、现有能力的缺口、具体落点与不应扩大的范围；末尾标注「经用户确认的跨项目候选」。当前项目有 remote 就给回链 URL。不要复制事故全过程。

4. **调 helper 跨仓库提**（`--platform "$PLAT" issue-create --repo "$SLUG"` + 三轴 label + `--body-file`），成功则打印返回的 issue URL。

   helper 报错时不得去掉 `--label` 重试；重新核对目标仓库的三轴 label，仍失败则报告错误，保留 SUMMARY 候选且继续 finish。

## Step 3 · 识别 issue 关联

读 `docs/<本轮编号>-*/PROMPT.md` 顶部有没有 `> 来自 [#<N> ...](<URL>)` 引用块（由 `/start <issue#>` 写入）。

**有** → 提取全部 issue 号与 URL，传给 `/commit`：已完整交付的各写一行 `Closes #N`；未完成的只写 `Refs #N` 并说明剩余验收项。合入后的关闭状态按项目实际合入路径核验，不把关键字存在当作已经关闭。

**关多个 issue 时每个都要带自己的关闭关键字、各占一行**：

```
Closes #13
Closes #20
```

不要把多个号合写成 `Closes #13 #20`；每个 issue 各带关闭关键字。

**无 issue 关联**（自由描述分支）→ 跳过本步剩余部分。

### Step 3.5 · round 编号一致性检查

本轮若经历过 rebase / 历史整理，目标分支可能已占用本地 round 编号，导致 **docs 目录编号** 与 `/commit` 将生成的 `[round N]` 前缀脱节。commit 前逐条核对，**命中不一致则给出顺延计划、要求用户确认，绝不静默继续**：

1. `docs/<N>-...` 目录编号是否需顺延到下一个空位；
2. `docs/DEVTREE.md` 的 Epic 结构与索引是否随之顺延（本步在 Step 4 `/devtree` 之前，顺延后 `/devtree` 会据最新目录重生成）；
3. `/commit` 将生成的 `[round N]` 前缀是否与文档目录编号一致；
4. **顺延如需改写已提交的历史**（rename docs 目录 + amend/rebase）→ 明确提示「这会改写历史」，等用户确认才动手；
5. 顺延后重跑 `git log --oneline` / `git status` 确认三者编号一致再进 Step 4。

三者本就一致 → 打印一行「round 编号一致，无需顺延」直接进 Step 4。

## Step 4 · 调用 `/devtree`

更新开发树 `docs/DEVTREE.md`。

## Step 5 · README review & update

本轮新增/删除 skill 或 hook、改变顶层目录结构，或改变用户入口、安装、模板、命令接口等约定时，读 `references/readme-review.md` 更新相关段落。纯内部重构、开发记录、依赖升级或不改变用户使用方式的修复不触发。SUMMARY/DEVTREE 自身不触发；用本轮已提交及未提交 diff 判断，避免只看到最后一次提交。README 更新随本轮提交。

## Step 6 · 调用 `/commit`

提交本轮全部相关变更（含 SUMMARY.md / DEVTREE.md / README.md），不夹带他人或归属不明的工作。Step 3 识别到 issue 关联时，把 `Closes #N` 作为额外上下文传给它，**多 issue 按 Step 3 的硬规则各占一行**。所有 review、验证与 lint 门禁照常执行。

## Step 7 · worktree 收尾

`/start` 默认在独立 worktree 内开一轮。本步在 `/commit` 之后自动判断是否在 worktree 内：

```bash
[ "$(git rev-parse --git-dir)" != "$(git rev-parse --git-common-dir)" ]
```

- **不在 worktree**（含 `--no-worktree` 轮）→ 打印一行「non-worktree round，跳过 worktree 收尾」，直接进 Step 8。
- **在 worktree** → **读 `references/worktree-finish.md`** 按其 7.1–7.5 执行（诊断 / 备份 + rebase / FF merge / 默认清理 / 不自动 push），各开关的跳过分支以上方对照表为准。已有明确授权在原对象、动作和范围内持续有效；默认清理无需另取授权，无新冲突或风险时连续完成，不重复询问。

## Step 8 · 交付说明与轻量提示

按实际结果区分已提交、已合入本地、已推送、已部署，说明保留项与剩余步骤；没有执行的动作如实标明。rebase 改变 SHA 时，结合前后提交的 `git range-diff` 等补丁核验说明是否等价、冲突修复是否引入变化，不能仅凭 SHA 不同或命令成功下结论。

打印一行：

> 「如果 SUMMARY 里的『后续 TODO』有想真正推进的项，单独跑 `/backlog` 起 issue。SUMMARY 是回顾文档不是承诺清单，TODO 不必每条都开 issue。」
