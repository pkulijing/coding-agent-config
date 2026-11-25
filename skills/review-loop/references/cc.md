# review-loop · Claude Code 委派说明

> 读者：在 Claude Code 运行时执行 `/review-loop` 的主会话 · 获取 CC 端命名 reviewer 委派、参数真源与降级的具体规则

实际环境使用 CC 命名 `Agent` 工具（`subagent_type`）时，走本入口。不能仅根据平台名称判断工具不可用。

## 资源预检补充

除 `SKILL.md` Step 4 共享资源外，还须检查本次需要的命名定义在 `$HOME/.claude/agents/` 下可读（`code-reviewer.md`，重档另含 `code-reviewer-deep.md`）。

CC 注册入口缺失但共享定义与清单完整时，先报告部署缺口并给出主 checkout 安装修复命令，再按 Step 5 实际核验命名类型；调用失败才进入既定降级链。文件都在但类型仍未注册时也走同一核验，不能把文件存在当作调用已成功。

## ① 平台首选编队

1. **并行启动命名 reviewer**：主会话按 `SKILL.md` Step 3 档位表直接并行起命名子 agent：
   - 角度 ①②③（重档另加 ④）→ `subagent_type: code-reviewer`
   - 重档角度 ⑤ → `subagent_type: code-reviewer-deep`
   - **按当前环境里 Agent 工具的实际 schema 填参** —— 该 schema 随 CC 版本漂移，不照抄记忆里的字段清单。
   - 每份委派 prompt 带上绝对仓库根、对应角度的 `references/angles.md` 逐字原文、已定设计前提及反例完整性硬要求。
2. **不要传 `model` 入参**：模型解析顺序是「环境变量 > 单次调用的 `model` 参数 > agent 定义的 frontmatter」—— 传了就会盖掉定义里钉死的那个（`code-reviewer-deep` 会被从 `opus` 打回去）。思考档没有单次调用入参，只认 frontmatter，所以**编队档位的唯一真源是 `agents/*.md`**。
3. **结构性只读**：命名定义自带 `disallowedTools: Edit, Write, NotebookEdit, Agent`，提供结构性只读与禁止再扇出。

## 失败与降级（对应 `SKILL.md` Step 5）

- 命名 agent 实际返回未注册或调用失败时，按 Step 5 门槛降到 ②（通用类型 `general-purpose` 等）。
- **② 是「不要传 `model`」的唯一例外**：通用类型没有 frontmatter 可继承，必须显式传 `model`（照抄 `agents/code-reviewer.md` / `agents/code-reviewer-deep.md` 的 frontmatter），并在 prompt 写死「只读不写：不修改任何文件」，同时自带对应角色正文与角度原文。
- 结果顶部按实报告能力损失：CC 通用类型可能丢失 effort 固定与结构性只读（只读仅由任务书约束）。
