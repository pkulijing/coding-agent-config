# coding-agent-config

管理 Coding Agent 全局规范、技能、review、hooks、脚本、模板和自动更新。Codex 为主要运行端，Claude Code 保留兼容入口；共享资源统一部署到 `~/.coding-agent/`。

## 当前文件与入口

- `GLOBAL_AGENTS.md`：全局宪法；安装链接到 `${CODEX_HOME:-~/.codex}/AGENTS.md`，已有 CC 安装可链接到其 `CLAUDE.md`。
- `AGENTS.md`：本项目规则正文；根 `CLAUDE.md` 只有 `@AGENTS.md` 兼容引用。新项目和已有子目录规则迁移遵循 bootstrap/sync，不能维护两份正文。
- `skills/`：共享流程；Codex 的发现入口为 `~/.agents/skills/`，资源引用统一从 `~/.coding-agent/skills/` 读取。
- `scripts/`、`templates/`、`playbooks/`、`hooks/`、`agents/`：整体软链到 `~/.coding-agent/` 同名目录；修改内容即时生效。
- `agents/codex-review.toml`：Codex review 角色模型和思考档的单一真源，由技能读取后传给原生子 agent 工具；不是原生注册配置。`agents/*.md` 保留 CC 定义及 reviewer 共用纪律。
- `codex.config.base.toml`：Codex 原生配置基线；托管 hook 块合并，块外用户配置保留；规则长度上限仅在用户未设置时补缺。
- `settings.base.json`：CC 兼容配置；只在 CC 已存在时部署。共享技能不依赖此文件或 CC 安装。
- `user.config.example.env`：配置示例；真实值为仓库外 `~/.coding-agent/config.env`，旧配置迁移不删除原件，新配置 user-wins。
- `uv.config.base.toml`：缺失时 seed `~/.config/uv/uv.toml`，已有内容不覆盖。
- `scheduler/`：跨平台自动同步，任务名使用 `coding-agent-config`，日志与运行标记位于 `~/.coding-agent/`。
- `.worktrees/`：开发工作树；按目录维护 `.gitignore`，不用 Codex 默认托管目录替代。
- `docs/`：中文开发记录；历史轮次保持原貌。

## 开发注意事项

- **安装只能在主 checkout 运行**；linked worktree 必须拒绝，否则全局软链在工作树删除后断裂。测试可用 `CCG_INSTALL_LIB_ONLY=1` source 函数，在临时 HOME 中验证；新测试在 `docs/61-Codex全盘迁移/`。
- 新增/删除技能或修改原生配置基线后需从主 checkout 重跑 `bash install.sh`。目录软链覆盖的脚本、模板和规则内容改动不必重装。
- Codex hook 的正确 schema 不能证明它已经运行；配置修改后必须经 `/hooks` 审阅信任，再核对触发。hook 尽力自动修复，commit 的 lint 门禁仍必须执行。
- 工作树操作用原生 Git 明确指定 `.worktrees/` 路径；所有调用显式设置 `workdir` 或 `git -C`，不要假定 `cd` 或聊天项目自动切换。
- review 的对象是本次工作树全部改动（含新文件）。按当前端的原生委派能力运行独立 context 编队，不能因平台名为 Codex 就降级。编队和降级规则以 review-loop 技能为准。
- 共享资源从 `~/.coding-agent/` 读取，不能重新引入 `~/.claude/scripts` 等依赖。原生端目录只用于注册入口；平台特定 CLI、事件、模型和权限不能机械替换。
- issue/label 操作走 `~/.coding-agent/scripts/platform_issue.py`，不绕过 helper；`.github/labels.yml` 修改后需同步才可在目标平台使用。
- GitHub 与 GitLab 模板机制见 `~/.coding-agent/templates/MECHANICS.md`，不要另写重复的落点或合并规则。
- 历史 `docs/` 中的旧项目名、路径和平台实验是当时记录，不批量替换。当前 README、技能和配置应使用现行名称。
- 不把 `playbooks/` 改挂到 CC 的 `rules/`：后者会把全部文档注册为常驻 memory。任何原生保留目录的新增挂载都先核实其发现语义。
- 开发流程遵循 `GLOBAL_AGENTS.md` 的需求、计划、执行、总结四步模式。

- **本仓有两条云端定时 routine，它们的 SKILL.md 都是安全边界、别当普通文档改**：
  - `/routine-dev`（每周一 / 三 / 五，**曾名 `/routine-docs`**）把够格自动做的 issue 做成 PR，**两条通道授权强度不同**：**自动通道**由模型保守分诊、**只许落文档**；**标记通道**要 owner 给 issue 打 `auto:take` label 背书，落点放开到 `skills/`（除自己）/ `templates/` / `scripts/` / `hooks/`。它把**外部 issue 正文**变成文件内容，是 prompt-injection 面 —— 原先由「落点只限文档」承担的安全职责，在标记通道里换成了人工背书，故**四条红线绝不因 `auto:take` 放宽**：`skills/routine-dev/**`（自己）、`agents/**`（自己的检查员）、`install.sh`、`.github/**`。完整推导见 `skills/routine-dev/references/security-boundary.md`（§3 是标记通道那一节）。**一次运行只出一个 PR**（选中那条做不成就换下一条，最多试 3 条），写权限面穷举为「push 一条新分支 / 开一个 PR / 编辑该 PR 的描述」—— 不打任何 label、不发任何评论、不 force-push
  - `/routine-slim`（每周日）按增长阈值把指令面精简一轮并出 PR。它**不需要逐条授权**就能改 `skills/*/SKILL.md` 与 `playbooks/*.md`（输入只有仓库自身、不读外部文本、只做删除与搬移），但**永不碰自己、`/routine-dev`、`agents/`、`.github/`、`install.sh`、`scripts/`、`hooks/`、`templates/`**，且对 `GLOBAL_AGENTS.md` 与本文件**只报告不动手**。注意 `skills/review-loop/references/angles.md` 在它的可改范围内、但**压缩角度清单等于降低 review 检出率**（清单是 reviewer 跑低思考档的配套条件），精简前先读那份文件顶部的说明
  - **两条 routine 现在都能改 `skills/*.md`，但放宽的理由各是各的**（一个靠 owner 逐条背书、一个靠不读外部文本），**别互相援引**；撞车防线是双向的：各自开 PR 前都把「所有 open PR 碰过的文件」整体排除
  - 改 `.github/workflows/ff-merge.yml` 等于改自动写 `master` 的那条路。两条 routine 都**绝不以任何方式触发合入** —— `ff-merge` 的准入闸校验「发起人 == 仓库 owner」，而云端 routine 用的就是仓库主人的凭证，这道闸区分不了人和 agent
