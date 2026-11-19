# Review 记录：DSH 三端配置接入

## 基线与范围

- 起始基线：`3ff9b38`（master，本轮开轮点）。
- 审查对象：`round69-dsh-inherit` 工作树相对基线的全部改动（含未跟踪文件）。
- 起始版本只有 CC / Codex 两个委派入口；本轮改动**包含 review 规则本身**，因此按起始版本审查，不使用本轮新增的 DSH 入口为自己放行。

## 档位与入口核验

- 档位：默认档（角度 ①②③）。改动为安装脚本、指令文件、角色配置与 MCP profile，不命中重档的并发 / 跨进程 / 难复现条件。
- 起始版本的 ① 需要「orchestrator 子 agent 扇出 reviewer」。本平台不可用，实测证据：
  - 子 agent 工具列表含 `subagent`，但调用返回 `Delegation depth for subagent: current 1, maximum 1, remaining levels 0. Do not call subagent at this depth; carry out the work directly.`
  - 起始版本的 `agents/codex-review.toml` 指定 `gpt-6.1-sol` / `gpt-6-astra`，本平台无对应 route（唯一 route 为 `deepseek-account/deepseek-flash`），模型名不可用同样构成明确失败。
- 因此按起始版本 Step 5 落到 ②：主会话当 orchestrator，直接并行起 3 个独立 context reviewer，各审一个角度；模型只能取本机唯一 route。

> **②** ⚠ 本次编队降级为**通用 agent 类型** —— 独立 context 未失，`model` 已按当前端的编队配置钉死、只读已由委派 prompt 约束；能力损失逐项按实报告：本平台无起始版本规定的 CC / Codex 模型，实际固定为 `deepseek-account/deepseek-flash` + `reasoning_effort=high`（与开发主会话同模型，同模型盲区存在）；reviewer 只读仅由任务书约束。
> 降级原因：子 agent 调用返回 `Delegation depth for subagent: current 1, maximum 1, remaining levels 0.`；且 `agents/codex-review.toml` 的模型在本平台无 route。

## 第 1 轮

- 编队：3 个 reviewer（角度 ①②③），统一锚定工作树绝对根，只读；模型 `deepseek-account/deepseek-flash`，effort `high`。
- 结果：8 条 finding，全部判为需修复。

| # | 角度 | 位置 | 问题 | 处置 |
| --- | --- | --- | --- | --- |
| 1 | ① | `skills/review-loop/SKILL.md` DSH 入口第 2 条 | DSH 没有命名 agent 类型，reviewer 任务书未要求携带 `agents/code-reviewer.md` / deep 正文，角色纪律（自证仓库根、单角度、证据先于判断）到不了 reviewer | 改为「任务书必须自带共用约束 + 角色正文 + 角度原文」，并说明 DSH 无命名类型可继承 |
| 2 | ①③ | `docs/69-.../PROMPT.md` 验收 3 | 写「三个角色」，实际交付两个 | 改为两个角色并注明原因 |
| 3 | ③ | `skills/review-loop/references/rationale.md` §4 | 「两端角色配置」在新增第三端后作废 | 改为「各端角色配置」 |
| 4 | ② | `install.sh` `deploy_dsh` | 覆盖 `DSH_AGENTS_HOME` 时只迁规则不迁技能，DSH 会静默丢掉全部共享技能 | 自定义根时补 `deploy_skills "$agents_home/skills"`；README / AGENTS.md 文案校正；测试覆盖 |
| 5 | ②③ | `skills/review-loop/SKILL.md` Step 3 | 「两档角色均按配置使用 medium」与 DSH 的 high/max 冲突，会传非法档位 | 改为按各端配置取值 |
| 6 | ①② | `test_dsh_deploy.py` 幂等断言 | 与 `deploy_codex` 的日志同串，「已跳过 AGENTS.md」不具区分力 | 改用 dentry（inode + ctime）不变断言 |
| 7 | ③ | `test_dsh_deploy.py` | 走整装主流程，不符合「安装测试先用 `CCG_INSTALL_LIB_ONLY=1` 隔离入口」 | 重写为纯函数级 lib-only 用例；整装只留手工沙盘验证并记入 SUMMARY |
| 8 | ③ | `docs/69-.../` | 缺目录级 `.gitignore`，跑测试会产生未跟踪 `__pycache__/` | 新增 `.gitignore` |

## 闸 A 运行验证（第 1 轮修复后）

- `bash -n install.sh`：通过。
- `python3 docs/69-DSH三端配置接入/test_dsh_deploy.py`：7/7 通过。
- `docs/61-Codex全盘迁移/test_install_migration.py`（Python 3.12）：17/17 通过。
- 隔离 HOME 整装沙盘：默认根与 `DSH_AGENTS_HOME` 自定义根均 exit 0，链接与 16 个技能就位。
- MCP：profile 热加载后 `mcp__playwright__*` 与 `gitlab-anyverse` 资源服务器在当前会话可用。

## 第 2 轮

- 编队：同第 1 轮（3 个 reviewer，角度 ①②③，同模型档），委派收窄为「核对上述 8 处 finding 是否已消除、修复是否引入新问题」。
- 结果：8 条 finding 全部确认消除；未发现功能性新问题。reviewer 另做了独立复核：变异验证（删掉 `deploy_skills` 调用、强制 `rm` 后重建链接）证明新断言有区分力；整装沙盘覆盖默认根 / 自定义根 / 用户文件冲突 / 无 `~/.dsh` 异常路径，行为均正确。
- 复审判为 P3、顺手修正的文档残留（不影响运行时，不计入迭代轮次）：
  - `PLAN.md` 仍写「不部署 skill 投影」→ 改为默认不重复、自定义 agents 根时补部署；验收 A5 补技能断言。
  - `SUMMARY.md` 整装沙盘结果里「默认根未被写入」表述过宽 → 收窄为「`deploy_dsh` 不写默认根 `AGENTS.md`；该根技能链由 `deploy_codex` 照常部署」。
  - `angles.md` 首段「medium 思考档」在新增 DSH 后作废 → 改为「各端配置的思考档」。
  - `PROMPT.md` 需求 2 仍写 orchestrator 编队 → 改为「直启 N 个角度 reviewer（委托深度为 1）」。
  - `SKILL.md` Step 2「两端的 agent 配置」→「各端的 agent 配置」。

## 闸 A 运行验证（第 2 轮文档修正后）

- `bash -n install.sh`：通过。
- `python3 docs/69-DSH三端配置接入/test_dsh_deploy.py`：7/7 通过。
- `docs/61-Codex全盘迁移/test_install_migration.py`（Python 3.12）：17/17 通过。
- 残留措辞扫描：规则文件中已无「medium 思考档」「不部署 skill 投影」；剩余「两端」均是本仓历史的过去式描述，不是现役规则。

## 结论

2 轮收敛，闸 A 与闸 B 同时满足：无高置信 correctness finding，8 条首轮 finding 与 5 条文档残留全部修正，未出现振荡或发散。commit message 需按起始基线的 ② 档写入降级标注与证据（本文件开头的引用块）。

收敛后按用户明确指示追加一项：`GLOBAL_AGENTS.md` 的 git 署名表新增 DSH 行（`Co-authored-by: DeepSeek Harness <noreply@localhost>`）。该改动只有表格一行、由用户当轮拍板，未再开第 3 轮 review（2 轮上限）；如实留痕于此。
