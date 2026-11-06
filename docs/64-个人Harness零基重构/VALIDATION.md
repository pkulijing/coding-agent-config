# 验证范围与边界保留

## 审查基线

本轮按 `1e5cb3e5da49bea7195ab472c070167c92e70c0b` 的 commit、review-loop、角度清单和角色配置审查。该版本已从 Git 物化至临时目录，任务书显式指定此基线；不从待审规则取放行标准。

改动跨全局入口、技能编排、领域入口与脚本，按原规则采用重档：orchestrator 一名、普通 reviewer 四名、deep reviewer 一名，角度①至⑤；Codex 模型/medium 思考档取基线 codex-review.toml。只读由任务书约束，未宣称工具强制只读。五个角度均完成，第一轮 clean，无降级，详见 REVIEW.md。

## 保留要求的落点

| 要求 | 最终落点与核对 |
| --- | --- |
| 中文与实际 Agent 署名 | GLOBAL_AGENTS 的称呼和语言、git 规则；commit 按实际端署名 |
| Git 与 issue 偏好 | 按目录 gitignore、三轴标签、helper、无本地 backlog；finish 区分完整交付与部分交付 |
| 需求—计划—执行—总结 | 全局生命周期与 start/finish；quick/design 例外仍在各自技能 |
| 人工方向决定 | 关键假设失效、未授权方向取舍、重叠实现取舍仍等待确认 |
| 自动化能力 | worktree、自动提交、独立 review、两轮留痕与无人值守出口保留；模型和思考档配置未改 |
| 保护已有工作 | 全局保全要求；start/rebase/finish 的明确路径、备份、工作区与归属检查 |
| 凭据与权限 | .env约定、TLS校验、routine文件白黑名单及远端写操作边界；不自动合入或改调度注册 |
| 成功核验 | 全局响应契约；helper close 后回读状态，失败明确报告结果未确认 |
| 个人栈选择 | uv/ruff、npm/Biome、布局/import/命名、暗色/shadcn、飞书署名保留；设备版本组合回到项目 |
| 规则准入与退出 | finish 无有效候选不问；routine-slim 允许普通规则退役，仍保护偏好、安全与工作流能力 |

## 路由核对

- 普通 Python 修改只需短 python 入口；发布再读 packaging；Rich、文件同一性、Uvicorn 只读 runtime 对应节。
- LLM 文本接入不加载多步编排；涉及工具/拆分或运行中会话配置才读 orchestration 对应节。
- 短 shell 命令不加载进程管理；后台任务与超时才读 processes；CI高影响脚本仍要求沙盘。
- start → commit → review-loop → finish 的调用、异常和确认出口保留；README 触发条件在 finish 入口直接可判。
- 两条 routine 的任务授权仍分开；普通规则退役不扩展文件范围。新增 playbooks/references 不在原 routine 写白名单，需人类授权开发轮维护，未借此次拆分扩大权限。

## 自动与人工检查

代码配套的红绿测试、原生 CLI 核验及回归结果见 VALIDATION-helper.md。领域原文来源与模板验证见 VALIDATION-playbooks.md，技能边界核对见 VALIDATION-skills.md。独立审查结果单列 REVIEW.md。

引用检查使用现有 context_budget check-refs，并额外检查本轮 Markdown 相对链接与章节引用；范围包括新增文件。脚本不覆盖所有自然语言引用或加载语义，人工路由核对补足本轮改动的接壤处，不宣称全仓语义已被程序证明。

本轮不改安装器、hook注册或调度器；不触发真实 issue 关闭、发布、合入服务或凭据操作。不做多模型任务重复、A/B或消融评测。静态与隔离测试证明本轮契约和本地编排的检查结果，不能证明模型行为质量不会下降，也不证明远端权限和线上任务实际运行。
