# coding-agent-config

个人 Coding Agent harness，集中维护开发规范、技能、独立 review、脚本、hooks 和跨项目模板。目标是让 Agent 自主完成工作，减少人工纠正与维护；Codex 主用，Claude Code 保留兼容入口。

日常规则见 [GLOBAL_AGENTS.md](GLOBAL_AGENTS.md)，本仓开发约束见 [AGENTS.md](AGENTS.md)。需求以 issue 为真源：[未关闭项](https://github.com/pkulijing/coding-agent-config/issues?q=is%3Aissue+is%3Aopen+label%3Apriority%3AP0%2Cpriority%3AP1%2Cpriority%3AP2)，开发历史见 [DEVTREE](docs/DEVTREE.md)。

## 安装与维护

准备 jq，在本仓**主 checkout** 运行 `bash install.sh`。安装拒绝 linked worktree，保留用户配置与第三方技能。Codex 可在没有 CC 安装的机器上独立使用。

| 内容 | 部署位置 |
| --- | --- |
| 共享资源目录 | `~/.coding-agent/{skills,scripts,templates,playbooks,hooks,agents}`，链接到本仓 |
| 稳定仓库入口 | `~/.coding-agent/global-repo` |
| Codex 指令与配置 | `${CODEX_HOME:-~/.codex}/AGENTS.md`、`config.toml` |
| Codex 技能发现 | `~/.agents/skills/`，逐技能链接 |
| 用户真实配置 | `~/.coding-agent/config.env`，示例见 [user.config.example.env](user.config.example.env) |
| 自动同步日志 | `~/.coding-agent/logs/auto-update.log` |

目录软链内普通内容随主 checkout 更新生效。新增/删除技能或修改原生配置基线后重跑安装；旧配置迁移保留原件，已有用户值不覆盖。配置项及安装行为以 [install.sh](install.sh) 和示例文件为准。

首次安装或更改 Codex hook 命令后，仍需在 `/hooks` 审阅信任并核对实际触发。格式化 hook 是尽力修复，提交前 lint 继续作为门禁。已打开的会话不保证加载新指令，合入后用新会话工作。

自动同步由 [scheduler](scheduler/) 调用 [auto-update.sh](scripts/auto-update.sh)，使用 coding-agent-config 任务名。网络失败、工作区脏或无法快进时保留现场并写日志；安装中断的标记供下次补跑。停止自动同步可在主 checkout 运行 `bash scheduler/uninstall.sh`。首次安装、无调度器的环境仍需手动更新。

## 日常工作流

明确需求用 `/start`：先在项目 `.worktrees/` 隔离工作，写需求和计划，用户确认方向后实施；Agent 自主提交，每次提交前独立 review，最后 `/finish` 总结、合入与清理。轻量改动用 `/quick`，尚需讨论的方案用 `/design`。

| 技能 | 用途 |
| --- | --- |
| [backlog](skills/backlog/SKILL.md)、[triage](skills/triage/SKILL.md) | 创建 issue、只读盘点与排序 |
| [start](skills/start/SKILL.md)、[finish](skills/finish/SKILL.md) | 开轮计划与开发收尾 |
| [design](skills/design/SKILL.md) | 主题工作树中的方案讨论与归档 |
| [quick](skills/quick/SKILL.md) | 不建开发文档的小改，自动提交 |
| [commit](skills/commit/SKILL.md)、[review-loop](skills/review-loop/SKILL.md) | 提交、独立审查与修复迭代 |
| [rebase](skills/rebase/SKILL.md)、[pybump](skills/pybump/SKILL.md) | 直线历史整理、Python 版本发布准备 |
| [bootstrap](skills/bootstrap/SKILL.md)、[sync-project-config](skills/sync-project-config/SKILL.md) | 新项目初始化、已有项目模板同步与接入 |
| [devtree](skills/devtree/SKILL.md) | 从 Epic 结构生成开发树 |
| [paper-read](skills/paper-read/SKILL.md) | 论文阅读笔记 |
| [routine-dev](skills/routine-dev/SKILL.md)、[routine-slim](skills/routine-slim/SKILL.md) | 自动开发明确需求、定期清理指令 |

review 规格以技能与 [Codex 角色配置](agents/codex-review.toml) 为准；CC 定义在 [agents](agents/)。两端均使用独立 context，能力不足时按既定链降级并报告。它不能证明模型质量不会下降，也不能消除同模型盲区。

## 规则的放置与维护

- 全局入口保存个人偏好、协作和授权边界，以及领域路由。
- [playbooks](playbooks/) 保存领域选择和条件式指引；SDK、部署和排障细节只在相应任务加载。
- skills 保存流程的权威正文，调用方只保留所需入口；[templates/MECHANICS.md](templates/MECHANICS.md) 统一模板落点和合并规则。
- 一次经验先在来源项目修实现、补测试或文档；只有能说明跨项目收益且现有工具/规则不足时，finish 才提出共享候选。跨仓 issue 仍经确认。
- 普通规则可以删除、收窄或退役；事故历史已有 Git/issue 可追溯，不另建档案。保留偏好、安全边界和工作流能力，不以字符数或删除比例验收。

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

两者都排除在途 PR 涉及的文件，保留各自白黑名单；远端写操作仅新分支、PR 和该 PR 描述，不改标签/评论、不强推、不触发合入。routine-slim 不能改自身、另一 routine、全局/项目入口、角色配置或执行脚本，也不能借删减撤掉权限与工作流能力。准确范围见两份技能与 [项目约束](AGENTS.md)。

修改 review 规则的任务按起始版本检查自身。routine 的规则禁令不等于凭据隔离，owner 凭据不能区分人和 Agent。

### PR 的人工合入入口

人可以在 PR 加 `ff-merge` 标签或评论 `/ff`，触发 [ff-merge 工作流](.github/workflows/ff-merge.yml)。实现见 [ff-merge.sh](.github/scripts/ff-merge.sh)：快进合入，必要时 rebase，冲突停止；关联 issue 的关闭另由脚本处理并回执。自动 routine 不得触发此入口。

涉及 workflow 文件的 PR 按工作流返回的限制处理，必要时本地合入，不提升 routine 权限绕过。普通开发轮的本地收尾仍按 `/finish`，不自动 push。

## 回退

每轮在 SUMMARY 记录验证、行为变化和回退点。已合入版本通过 revert 对应提交回退，保留后来工作，不重置共享历史；新增/删除技能或配置基线变化后，从主 checkout 重跑安装。第 64 轮的具体范围与回退记录见 [个人 Harness 重构](docs/64-个人Harness零基重构/SUMMARY.md)。
