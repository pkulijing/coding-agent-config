# 按平台拆分 review-loop 委派说明并移除独立 orchestrator

> 读者：本仓维护者与各平台 Coding Agent · 了解 review-loop 按平台渐进拆分与扁平编队重构的决策、范围与验收方式
> 来源：[#202 按平台拆分 review-loop 委派说明并评估编队开销](https://github.com/pkulijing/coding-agent-config/issues/202)（起始基线 SHA：`dca17ef0f6ae4765386c984a5198da7333e1377e`）

## 目标

1. 将 `skills/review-loop/SKILL.md` 中混载的四个平台（Codex、Claude Code、DSH、Antigravity）委派与降级细则拆分为按需加载的 `skills/review-loop/references/<platform>.md`，共同入口仅保留共享判据、档位表、平台路由、共用任务与汇总契约、降级门槛及收敛流程。
2. 经用户拍板，统一所有平台的编队形态：移除独立的 `review-orchestrator` 子 agent，由主会话直接并行启动各角度独立 reviewer，并在主会话完成去重、置信打分与只读探针验证。
3. 保持既有审查覆盖不变：默认 3 个 reviewer（①②③）、重档 5 个 reviewer（①②③④ + ⑤）、各端模型/思考档配置、置信 rubric、两轮上限与留痕契约均不变。

## 关键决策

- **移除独立 `review-orchestrator` 子 agent**：
  - 理由：每个角度的 finding 生成仍在独立子 agent context 中完成（保持无先入之见的审查）；主会话原本在 Step 6.1 就要复核证据，DSH 也已验证「主会话直启 + 汇总」模式可行。移除独立 orchestrator 每轮省掉 1 个子 agent 与 1 次串行中转，消除嵌套扇出失败面并统一四端架构。
  - 代价：去重与置信打分移回主会话，主会话直接接收 3–5 份原始 finding 列表（略增主上下文体积）。
- **四端分别落独立 reference（含 Antigravity）**：
  - 理由：issue #202 提出时只有三端，当前仓库已接入 Antigravity；拆为 `references/{codex,cc,dsh,antigravity}.md` 后，任意运行时只加载本端说明，不再背负其余三端细节。
- **与 #197 解耦**：
  - 理由：#197 涉及全仓渐进加载改造，本轮聚焦 #202，不扩大改动范围；本次也不调整普通改动的 reviewer 数量或触发节奏（#160）。
- **按开发起始基线自审**：
  - 理由：本轮修改审查规则与角色配置，提交前 review 严格按起始 SHA `dca17ef0f6ae4765386c984a5198da7333e1377e` 的基线规则与编队执行，不用新规则为自身放行。

## 实施提纲

1. 新增 `skills/review-loop/references/{codex,cc,dsh,antigravity}.md`，承接各端委派参数、资源要求、只读约束与降级细则。
2. 精简 `skills/review-loop/SKILL.md`：保留收敛判据、跳过规则、两档编队表（不含 orchestrator）、平台路由表、共用委派与主会话汇总契约、三档降级链（① 平台首选并行 reviewer > ② 通用并行 reviewer > ③ 主会话自审）及 Step 6 收敛规则。
3. 删除 `agents/review-orchestrator.md`，清理 `agents/codex-review.toml` 与 `agents/antigravity-review.toml` 中的 `[orchestrator]` 配置，同步更新 `agents/code-reviewer.md`、`agents/code-reviewer-deep.md`、`agents/dsh-review.toml`、`skills/review-loop/references/rationale.md`、`AGENTS.md` 与 `README.md` 中的相关描述。
4. 在 `tests/` 新增结构与引用测试，验证四端 reference 存在、由 `SKILL.md` 路由且活跃规则中无失效的 `review-orchestrator` 引用；运行 `bash scripts/check.sh` 验收。

## 验收

- `bash scripts/check.sh` 全绿（`pytest`、`docs_lint.py`、`context_budget.py check-refs`）。
- 核对四个平台在正常委派与委派失败（降级 ②/③）场景下均能从 `SKILL.md` 定位到对应 reference、配置文件及约束，且未丢失原有降级门槛、只读要求或角度覆盖。
- 按起始基线 SHA `dca17ef0f6ae4765386c984a5198da7333e1377e` 完成独立 review 并收敛后提交。
