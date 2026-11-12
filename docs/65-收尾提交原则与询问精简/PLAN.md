# 实现计划

> 状态：用户已确认并追加默认清理需求；两次交付均已实现、验证并通过独立 review，待合入
> 日期：2026-11-12
> 工作树：`.worktrees/round65-finish-flow`
> 分支：`round65-finish-flow`
> 检查基线：`076615da4ed3a9242d94f03b54e8347090b03869`

## 一、方案

### 1. 在 commit 中定义完整交付单元

在 `skills/commit/SKILL.md` 的普通提交入口补充简短判据：开发单元完成后按原流程自动提交；同一次可连续完成的收尾，先汇齐适用文档，不将“用户已授权”“即将合入”等过程状态各自变成提交。

独立功能、修复、隔开的交付、必要部署与验收记录仍可独立提交；尤其不能为了凑成一个提交删掉已发布记录或改写共享历史。保持 design 的特殊归档契约，保持所有提交前 review 与 lint 门禁。新增规则用于决定提交内容与时机，不更改审查触发机制。

### 2. finish 集中完成本次可执行的收尾文档

在 `skills/finish/SKILL.md` 明确文档汇齐后集中提交的原则，沿用已有 SUMMARY、DEVTREE、README 流程，不额外引入中间状态文件或固定检查清单。

文档只记录当时可核实的事实和已决定的取舍。合入、推送、部署尚未发生时不得提前写成成功；已经授权、可以连续执行的步骤不为记录“收到授权”另做提交。提交之后出现影响交付判断的新事实、真实部署结果或较晚的新决定时，允许有独立价值的后续记录，不以少提交为由隐藏事实。

### 3. 收尾 reference 复用已有明确授权

在 `skills/finish/references/worktree-finish.md` 统一确认分支的判据：

- 进入后续步骤先核对既有授权的动作、对象与范围。已经明确授权合入，且复核无新冲突、资产风险、范围变化时，直接连续完成。
- 用户已明确追加清理默认授权：调用 `/finish` 默认清理本轮 worktree、本地开发分支及本轮 backup tag，不另问是否清理。未授权的合入与 push 仍在边界集中确认，不扩大成任意销毁授权。
- 新增 `--no-cleanup` 并识别自然语言“不要清理”，保留三者；不影响是否合入。组合开关时保留要求优先。保留 worktree 时也保留其正在使用的分支；既有 `--keep-backup` 与 `--no-merge` 等开关继续有效。
- 清理前仍核验成果与资产保全，仅删除本轮对象，不删除发布 tag、远端引用、未合入成果或未保全文件；no-merge 路径只删树，保留成果分支和备份。
- 用户改变保留/合入决定后，以最新明确指令为准；对象改变或发现新风险时解释差异，不能机械套用旧授权。
- 保留备份、FF-only、冲突处置、失败保全、普通与托管工作树的现有边界。#191 另行解决具体产品生命周期问题。

最终说明实际完成与剩余事项，区分提交、本地合入、推送和部署。rebase 后以实际补丁核验说明是否等价；存在冲突修复时如实说明变化，不仅展示新 SHA。

GLOBAL_AGENTS.md 的总结条款改为由 finish 定义默认行为、保留选项与授权边界，去掉泛化的“清理确认边界”；README 同步默认清理与保留入口，不复制详细步骤到宪法。

### 4. 删除固定归档询问并修复引用

- 删除 finish 原 Step 2 全节，后续步骤、子步骤连续重编号；worktree reference 的标题、内部编号及跳转同步更新。
- 更新 `skills/finish/references/readme-review.md` 的步骤说明。
- 更新 `skills/quick/SKILL.md`、`skills/rebase/SKILL.md`、`skills/start/references/remote-align.md` 中指向 finish 的步骤引用；检查其他现行入口，不批量改写历史 docs。
- `skills/sync-project-config/SKILL.md` 的旧 BACKLOG 迁移当前引用 finish Step 2：改为该迁移场景下明确的手动归档说明，保留原有原因与信息、确认边界和 helper 使用要求，不把 finish 的固定询问搬到其他每轮流程。
- 保留宪法中用户决定不做的事项以 `wontfix` 归档的原则；检查 quick 的边界说明，移除对已删除 finish 自动流程的过时描述。

### 5. 保持改动范围最小

预计主要落点为三个核心文件（finish、worktree-finish、commit），加上述引用修复文件；GLOBAL_AGENTS.md 与 README.md 仅按实际语义影响更新必要段落。本轮开发记录单独放当前轮目录，完成时按 finish 更新 SUMMARY 与 DEVTREE。

不增加 squash 开关，不修改 review 编队、模型、角度、次数或降级门槛；不修改 routine 权限与安装部署。普通技能内容在主 checkout 合入后随已有目录软链生效，本轮无新增/删除技能或原生基线变更，不要求重装。

## 二、验收与验证

本轮修改指令与引用，没有新增可执行代码，采用情景走查、引用检查及独立 review；不编写只复述文本的镜像测试，不用真实业务历史验证销毁或改写操作。

| 输入场景 | 预期结果 |
| --- | --- |
| 一次连续收尾，SUMMARY、DEVTREE、README 均需更新 | 汇齐后集中提交，不拆成多个过程状态提交 |
| 独立功能/修复已完成，随后另有交付单元 | 各自可审阅、可说明目的，保留独立提交 |
| 先发布验收，较晚才决定合入 | 保留发布事实与必要后续记录，不机械压成一次提交 |
| 已明确授权本轮合入并清理，复核无新增风险 | 在原范围内连续完成，不对相同步骤重复确认 |
| 只有计划确认，或只有提交授权，未调用 finish | 不自行触发收尾、合入或推送 |
| 调用 finish 并已授权合入，没有单独说清理 | 核验通过后默认删除本轮树、分支与 backup tag，不再询问 |
| finish 明确说不要清理，或 --no-cleanup | 保留树、分支、backup tag，不自动禁止合入 |
| --no-cleanup 与 --no-merge、--keep-backup 等组合 | 保留要求优先，既不误合入也不误清理 |
| --no-merge / --keep-branch，未要求保留 worktree | 成果已保全在分支后默认只清理树，分支与备份保留 |
| 只要求保留 worktree 或 backup tag | 保留所指对象及必要依赖，清理其余可安全移除项 |
| 用户中途改变保留/合入决定 | 遵循最新指令，不为每次决定单独创建状态提交 |
| rebase 出现新冲突、发现未保全资产或对象改变 | 保全现场并说明新问题，原授权不自动覆盖新增风险 |
| 历史已发布/共享或已被部署依赖 | 不自动 squash、改写或 force push |
| 多工作树并行，有归属不明的工作 | 只处理本轮明确对象，保留他人修改和引用 |
| rebase 后 SHA 改变 | 根据实际核验说明补丁是否等价、冲突修复是否带来变化 |
| finish 的 SUMMARY 中含局限性或 TODO | 无固定“刻意不做”询问，无自动建/关 issue |
| 用户主动要求将事项归档为 wontfix | 既有手动能力保留，仍遵循 issue helper 与授权要求 |
| sync 迁移旧 BACKLOG 中已有不再追踪项 | 原因与条目先保全，手动归档路径明确，无失效步骤引用 |
| 删除 finish Step 2 后检查跨技能引用 | 步骤、子步骤、跳转及正文含义一致，无编号缺口 |

实施时检查现行引用与 `git diff --check`，按实际可用的仓库引用检查入口执行验证，报告基线既有问题。若新增可执行逻辑，须先补充输入输出契约与 TDD 验证方案，不能沿用“纯指令”豁免。

## 三、审查与交付

1. 实施前从上述起始 SHA 读取并核验 `/commit`、`/review-loop`、其实际需要的 references 与 agent 配置；提交前按冻结基线调用独立 context review，不用本次待审规则放行自身。
2. 每个实际开发单元完成后按原流程 `/commit`；两个需求共享 finish 步骤与引用修复，可作为一个完整主题交付，不强行按 issue 拆出相互不完整的中间态提交。
3. 独立审查重点：提交时机与事实记录是否自洽、已有授权是否被过度扩大、必要确认是否保留、历史保护与审查门槛是否保持、被删步骤引用是否清理完整。
4. 完整交付后分别写 `Closes #190` 与 `Closes #186`；未完成项只用 `Refs` 并说明剩余范围。以实际默认分支合入路径核对关闭状态。
5. `/start` 阶段仅建立工作树和 PROMPT、PLAN；用户确认计划后实施。用户本轮追加的默认清理方向已明确授权，不再为相同方向索要计划确认；本次实施不自行触发 finish、合入或 push。

## 四、首个交付验证

- 已修改 finish、commit 与 worktree-finish reference，并同步 README 和相关步骤引用；GLOBAL_AGENTS.md 既有原则可容纳本轮细化，无需重复扩写。
- `git diff --check` 通过。
- `python3 scripts/context_budget.py check-refs` 通过；此工具不验证章节语义，现行 finish 的 Step/§ 引用已另行核对，历史 docs 保持原版本。
- skill-creator 的 `quick_validate.py` 对 commit、finish、quick、rebase、start、sync-project-config 六个受影响技能均返回 `Skill is valid!`。
- 情景走查覆盖：同次文档集中提交、独立交付与后续新事实保留、授权沿用与对象变化、缺授权时停在边界、no-merge 保留分支、忽略资产保全、清理部分失败及手动 wontfix 迁移。基线 review、备份和 FF-only 门槛未减少。
- 本轮只有指令与文档变更，无可运行代码单元，运行测试判 N/A；仓库根没有 `/commit` lint 表命中的项目配置，模板目录不作为本仓 lint 入口。
- 本机 `core.hooksPath` 指向不存在的旧路径 `/home/jing/Developer/claude-code-global/.git/hooks`，本轮不改无关配置、不宣称 hook 已运行。上述检查均显式执行。
- 独立 review 按开轮 SHA 的重档编队执行，五个角度均 clean，无编队降级；结果见本轮 REVIEW.md。

## 五、默认清理追加交付

- 追加开发起点为 `931434d3a2dc7a73d68b0a8663d9a870a974e743`，沿用本轮起始审查基线，不用待审修改降低检查标准。
- 修改 finish、worktree reference、GLOBAL_AGENTS.md 与 README；新增明确保留入口与组合语义。保持前一交付提交，不为本次追加改写历史。
- 验证默认清理、整体保留、局部保留、no-merge 组合及资产保全的分支；运行技能结构、引用与 diff 检查后做独立 review，结果记录到 REVIEW.md。
- `git diff --check`、`context_budget.py check-refs` 与 finish 的 `quick_validate.py` 均通过；五角度独立 review 均 clean，无调用失败或编队降级。无新增运行代码，运行测试仍为 N/A。
