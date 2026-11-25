# review-loop · Codex 委派说明

> 读者：在 Codex 运行时执行 `/review-loop` 的主会话 · 获取 Codex 端并行委派独立 reviewer 与降级的具体参数及约束

实际工具有 `collaboration.spawn_agent` 时，走本入口，不调用 CC 的 `subagent_type`。

## ① 平台首选编队

1. **读取配置**：读取 `~/.coding-agent/agents/codex-review.toml`（与 `~/.coding-agent/agents/code-reviewer.md`、重档另读 `code-reviewer-deep.md`、`~/.coding-agent/skills/review-loop/references/angles.md`）。两个 reviewer 角色的模型与思考档以此 TOML 文件为单一真源，不照抄 CC 的 sonnet/opus。
2. **并行启动 reviewer**：主会话按 `SKILL.md` Step 3 档位表直接并行创建 reviewer：①②③（重档另加 ④⑤）。
   - `fork_turns="none"`（新 context 只接收本次任务书，避免继承开发过程的先入之见）。
   - 普通角度（①②③④）的 `model` 与 `reasoning_effort` 取 `[reviewer]`；重档 ⑤ 取 `[deep_reviewer]`。
   - 每份任务书自带：`SKILL.md` Step 4「各端共用的委派与汇总契约」的全部共用约束、对应的 `agents/code-reviewer.md` 或 `agents/code-reviewer-deep.md` 正文（不把其 CC frontmatter 当模型配置），以及 `references/angles.md` 对应角度的逐字原文。
3. **并发槽位处理**：并发槽位不够时分批创建，等待前一批完成再起下一批；总数和角度覆盖不变。槽位限制本身不能成为少审角度的理由。
4. **只读约束声明**：Codex 通用子 agent 未必具备 CC `disallowedTools` 的结构性限制，必须在每份任务书写明「只读不写、不提交、不再派生子 agent」，并在结果中如实说明只读由指令约束；不得宣称工具已强制只读。这属于已声明的平台实现，不是丢失独立 context 的自审降级。

## 失败与降级（对应 `SKILL.md` Step 5）

- 真正调用失败才按 Step 5 逐档降级；模型名不可用也算明确失败，不能悄悄换模型或继承主会话档位。
- 实际工具没有模型 / 思考档参数时，保住独立 context 并逐项声明未固定的属性。
- 落到 ②（通用子 agent）时，按 `agents/codex-review.toml` 同时传 `model` 与 `reasoning_effort`、`fork_turns="none"`，并写死「只读不写：不修改任何文件」；参数已传入时不能声称 effort 丢失。
