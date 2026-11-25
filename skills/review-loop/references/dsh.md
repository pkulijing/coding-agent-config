# review-loop · DSH 委派说明

> 读者：在 DeepSeek Harness (DSH) 运行时执行 `/review-loop` 的主会话 · 获取 DSH 端 `subagent` 路由解析、档位传入与重试规则

实际工具有 `subagent` 时，走本入口。新会话只接收本次任务书，等价于 Codex 的 `fork_turns="none"`。**不要用 `subagent_fork`** —— 它继承父会话历史，等于把开发过程的先入之见带进审查。

## ① 平台首选编队

1. **读取配置**：读取 `~/.coding-agent/agents/dsh-review.toml`（与 `agents/code-reviewer.md`、重档另读 `code-reviewer-deep.md`、`references/angles.md`）。
2. **路由与档位先解析再传**：用 `list_subagent_models` 依次取授权 provider、该 provider 的 model、该 model 的思考档，然后显式传 `provider` / `model` / `reasoning_effort` 三者（DSH 拒绝只传 effort）。
   - 没有 model-selection 白名单时，授权集只有母对话路由一条，传它就是跟随主会话。
   - 思考档取 `agents/dsh-review.toml` 的目标档（`[reviewer]`；⑤ 取 `[deep_reviewer]`），该路由不支持就取它最高可用档。
   - 实际路由与档位写进结果顶部；目标档没拿到要写明，不许写成「已钉死」或「无减配」。
   - 没有 `list_subagent_models` 工具时三个字段全不传，按平台规则回落母对话路由，并注明「档位未固定」。
3. **并行启动 reviewer**：主会话按 `SKILL.md` Step 3 档位表同一轮并发起全部角度 reviewer。
   - `cwd` 传绝对仓库根。
   - 每份任务书必须自带：`SKILL.md` Step 4 共用约束、对应的 `agents/code-reviewer.md`（⑤ 用 `code-reviewer-deep.md`）正文（不把 CC frontmatter 当模型配置）、`references/angles.md` 对应角度逐字原文，以及「只读不写、不提交、不再派生子 agent」。
4. **只读约束声明**：DSH 对子 agent 没有结构性只读限制，只读由任务书约束 —— 结果须如实说明，不得宣称工具已强制只读。

## 失败与降级（对应 `SKILL.md` Step 5）

- 路由被 Session 策略拒绝（`child LLM route "..." is not allowed for this Session`）**不算编队能力缺失**：按第 2 条改用母对话路由重试一次。仍调不起来（provider 未注册、适配器报错）才算明确失败，按 Step 5 处理；换路由或降档都要写进结果顶部。
- 落到 ② 时仍按第 2 条解析并显式传参，写死只读约束；已显式传参时不能声称 effort 丢失，目标档未拿到则按实写明。
