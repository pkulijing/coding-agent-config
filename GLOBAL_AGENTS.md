# Development Constitution

## 称呼和语言

CC 指 Claude Code，Codex 指 OpenAI Codex，统称 Coding Agent；本规范对两端同等适用。

按用户使用的语言回复；语言不明确时默认使用英语。项目文档默认使用简体中文。用户明确指定语言时遵从。代码、命令、报错和专有名词保留原文。

## Communication and Collaboration

Communicate like an experienced software engineer talking to another experienced software engineer, not like a machine generating an execution report.

- Use plain, natural, conversational language.
- Never invent terminology for ordinary engineering concepts. Use established technical vocabulary.
- Prefer concrete descriptions over abstract labels. Explain what something does rather than giving it an elaborate name.
- Explain why a decision makes sense, not merely what actions were performed.
- Answer questions directly before introducing implementation details.
- Exercise independent engineering judgment. Disagree with the user when there are sound reasons to do so.
- Understand the user's underlying objective rather than mechanically interpreting individual words.
- Do not turn an exploratory discussion into an implementation task unless implementation is requested.
- Avoid bureaucratic language, excessive headings, unnecessary categorization, and machine-generated status reports.
- Match the user's language and conversational style.

Communication quality is part of engineering quality. An explanation that requires another explanation has failed its purpose.

These instructions concern communication and collaboration. They do not relax engineering standards, testing requirements, review requirements, or security constraints.

## 领域规则文档（playbooks/）

共享规则位于 `~/.coding-agent/playbooks/`。下表命中时，在相关操作前读对应入口；入口中的场景分支只在实际涉及时加载，不因“不确定”遍历全部资料。

| playbook | 触发条件 |
| --- | --- |
| `python.md` | 编写 Python、修改 pyproject.toml 或 Python 依赖、决定 Python 风格 |
| `python-packaging.md` | 构建 wheel、发布 Python 包或安装发布产物到目标环境 |
| `frontend.md` | 开发 web UI，配置 React / Vite / TypeScript / Biome / Tailwind / shadcn |
| `ros2.md` | ROS 2、colcon、ament、ROS 包配置或 launch |
| `lark.md` | 用 lark-cli 创作或编辑飞书云文档 |
| `feishu-bot.md` | 开发飞书 bot 后端、处理消息或卡片回调 |
| `llm-app.md` | 接入或修改 LLM API 调用；按入口区分文本、流式与 Agent 编排 |
| `shell.md` | 编写 shell 脚本、ssh 远端命令，或提供用户需手动执行的命令 |
| `cloud-routine.md` | 开发或维护 claude.ai Routines；不据其旧环境结论推断其他云端能力 |
| `scheduled-agent.md` | 用 launchd / systemd timer 部署本机无头 Agent 定时任务 |

这些资源按需读取，不挂到平台自动全文加载的目录。新增平台入口前核实其发现语义。

## 技能依赖的资源检查

首次使用 skill 要求的脚本、reference、模板、agent 定义或 playbook 前，检查本次所需具体路径存在且可读；软链检查目标，脚本还须可由指定解释器运行。不要预读未触发的可选资源。

资源缺失时，先报告 skill、受阻步骤、完整路径、实际错误、影响与可执行的修复方式，停止依赖动作；只按 skill 明定的降级路径处理。不得凭记忆补规则、另找同名副本或静默替换工具/agent，也不因此获得安装权限。

部署缺失时先核实 `~/.coding-agent/global-repo` 指向可用主 checkout，再给该入口的安装命令；入口失效则使用已核实的主 checkout 绝对路径，尚未定位就明确缺项。源文件本身缺失或不可读须先恢复文件或权限，不能承诺重装修复。

文件存在不等于运行时已注册或加载。能力失败以实际调用或工具列表核验为据，区分资源缺失、未注册和调用失败，并报告降级丢失的属性。

## 核心开发模式

常规交互开发走 `/start`：在当前模式中调查与讨论，无需切换原生 Plan 模式；用户批准方案后创建独立工作树并实施；`--no-worktree` 使用当前分支。小改走 `/quick`，调用即授权自主调查、实施、验证和提交。无人值守 routine 遵循各自的执行契约。

工作树统一在主 checkout 的 `.worktrees/` 下提供入口：普通工作树直接建在其中；Codex 托管工作树保留应用分配的真实路径，并在其中建立指向该工作树的软链接。创建、恢复与清理入口按 `/start` 的 worktree 细则执行；用户明确指定其他布局时遵从。

需求尚未明确时在当前模式中逐步讨论；仅讨论或搁置时，结论留在聊天里。

### 需求管理

- issue 是需求与讨论的单一真源，不建本地 backlog 索引；README 用 saved query 链接提供未关闭项入口。
- 每条 issue 使用 `type:*`、`area:*`、`priority:*` 三轴标签；type/priority 以 `_common` 模板 `.github/labels.yml` 为准，area 按项目定义。
- `/backlog` 建 issue，`/start <issue#>` 开轮，完成时在 commit/PR 写 `Closes #N`。核对合入路径的关闭结果，不把写了关键字等同于已经关闭。
- 经用户决定不做的项归档为带 `wontfix` 的 closed issue。
- issue/label 操作统一走 `~/.coding-agent/scripts/platform_issue.py`，跨仓操作同样带三轴标签。已确认该 helper 的本机 CLI 依赖不可用的云端环境，按对应技能使用环境内置 GitHub MCP；不得据平台名称猜测能力或扩大写权限。

### 需求生命周期

**计划**：正式轮次先从真实入口调查已有行为、实现和测试。计划以现状、改法、关键取舍和验收摘要开头，后附完整实施提纲。客户端的实施按钮或对当前方案的明确批准均有效。复用已批准的完整计划；客户端已在原生 Plan 模式时遵守其执行约束。实施中改变已批准的用户可见行为时再确认该变化。只有用户知道且没有权威来源的信息集中询问。

**执行**：在已授权需求范围内按计划自主完成工作；开发单元完成就 `/commit`，不等待用户催促。

- 关键技术假设失效、或继续推进需要选择计划未授权且代价不同的方向时，说明证据、可选方案和建议，等待用户确认；等价实现细节自主处理。已有明确优先级的能力降级按技能执行并留痕。
- 与远端已合入实现重叠时，先盘点双方独有与共有内容，核实远端可用性，提出增量保留方案并等确认。弃掉工作前打备份 tag，在计划中记下弃因；处理细节见 `/rebase`、`/finish`。
- 实测与文档多处冲突时，先核对目标系统、身份和环境前提。
- 引用外部权威材料的具体断言前取到原文。实际检索仍取不到时，说明查找范围、结果及未核实部分，不凭记忆补引文。
- 封装外部工具前核实原生能力，只补缺失编排，其余参数透传。核对查询范围、失败与部分成功的响应契约；不把空结果、零退出码或 HTTP 成功状态单独当成业务成功证明。

**收尾**：实现与验证结果留在代码、commit body 和交付回复中。收尾的默认行为、保留选项与授权边界以 `/finish` 为准。

### 测试先行（TDD）

能明确写出“输入 X 应得到输出 Y”的逻辑，先列正常/边界/异常用例，跑红，再做最小实现与必要重构。原型、视觉 UI、外部集成可先跑通，稳定后补齐适用单测。

行为随平台、网络、时钟、locale、HOME、配置等环境分叉时，把条件显式设为测试输入并覆盖各分支，不继承真实宿主或静默跳过。缺少无法模拟的运行前提（如 ROS 库、GPU）才允许对应测试跳过，并报告覆盖限制。危险副作用须先隔离，再跑红态。

### 提交前 review（自动跑）

每次执行阶段 commit 前调用 `/review-loop`，其编队、模型/思考档、角度、收敛和降级规则为单一真源。配置与指令规则文件不能按“纯文档”跳过。修改检查规则的任务按开发起始基线审查，不能用待审规则放行自身。

用户长期授权自主委派子 agent，无需逐次确认；该授权不扩展其他平台权限。review 在独立 context 中进行；能力降级必须有实际失败证据并保留规定角度，不允许不 review。独立 context 不等于跨模型保证，不宣称它消除了同模型盲区。

### 文档记录规范

正式轮次的唯一过程文档是批准版 `docs/<N>-<中文主题>/PLAN.md`，永久随仓库保存。包含读者、来源、目标、关键决策及理由、实施提纲、验收方式。以后获批的方案调整更新同一文件。存量历史文档原样保留，在途旧轮次沿用已有记录收尾。

每份新文档出生时必须有一行 `> 读者：<谁> · <什么问题>`；写不出读者的内容进 commit body，不落盘。一轮允许产出的文档是闭集，扩充先改本节。

交付文档记录决策、降级与取舍；自行发现并修正的未发布错误直接改正，不保留撤回段、作废行、编号缺口或反转叙事。影响用户判断的错误在对话中说明。已发布、他人可能读到的内容正常说明修订；弃因与备份等必要决策记录照常保留。不得为清理叙事擅自改写已提交历史。

一次性经验优先进入来源项目的实现、测试或文档。新增共享规则须说明跨项目适用条件、现有工具/规则为何不足及最小落点；事故发生过不自动构成准入理由。已有规则可以因重复、作用域不当或不再必要而退出，保留必要行为与授权边界，不另建事故档案。具体收尾候选和定期清理分别由 `/finish`、`/routine-slim` 执行。

## git 规则

- `.gitignore` 按目录维护，子目录规则不堆在根文件。
- commit message 默认中文 semantic 格式，聚焦目的与最终状态；轮次前缀按 `/commit`。
- 提交末尾按实际执行 Agent 署名，不从仓库路径或示例猜身份：

  | 执行 Agent | trailer |
  | --- | --- |
  | CC | `Co-authored-by: Claude <noreply@anthropic.com>` |
  | Codex | `Co-authored-by: OpenAI Codex <noreply@openai.com>` |
  | DSH | `Co-authored-by: DeepSeek Harness <noreply@localhost>` |

- 保全已有、未提交及归属不明的工作；历史改写、合入和清理遵循相应技能的授权与备份条件，不强行覆盖或删除。

## 环境变量管理

真实值放项目根 `.env.local` 并加入 gitignore；提交 `.env.example`，密钥仅用占位符，非敏感项可提供推荐值。不得提交真实凭据，也不将测试或示例中的凭据写入日志。
