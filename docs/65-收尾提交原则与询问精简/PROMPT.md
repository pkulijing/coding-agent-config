# 收尾提交原则与询问精简

> 来自 [#190 明确 /finish 默认提交与合入原则，避免碎片化状态提交及反复人工提醒](https://github.com/pkulijing/coding-agent-config/issues/190)
> Labels: `type:bug` `area:skill` `priority:P1`
>
> 来自 [#186 移除 /finish 的“刻意不做”筛选与归档询问](https://github.com/pkulijing/coding-agent-config/issues/186)
> Labels: `type:feat` `area:skill` `priority:P2`

## 背景

用户要求在同一开发轮处理 #190 与 #186。两者共同改善 `/finish` 的收尾体验：减少没有独立价值的状态提交与固定询问，使已经明确授权的工作连续完成，同时保留实际必要的权限边界。

#190 来源于 infra-team 第30轮收尾：功能交付之后，发布验收记录、已获合入授权的状态更新、最终归档先后形成三个文档提交。已有 Step 7 要求集中提交 SUMMARY、DEVTREE 和相关 README，问题并非现行规则强制拆分，而是缺少完整交付单元的判断，以及跨步骤复用已有授权的明确约定。

#186 指出 finish 的“刻意不做”扫描及归档询问使用率低；用户希望需要时手动处理，删除每轮固定流程。

## 需求

### #190：形成稳定的默认提交与收尾原则

1. 提交围绕可独立审阅、回退和说明目的的交付单元；对话状态变化本身不构成提交单元。
2. 同一次连续收尾，先完成适用的 SUMMARY、开发树与 README 更新，再集中提交；避免“已同意合入”“准备归档”之后马上追加最终归档提交。
3. 明确授权在原范围内持续生效。没有新冲突、风险或范围变化时，连续执行，不对同一动作反复询问；尚未授权的合入、销毁性清理、push 仍按既有边界处理。
4. 保留独立功能、修复、必要部署记录、已发布或被引用的记录、影响判断的新事实、审计与恢复点等例外，不机械限制一轮提交数。
5. 优先避免产生新碎片；不借此自动 squash、改写已发布或公共历史、force push，或操作其他工作树。
6. 最终报告区分已提交、已合入本地、已推送、已部署；rebase 改变 SHA 时说明补丁等价性核验结果及实际变化。
7. 保留提交前 review、验证和 lint 的原有强度。

### #186：移除低收益固定询问

1. 删除 finish 现行 Step 2 的 SUMMARY 扫描、归档询问及该步自动创建/关闭 issue 的路径。
2. 连续调整步骤编号、子步骤及现行引用，不保留作废步骤或编号缺口。
3. 保留用户主动要求时使用 `wontfix` 归档的能力与既有记录。旧 BACKLOG 迁移等必要场景不依赖被删除的 finish 步骤。

## 范围与边界

- 优先修改 finish、commit 与 worktree-finish reference；相关技能只修正失效引用或受影响的说明。
- 仅在跨流程原则存在必要缺口时小幅调整 GLOBAL_AGENTS.md；不建立另一套审批或事故记录机制。
- #172 的 squash 功能、#160 的 review 触发节奏、#168 的范围接力及 #191 的托管工作树生命周期不纳入本轮。
- 不修改 infra-team 业务实现，不追溯整理任何业务仓库历史，不清理已有工作树或引用。
- 本轮计划确认仅授权按计划实施，不自动授予本轮后续合入、清理或推送权限。

## 开轮检查

- 日期：2026-11-12，Asia/Shanghai。
- 两条 issue 最新状态均为 open，无评论或 owner 补充。
- fetch origin 成功；默认分支符号引用缺失，依据实际存在的本地 master 及 origin/master 使用 master。
- 已合入及远端在途提交均未检出关闭 #190、#186 的关键字。
- 主 checkout 干净，master 与 origin/master 无分叉；五源最大已占轮次为64，新轮次为65。
- 工作树：`/home/jing/Developer/coding-agent-config/.worktrees/round65-finish-flow`。
- 分支：`round65-finish-flow`。
- 起始基线：`076615da4ed3a9242d94f03b54e8347090b03869`。
