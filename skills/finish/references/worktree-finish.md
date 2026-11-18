# worktree 收尾细则（`/finish` Step 7 展开）

> `/finish` Step 7 在**确认自己处在 linked worktree 内**之后读本文。非 worktree 轮（含 `--no-worktree`）根本走不到这里。

收尾流程遵循 `/rebase` 的核心原则（FF-only、备份 tag、冲突逐文件解、abort 兜底），但**不调用 `/rebase`** —— 它阶段 3 的 `git checkout <主分支>` 在 worktree 下必失败（主分支已被主工作树占用），FF merge 必须改用 `git -C <主工作树> merge`。

**本地收尾授权**：调用 `/finish` 默认授权将本轮提交 FF 合入本地主分支，并清理本轮工作树、本地开发分支及本轮备份 tag。用户明确的跳过与保留要求优先。新增冲突、风险或对象变化须先核对；涉及取舍再请用户决定。远端 push、共享历史改写和丢弃未保全资产须另有授权。

## 工作树清理通用条件

先解析工作树真实路径，结合 Git 注册及应用附件核对归属和托管身份。清理前核对无其他会话占用、index 和工作树干净，并用 `git status --porcelain=v1 --untracked-files=all --ignored` 检查未跟踪与忽略文件。存在未保全资产或无法核实归属时，保留工作树并报告具体原因。核实本轮提交可从目标分支或明确保留的本地分支到达。后续调用的 `workdir` 显式指定为主 checkout。

普通树用 `git worktree remove`，禁用强制删除。托管树用应用 archive，按 `~/.coding-agent/skills/start/references/worktree-create.md`「项目内入口」核对附件身份；成功后只移除经核实的本任务软链接。应用恢复后按同一节修复入口。清理失败则保留入口、分支和备份，不执行依赖的删除。复核实际清理结果并报告。

## 7.1 诊断

展示 `git worktree list`、`git branch --show-current`、`git status`（应干净，`/commit` 刚跑完）、`git log --graph --oneline -15`。

- **探测主分支**：`git symbolic-ref --short refs/remotes/origin/HEAD`（仅剥掉 `origin/` 前缀，保留主分支自身可能含有的 `/`）；失败则本地探测 `main` / `master`。
- **算主工作树路径**：`dirname "$(git rev-parse --path-format=absolute --git-common-dir)"`

**前置检查**：当前分支必须是本轮开发分支，工作树与 index 必须干净。不满足就保留现场并报告。

## 7.2 备份 + rebase

若发现远端已合入与本轮重叠的实现，先停下盘点双方各自增量并请用户确认：远端已覆盖且可用则只补真增量；各有价值或无法判断则在远端版本上重写己方增量；保留己方时说明如何吸收远端价值。不要直接硬解冲突或擅自弃稿。弃掉的分支先打备份 tag，并在 SUMMARY 写明弃因；确认取舍后再继续。

> `--no-rebase` 跳过本整节（不打备份 tag、不 rebase），直接进 7.3。

如有提交会被改写，先核实本轮分支的发布和共享状态；未经相应授权不得改写已发布或共享历史。无法核实且确需改写时，保留分支并报告。

1. **备份 tag**：`git tag backup/<分支名>-$(date +%Y%m%d-%H%M)`，告诉用户「搞砸了用 `git reset --hard <该 tag>` 回退」。
2. **rebase**：`git rebase <主分支>`。
   - **无冲突** → 展示 `git log --graph --oneline -10`，先做下文补丁核对，通过后进入 7.3。
   - **有冲突** → `git status` 列冲突文件，暂停说明并让用户决定冲突处置；按已确认的处置**逐个解、逐个 `git add`**，再 `git rebase --continue`，后续 commit 续冲突则重复，不自动跳过。随时可 `git rebase --abort` + 备份 tag 兜底。解完核对实际变化与受影响验证，通过后进入 7.3。

备份仍在时，用 rebase 前后各自基线与 tip 的 `git range-diff` 核对补丁，将等价性结论或实际变化保留给最终交付说明；不能等删掉 backup tag 后才寻找对照。出现未经授权的补丁变化时暂停合入。

## 7.3 FF merge 到主分支

> `--no-merge` / `--keep-branch` 跳过本节，清理改走 7.4-skip（默认清理 worktree，保留分支与 backup tag；`--no-cleanup` 则三者都保留）。

合入前核对主 checkout 已检出目标主分支且工作区和 index 干净，待合入范围只有本轮提交。核对通过后直接 FF；成功后核实目标 ref 与本轮提交的可达性，再进入清理。

主分支 checkout 在主工作树，当前 worktree 不能 `git checkout` 它，故用 `-C` 在主工作树内合并：

```bash
git -C <主工作树> merge --ff-only <当前分支>
```

FF 失败时先查原因。仅在核实目标主分支前进、且允许 rebase 时回 7.2，再核对目标和待合入范围；其他失败保留现场并报告。禁止 fallback 普通 merge。

## 7.4 默认清理

`--no-cleanup` 或用户明确要求不要清理 → 保留 worktree、分支与 backup tag，直接进 7.5；只保留部分对象时，跳过这些对象及其必要依赖的删除。

按「工作树清理通用条件」核验并归档工作树。在主分支上下文用 `git branch -d <当前分支>` 删除本轮分支，再用 `git tag -d <本轮备份>` 删除本轮备份（`--keep-backup` 时保留并报告）。仅执行适用项。归档或分支删除失败时保留备份并报告。

## 7.4-skip（`--no-merge` / `--keep-branch` 专用）

不 merge，默认清理 worktree，保留分支与 backup tag。用户明确要求不要清理（含 `--no-cleanup`）时保留三者，报告实际状态后直接进 Step 8。只保留部分对象时沿用 7.4 的保留规则。

按「工作树清理通用条件」核验并归档工作树，以保留的本地分支核实提交可达性。工作树清理失败时报告实际状态。

删成功后打印：

```
本轮已 commit + SUMMARY 就位，按 --no-merge 保留分支不合入主干（worktree 已删）：
  分支   : <当前分支>（按实际状态说明是否已 rebase、是否可 FF）
  backup : <本轮备份 tag，如适用>
后续可：① 在主工作树 git switch <当前分支> 联调 / 让人 review / 提 PR；
       ② 准备好后 git -C <主工作树> merge --ff-only <当前分支>。
```

然后直接进 Step 8（跳过 7.5 —— 主分支未前进）。

## 7.5 不自动 push

主分支已 FF 前进，push 须有单独覆盖远端与目标分支的授权；已有明确授权时可在原范围内执行，不再重复询问，否则保留本地结果并说明尚未推送。合入或清理授权不包含 push。
