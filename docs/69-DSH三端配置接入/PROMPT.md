# 需求：把 DeepSeek Harness 接入为第三个使用端

## 背景

本仓此前只服务 Codex（主用）与 Claude Code（兼容入口），共享资源落在 `~/.coding-agent/`，两端各自只提供原生发现入口：

- Codex：`~/.codex/AGENTS.md` → `GLOBAL_AGENTS.md`，`~/.agents/skills/` 逐技能软链，`config.toml` 托管 hook 块。
- Claude Code：`~/.claude/CLAUDE.md` → `GLOBAL_AGENTS.md`，`~/.claude/skills/`、`~/.claude/agents/`、`settings.json` 基线合并。

DeepSeek Harness（下称 DSH，桌面端 0.2.2 系列）是新的本地 Agent 运行环境。实测它的发现语义与两端部分重合、部分不重合：

| 能力 | DSH 实际行为（已核验） |
| --- | --- |
| skill 发现 | 本地提供方按 rank 扫描 `<project>/.dsh/skills`、`<project>/.agents/skills`、`customSkillDirs`、`<dshHome>/skills`、`<agentsHome>/skills`；格式同为 `SKILL.md` + frontmatter，`disable-model-invocation` / `user-invocable` 与 CC 同名 |
| 项目指令 | 默认候选 `AGENTS.md` + `CLAUDE.md`（同目录按内容去重），并加载 `$DSH_HOME/AGENTS.md`、`<agentsHome>/AGENTS.md` 两条用户全局链 |
| 子 agent | `subagent`（独立 context，新会话只收任务书）与 `subagent_fork`（继承父会话历史）两个工具，支持 `provider` / `model` / `reasoning_effort` |
| MCP | `dsh-mcp-manager` 已随 web-app bundle 挂载，Settings 可增删服务器，`servers` 配置可写入 profile patch |
| hooks | 文档有 `dsh-hooks-claude-code` / `dsh-hooks-codex` 两个包，但当前 Desktop 安装未包含，无法仅靠配置启用 |
| 权限 | 使用 sandbox 模式 + 审批策略，没有 CC `allow`/`deny` 的按命令清单 |

现状问题：本仓在本机 DSH 会话里，项目 `AGENTS.md` 生效，但**用户全局 `GLOBAL_AGENTS.md` 没有被任何一条链加载**（`$DSH_HOME/AGENTS.md` 与 `~/.agents/AGENTS.md` 都不存在）；提交前 review 的编队只能按 CC / Codex 两种入口写，DSH 里无对应分支。

## 需求

经用户确认，本轮落地四件事：

1. **补全局规则入口**：安装脚本为 DSH 部署用户全局指令链入口，使 `GLOBAL_AGENTS.md` 在 DSH 会话中生效。
2. **review-loop 增加 DSH 委派入口**：用 DSH 原生 `subagent` 工具按档位表直启 N 个角度 reviewer（DSH 委托深度为 1，没有 orchestrator 子 agent），模型与思考档仍由单一真源文件提供，不许继承主会话。
3. **把 DSH 纳入 install.sh 的多端部署**：部署动作幂等、保留用户已有文件、只在 DSH 已安装时执行，并在 README / AGENTS.md 的部署表里如实登记。
4. **迁移 MCP**：把 CC 现用的 `gitlab-anyverse`（http）与 `playwright`（stdio）两条服务器配置迁移到 DSH profile 的 mcp-manager。

## 范围与边界

- 不做 hooks 插件化：`fix-after-edit` 在 DSH 侧本轮不迁移，提交前 lint 继续作为门禁；不因此删除 Codex / CC 现有 hook。
- 不改 DSH 的 skill 发现配置（`~/.agents/skills` 已被默认扫描，不新增 `customSkillDirs`），也不新增 `~/.dsh/skills` 投影。
- 不迁移 CC 的 `permissions` 清单与 `agents/*.md` 注册；DSH 端只按任务书约束只读。
- 不安装 DSH 缺失的 `dsh-hooks-*` / `dsh-subagent-claude-code` 等包；不修改 npm 缓存属主。
- MCP 只迁移上述两条，凭据不落明文：两条配置当前都不带密钥，保持原样。
- 不改审查判据、角度清单与降级门槛；改动只新增第三方平台入口。

## 验收

1. 从主 checkout 重跑 `bash install.sh` 后，`~/.agents/AGENTS.md` 指向本仓 `GLOBAL_AGENTS.md`，重复运行幂等；用户原有的 `~/.agents/AGENTS.md` 若存在会被备份而非覆盖。
2. DSH 未安装（`$HOME/.dsh` 不存在）时安装脚本跳过该步，不报错、不创建目录。
3. `agents/dsh-review.toml` 与 `agents/codex-review.toml` 同构，但只含 `[reviewer]` / `[deep_reviewer]` 两个角色（DSH 委托深度为 1，没有 orchestrator 子 agent），两个角色的 provider / model / reasoning_effort 均为本机实际可用的档位。
4. `review-loop` 的 Step 3、Step 4、Step 5 与资源预检都有 DSH 分支，且明确禁止用 `subagent_fork`（会继承开发上下文，破坏独立审查）。
5. 隔离 HOME 下 `CCG_INSTALL_LIB_ONLY=1` 函数级测试与 `bash -n install.sh` 通过。
6. DSH profile 里 `mcp-manager` 的 `servers` 含两条迁移项；配置写坏时不影响其他行。
