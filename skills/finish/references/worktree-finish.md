# worktree 收尾细则（`/finish` Step 7 展开）

> `/finish` Step 7 在**确认自己处在 linked worktree 内**之后读本文。非 worktree 轮（含 `--no-worktree`）根本走不到这里。

收尾流程遵循 `/rebase` 的核心原则（FF-only、备份 tag、冲突逐文件解、abort 兜底），但**不调用 `/rebase`** —— 它阶段 3 的 `git checkout <主分支>` 在 worktree 下必失败（主分支已被主工作树占用），FF merge 必须改用 `git -C <主工作树> merge`。

**授权沿用与默认清理**：先核对当前对话已有授权的动作、对象与范围；已明确授权的合入无新冲突或范围变化时连续执行，不重复确认。调用 `/finish` 默认授权清理本轮 worktree、本地开发分支及本轮 backup tag，不再询问是否清理；用户最新明确的保留要求优先。此授权不涵盖其它工作树、无关分支、发布 tag、远端引用或未保全资产，也不授予尚未明确的合入或 push 权限。缺合入等授权时，先完成当前已授权范围，再呈现具体提交结果和待操作目标，集中询问必要决策；新增风险或对象变化须说明差异并取得对应确认。

普通 `.worktrees/` 中的工作树按下述 Git 流程处理；若检测到 Codex 托管工作树，先识别其附件与生命周期，清理必须使用应用的 archive 能力，不能直接删托管 checkout。

## 7.1 诊断

展示 `git worktree list`、`git branch --show-current`、`git status`（应干净，`/commit` 刚跑完）、`git log --graph --oneline -15`。

- **探测主分支**：`git symbolic-ref --short refs/remotes/origin/HEAD`（仅剥掉 `origin/` 前缀，保留主分支自身可能含有的 `/`）；失败则本地探测 `main` / `master`。
- **算主工作树路径**：`dirname "$(git rev-parse --path-format=absolute --git-common-dir)"`

**前置检查**：当前分支不能就是主分支；工作区必须干净。任一不满足 → 停下问用户。

## 7.2 备份 + rebase

若发现远端已合入与本轮重叠的实现，先停下盘点双方各自增量并请用户确认：远端已覆盖且可用则只补真增量；各有价值或无法判断则在远端版本上重写己方增量；保留己方时说明如何吸收远端价值。不要直接硬解冲突或擅自弃稿。弃掉的分支先打备份 tag，并在 SUMMARY 写明弃因；确认取舍后再继续。

> `--no-rebase` 跳过本整节（不打备份 tag、不 rebase），直接进 7.3。

1. **备份 tag**：`git tag backup/<分支名>-$(date +%Y%m%d-%H%M)`，告诉用户「搞砸了用 `git reset --hard <该 tag>` 回退」。
2. **rebase**：`git rebase <主分支>`。
   - **无冲突** → 展示 `git log --graph --oneline -10`，按上述授权判据进入 7.3；已有合入授权时不再停下。
   - **有冲突** → `git status` 列冲突文件，暂停说明并让用户决定冲突处置；按已确认的处置**逐个解、逐个 `git add`**，再 `git rebase --continue`，后续 commit 续冲突则重复，不自动跳过。随时可 `git rebase --abort` + 备份 tag 兜底。解完核对实际变化与受影响验证，再按授权判据进入 7.3。

备份仍在时，用 rebase 前后各自基线与 tip 的 `git range-diff` 核对补丁，将等价性结论或实际变化保留给最终交付说明；不能等删掉 backup tag 后才寻找对照。无冲突不单独证明补丁等价。

## 7.3 FF merge 到主分支

> `--no-merge` / `--keep-branch` 跳过本节，清理改走 7.4-skip（默认清理 worktree，保留分支与 backup tag；`--no-cleanup` 则三者都保留）。

尚无合入授权时，展示待合入提交及目标主分支，等待确认；已有明确授权且范围未变时直接执行。

主分支 checkout 在主工作树，当前 worktree 不能 `git checkout` 它，故用 `-C` 在主工作树内合并：

```bash
git -C <主工作树> merge --ff-only <当前分支>
```

`--ff-only` 失败（主分支在本轮期间又前进）→ 回 7.2 把当前分支继续 rebase 到最新主分支再重试（`--no-rebase` 下不能自动 rebase → 停下提示用户去掉该开关重跑或手动 rebase）。**禁止 fallback 普通 merge。** 新冲突、风险或范围变化仍按授权判据处理。

## 7.4 默认清理

`--no-cleanup` 或用户明确要求不要清理 → 保留 worktree、分支与 backup tag，直接进 7.5；只保留部分对象时，跳过这些对象及其必要依赖的删除。

**明确列出**将删除的具体 worktree 路径、分支与 backup tag（`--keep-backup` 时不含 tag）。核对成果已合入目标、工作树与 index 干净，以及未跟踪/忽略文件中有无凭据、运行数据或其他未保全资产；普通 `git status` 干净不能证明这些资产不存在。发现资产或归属不明时先保全，不让“清理”默认涵盖丢弃它们；其他活动工作树不在删除范围。

上述核验通过后直接清理，不停下来询问是否删除。先将后续调用的 `workdir` 显式设置为主工作树（当前工作树即将删除，不能依赖一次 `cd`），再依次执行适用项：

```bash
git -C <主工作树> worktree remove <当前 worktree 路径>
git -C <主工作树> branch -d <当前分支>
git -C <主工作树> tag -d backup/<分支名>-<时间戳>   # --keep-backup 时跳过，末尾打印保留的 tag 名
```

`git worktree remove` 失败（IDE / 编辑器占用 worktree 内文件）→ 提示「请关闭打开该目录的编辑器后重试」，**不加 `--force` 硬删**，保留全部状态。

按实际执行结果报告各项；前一步失败不得继续依赖它的删除。完成后复核 worktree 注册、路径与引用，不能把单个命令成功当成全部清理完成。

## 7.4-skip（`--no-merge` / `--keep-branch` 专用）

不 merge，默认清理 worktree，保留分支与 backup tag。用户明确要求不要清理（含 `--no-cleanup`）时保留三者，报告实际状态后直接进 Step 8。只保留部分对象时沿用 7.4 的保留规则。

**删除项只有 worktree 一项，其余纪律同 7.4**：核对资产；此路径不要求已合入主分支，但必须核对成果均已保全在保留的分支与适用备份中。核验通过即默认清理，无需再次确认。显式将 `workdir` 设置为主工作树；`remove` 失败提示关编辑器重试且**不加 `--force`**。额外一条：**`remove` 失败时必须把「worktree 未删」打印出来**，不得静默按已删继续 —— 否则下面引导的 `git switch` 会切不动。

删成功后打印：

```
本轮已 commit + SUMMARY 就位，按 --no-merge 保留分支不合入主干（worktree 已删）：
  分支   : <当前分支>（已 rebase 到 <主分支>，线性可后续 FF）
  backup : backup/<分支名>-<时间戳>
后续可：① 在主工作树 git switch <当前分支> 联调 / 让人 review / 提 PR；
       ② 准备好后 git -C <主工作树> merge --ff-only <当前分支>。
```

然后直接进 Step 8（跳过 7.5 —— 主分支未前进）。

## 7.5 不自动 push

主分支已 FF 前进，push 须有单独覆盖远端与目标分支的授权；已有明确授权时可在原范围内执行，不再重复询问，否则保留本地结果并说明尚未推送。合入或清理授权不包含 push。
