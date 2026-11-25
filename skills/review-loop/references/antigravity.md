# review-loop · Antigravity 委派说明

> 读者：在 Antigravity 运行时执行 `/review-loop` 的主会话 · 获取 `define_subagent` / `invoke_subagent` 委派、只读快照与降级规则

实际工具有 `define_subagent` 与 `invoke_subagent` 时，走本入口。

## ① 平台首选编队

1. **读取配置**：读取 `~/.coding-agent/agents/antigravity-review.toml`（与 `agents/code-reviewer.md`、重档另读 `code-reviewer-deep.md`、`references/angles.md`）。`invoke_subagent` 只支持 `Model` 档位（`inherit` / `flash_lite` / `flash` / `pro`），无独立 `reasoning_effort` 参数；结果顶部须如实注明「思考档未固定（平台无独立 effort 参数）」。
2. **主会话先预采集 git 快照**：Antigravity 的 `EnableWriteTools: false` 会同时移除写文件与命令行（shell）工具，子 agent 仅有只读文件检索能力，无法自己跑 `git -C`。因此主会话在委派前先执行 `git rev-parse --show-toplevel`、`git status --short` 与 `git diff`（将完整 diff 写入对话 scratch 文件或内联），列出全部修改 / 未跟踪文件的绝对路径；**重档（角度 ④）**另预采集改动文件的近期 `git log` 快照。
3. **注册只读 reviewer 角色**：用 `define_subagent` 注册本次需要的只读角色（`SystemPrompt` 传对应 `agents/*.md` 正文，不把 CC frontmatter 当模型配置，并附加一条 Antigravity 运行时补充：在 `EnableWriteTools: false` 无 shell 环境下，用主会话预采集的仓库根与 git status/diff 快照替代 `git -C` 自证与取 diff，以绝对路径 `read_file` 核对仓库文件，不因无 shell 中止）：
   - `code-reviewer`：`EnableWriteTools: false`、`EnableSubagentTools: false`、`EnableMCPTools: false`
   - 重档另注册 `code-reviewer-deep`：`EnableWriteTools: false`、`EnableSubagentTools: false`、`EnableMCPTools: false`
   这提供了**结构性只读**与 reviewer 禁止再扇出。
4. **并行启动 reviewer**：主会话按 `SKILL.md` Step 3 档位表用 `invoke_subagent` 并行起各角度 reviewer（`code-reviewer` 的 `Model` 取 `[reviewer]`，重档 ⑤ 用 `code-reviewer-deep` 取 `[deep_reviewer]`，`Workspace: "inherit"`）。每份 prompt 带上仓库根、改动 / 新增文件绝对路径清单、git 快照路径、`references/angles.md` 对应角度逐字原文、已定设计前提及反例完整性硬要求。新子 agent 不继承父对话历史，等价于 `fork_turns="none"`；启动后结束当前 turn 等系统唤醒通知，不轮询。

## 失败与降级（对应 `SKILL.md` Step 5）

- 若 `define_subagent` 或自定义 reviewer 调用失败，按 Step 5 降级到 ②：主会话直接并行调用内置只读 `research` 子 agent 各审一个角度（同样传入预采集的仓库根、git 快照、角色正文与角度原文，`Model` 按 `agents/antigravity-review.toml` 传入），保住独立 context 与结构性只读，并按实注明思考档未固定。
