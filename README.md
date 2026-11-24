# coding-agent-config

个人 Coding Agent harness，集中维护开发规范、技能、独立 review、脚本、hooks 和跨项目模板。目标是让 Agent 自主完成工作，减少人工纠正与维护；Codex 主用，Claude Code 保留兼容入口，DeepSeek Harness 复用同一套共享资源。

日常规则见 [GLOBAL_AGENTS.md](GLOBAL_AGENTS.md)，本仓开发约束见 [AGENTS.md](AGENTS.md)。需求以 issue 为真源：[未关闭项](https://github.com/pkulijing/coding-agent-config/issues?q=is%3Aissue+is%3Aopen+label%3Apriority%3AP0%2Cpriority%3AP1%2Cpriority%3AP2)，开发历史用 `git log` 与 issue 列表（[DEVTREE](docs/DEVTREE.md) 已冻结于第 69 轮）。

## 安装与维护

准备 jq，在本仓**主 checkout** 运行 `bash install.sh`。安装拒绝 linked worktree，保留用户配置与第三方技能。Codex 可在没有 CC 安装的机器上独立使用。

| 内容 | 部署位置 |
| --- | --- |
| 共享资源目录 | `~/.coding-agent/{skills,scripts,templates,playbooks,hooks,agents}`，链接到本仓 |
| 稳定仓库入口 | `~/.coding-agent/global-repo` |
| Codex 指令与配置 | `${CODEX_HOME:-~/.codex}/AGENTS.md`、`config.toml` |
| 共享技能根 | `~/.agents/skills/`，逐技能链接；Codex 与 DeepSeek Harness 共用（DSH 覆盖 `DSH_AGENTS_HOME` 时同步部署到该根的 `skills/`） |
| DSH 全局指令 | `${DSH_AGENTS_HOME:-~/.agents}/AGENTS.md`，仅在 `${DSH_HOME:-~/.dsh}` 存在时部署 |
| 用户真实配置 | `~/.coding-agent/config.env`，示例见 [user.config.example.env](user.config.example.env) |
| 自动同步日志 | `~/.coding-agent/logs/auto-update.log` |

目录软链内普通内容随主 checkout 更新生效。新增/删除技能或修改原生配置基线后重跑安装；旧配置迁移保留原件，已有用户值不覆盖。配置项及安装行为以 [install.sh](install.sh) 和示例文件为准。

首次安装或更改 Codex hook 命令后，仍需在 `/hooks` 审阅信任并核对实际触发。格式化 hook 是尽力修复，提交前 lint 继续作为门禁。已打开的会话不保证加载新指令，合入后用新会话工作。

自动同步由 [scheduler](scheduler/) 调用 [auto-update.sh](scripts/auto-update.sh)，使用 coding-agent-config 任务名。网络失败、工作区脏或无法快进时保留现场并写日志；安装中断的标记供下次补跑。停止自动同步可在主 checkout 运行 `bash scheduler/uninstall.sh`。首次安装、无调度器的环境仍需手动更新。

## 日常工作流

正式开发用 `/start` 在当前模式中先调查现状并给出方案摘要和完整提纲，无需切换原生 Plan 模式。用户批准一次后创建工作树，将批准版保存在 `docs/<N>-<中文主题>/PLAN.md`，再实施、验证和审查。只讨论时留在聊天里。局部小改用 `/quick`，自主调查、验证和提交，免计划审批与轮次文档；超范围交回调用方。

Codex 在 `/start` 开始实施时将当前会话命名为 `r<N>-<中文描述>`；`/finish` 完成适用的提交与收尾后追加 `-已完成`。通过 [会话标题工具](scripts/codex_session_title.py) 调用现有 App Server 并读回核验，不依赖自动标题摘要。工具使用 `uv run --script`，要求 uv、Python ≥3.11（由 uv 准备）及脚本声明的 websockets 依赖；首次运行可能下载运行时或依赖。当前支持暴露 Unix 控制 socket 的主机，要求 `CODEX_THREAD_ID`，默认从 `codex app-server daemon version` 发现服务，也可用 `--socket` 指定已知绝对路径。手机远程复用主机上的会话，无需手机端安装；客户端显示刷新需实际核对。连接失败会明确报告并继续开发，不启动服务、不改数据库。新脚本和既有技能随主 checkout 的目录软链更新生效。

提交按完整交付单元组织，同一次连续收尾的文档集中提交；已有明确授权在原范围内持续有效。`/finish` 默认在本地 FF 合入本轮提交，并在核验成果已保全后清理本轮 worktree、本地分支与 backup tag；明确说“不要清理”或用 `--no-cleanup` 即保留，`--keep-backup` 可只留备份。显式 `--squash` 可在合入前将本轮多个未发布提交压为一个；默认不压缩，已发布或共享历史不改写，压缩前备份并核对最终文件树及 issue 关联。未保全资产及未合入成果仍受保护，`--no-merge` 可跳过合入，远端推送须另有授权。`/finish` 不再固定询问“刻意不做”项，需归档时由用户主动要求；最终报告区分提交、本地合入、推送与部署状态。

| 技能 | 用途 |
| --- | --- |
| [backlog](skills/backlog/SKILL.md)、[triage](skills/triage/SKILL.md) | 创建 issue、只读盘点与排序 |
| [start](skills/start/SKILL.md)、[finish](skills/finish/SKILL.md) | 开轮对齐与开发收尾 |
| [quick](skills/quick/SKILL.md) | 不落轮次记录的小改，自动提交；`--worktree` 隔离工作区 |
| [commit](skills/commit/SKILL.md)、[review-loop](skills/review-loop/SKILL.md) | 提交、独立审查与修复迭代 |
| [rebase](skills/rebase/SKILL.md)、[pybump](skills/pybump/SKILL.md) | 直线历史整理、Python 版本发布准备 |
| [bootstrap](skills/bootstrap/SKILL.md)、[sync-project-config](skills/sync-project-config/SKILL.md) | 新项目初始化、已有项目模板同步与接入 |
| [devtree](skills/devtree/SKILL.md) | 已冻结：仅用于存量开发树修复 |
| [paper-read](skills/paper-read/SKILL.md) | 论文阅读笔记 |
| [routine-dev](skills/routine-dev/SKILL.md)、[routine-slim](skills/routine-slim/SKILL.md) | 自动开发明确需求、定期清理指令 |

review 规格以技能、[Codex 角色配置](agents/codex-review.toml)与 [DSH 角色配置](agents/dsh-review.toml) 为准；CC 定义在 [agents](agents/)。三个平台均使用独立 context，能力不足时按既定链降级并报告。DSH 的委托深度上限为 1，编队由主会话直启 reviewer，角度不变；reviewer 路由跟随主会话。它不能证明模型质量不会下降，也不能消除同模型盲区。

## 规则的放置与维护

- 全局入口保存个人偏好、协作和授权边界，以及领域路由。
- [playbooks](playbooks/) 保存领域选择和条件式指引；SDK、部署和排障细节只在相应任务加载。
- skills 保存流程的权威正文，调用方只保留所需入口；[templates/MECHANICS.md](templates/MECHANICS.md) 统一模板落点和合并规则。
- 一次经验先在来源项目修实现、补测试或文档；只有能说明跨项目收益且现有工具/规则不足时，finish 才提出共享候选。跨仓 issue 仍经确认。
- 普通规则可以删除、收窄或退役；事故历史已有 Git/issue 可追溯，不另建档案。保留偏好、安全边界与审查强度，不以字符数或删除比例验收。

[scripts/context_budget.py](scripts/context_budget.py) 提供体量描述和部分引用检查；它不覆盖所有链接、章节与语义依赖，历史 token 估算也不是当前模型的实测成本。

## 跨项目模板

模板由 `_common` 与可组合的 stack 组成。前后端可叠加，单包 Python 与 uv workspace 二选一；stack 的实际清单、落点及版本以 [templates](templates/) 为准，避免在 README 再维护副本。

`/bootstrap` 用于新项目，`/sync-project-config` 用于已有项目的 adopt 或后续同步。已有文件冲突保留用户决策；配置复制、fragment 合并、CI 变体与可跑化步骤统一按 [模板机制](templates/MECHANICS.md)。技能清单与业务 CLI 可使用 `cli-plugin` stack，但不会自动安装 CLI 或注册市场。

## 后台自动化

现有 claude.ai 调度保留，不因本轮改写转换成 Codex 自动化；环境能力按实际工具核验。

| routine | 工作方式 |
| --- | --- |
| routine-dev（每周一/三/五） | 目标明确的 issue 按优先级与关联关系组批，Agent 自主实现、验证、review，提交主题 PR 等人工合入 |
| routine-slim（每周日） | 有界盘点现有指令，一次处理 1–3 个有价值目标；允许普通规则退役，没有候选就退出，不再要求增长超过 15% |

两者都在独立 worktree 中执行，复用 Quick 的轻量隔离规则，不切换或清理主 checkout；PR 成功后清理已保全的干净工作树，失败保留成果与恢复路径。两者都排除在途 PR 涉及的文件，保留各自白黑名单；远端写操作仅新分支、PR 和该 PR 描述，不改标签/评论、不强推、不触发合入。routine-slim 不能改自身、另一 routine、全局/项目入口、角色配置或执行脚本，也不能借删减撤掉权限、审查强度与个人偏好；技能内的文档仪式与默认产出可以收缩，与宪法冲突的只报告。准确范围见两份技能与 [项目约束](AGENTS.md)。

修改 review 规则的任务按起始版本检查自身。routine 的规则禁令不等于凭据隔离，owner 凭据不能区分人和 Agent。

### PR 的人工合入入口

人可以在 PR 加 `ff-merge` 标签或评论 `/ff`，触发 [ff-merge 工作流](.github/workflows/ff-merge.yml)。实现见 [ff-merge.sh](.github/scripts/ff-merge.sh)：快进合入，必要时 rebase，冲突停止；关联 issue 的关闭另由脚本处理并回执。自动 routine 不得触发此入口。

涉及 workflow 文件的 PR 按工作流返回的限制处理，必要时本地合入，不提升 routine 权限绕过。普通开发轮的本地收尾仍按 `/finish`，不自动 push。

## 回退

批准版计划与 commit body 承担验证、行为变化和回退点。已合入版本通过 revert 对应提交回退，保留后来工作，不重置共享历史；新增/删除技能或配置基线变化后，从主 checkout 重跑安装。第 64 轮的具体范围与回退记录见 [个人 Harness 重构](docs/64-个人Harness零基重构/SUMMARY.md)。
