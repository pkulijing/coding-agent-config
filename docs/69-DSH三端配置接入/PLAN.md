# 方案：DSH 作为第三个使用端

## 1. 已实证的前提

| 假设 | 核验方式与结论 |
| --- | --- |
| DSH 用户全局指令链读 `$DSH_HOME/AGENTS.md` 与 `<agentsHome>/AGENTS.md` | 读安装包 `@deepseek-ai/dsh-agent-instructions` 的 `src/config.ts` 与 README：默认候选 `AGENTS.md`/`CLAUDE.md`，两条用户全局链，agentsHome 默认 `~/.agents`（`DSH_AGENTS_HOME` 可覆盖） |
| DSH 默认扫描 `~/.agents/skills` | `dsh-skill-filesystem` README 根目录表：`user-agents` rank 500 = `<agentsHome>/skills`；本机会话 skill 目录即来自该根 |
| DSH 子 agent 的委托深度上限为 1 | 实跑探测：子 agent 工具列表含 `subagent`，但调用返回 `Delegation depth for subagent: current 1, maximum 1, remaining levels 0`，即 **子 agent 无法再扇出** |
| `subagent` 支持固定模型/思考档 | 工具签名含 `provider` / `model` / `reasoning_effort`；本机唯一 route 为 `deepseek-account/deepseek-flash`，思考档为 `off`/`low`/`high`/`max`（无 medium） |
| mcp-manager 的 `servers` 可从 profile patch 写入 | `dsh-mcp-manager` README：profile 的 `cordis.patch.yml` 按条目 id 替换完整 `servers` 映射；本机 row id 为 `mcp-manager`（web-app bundle） |

## 2. 改动清单

### 2.1 `install.sh`：新增 DSH 部署

- 新增 `deploy_dsh()`，在 `deploy_codex` 之后调用。
- 触发条件：`${DSH_HOME:-$HOME/.dsh}` 目录存在（与 `deploy_claude_compat` 的「已有安装才保留入口」同构）。
- 动作：`link_item "$REPO_DIR/GLOBAL_AGENTS.md" "${DSH_AGENTS_HOME:-$HOME/.agents}/AGENTS.md"`，先 `mkdir -p` agents 根。
- 不部署 `~/.dsh/AGENTS.md`：DSH 的全局链按 harness home → shared agents 根顺序读取，写共享根一份即可；`~/.agents` 已是 Codex skill 与 DSH skill 的共同入口，避免同一份规则出现两个 owner。
- 技能投影默认不重复部署：`deploy_codex` 已把每个技能链到 `~/.agents/skills/`，DSH 默认扫描该根；但 DSH 覆盖 `DSH_AGENTS_HOME` 时技能根随之改到 `<agentsHome>/skills`，此时 `deploy_dsh` 必须补一次 `deploy_skills "$agents_home/skills"`，否则该路径会静默丢光共享技能。

### 2.2 `agents/dsh-review.toml`：DSH review 模型与思考档真源

- 只定义 `[reviewer]` 与 `[deep_reviewer]` 两个角色：DSH 委托深度为 1，不存在 orchestrator 子 agent，保留一个不会被读的 `[orchestrator]` 会让「单一真源」变成误导。
- 取值：`provider = "deepseek-account"`、`model = "deepseek-flash"`；`reasoning_effort` 普通 reviewer 用 `high`（本机默认平衡档），deep 用 `max`。文件内注明「本机 route 无 medium 档」，避免照抄 CC 的 medium 被拒。

### 2.3 `skills/review-loop/SKILL.md`：DSH 委派入口

- Step 3 编队约束补 DSH 真源（`agents/dsh-review.toml`）。
- Step 4 新增「DSH 委派入口」：主会话直接并行起 N 个 reviewer（每个角度一个 `subagent`），**不得用 `subagent_fork`**（继承父会话历史 = 破坏独立 context）。
- 明确平台约束：委托深度上限 1，所以 orchestrator 子 agent 无法再扇出；汇总裁决留在主会话。该入口不解聘任何角度、不降模型档，因此不按 Step 5 降级链处理，但结果须注明「汇总在主会话」。
- 只读由任务书约束（DSH 无结构性只读限制），须如实声明，不能宣称工具已强制只读。
- 资源预检、Step 5 ② 的模型传参说明同步补 DSH。

### 2.4 `skills/review-loop/references/rationale.md`

- 在「两档编队」后补一条跨平台边界：DSH 的委托深度上限决定其编队形态，不构成减配；角度、置信 rubric 与两轮留痕不变。

### 2.5 `README.md`、`AGENTS.md`

- 部署表补 DSH 行：`${DSH_HOME:-~/.dsh}` 存在时部署 `${DSH_AGENTS_HOME:-~/.agents}/AGENTS.md`；技能默认沿用 `~/.agents/skills/`，自定义 agents 根时同步部署到该根的 `skills/`。
- 更正「Codex 通过 `~/.agents/skills/` 发现」的表述为「Codex 与 DSH 共用该根」。
- review 规格段补 DSH 角色配置。

### 2.6 MCP（不属于仓库文件）

- 在 `~/.dsh/profiles/desktop/cordis.patch.yml` 增加 `- id: mcp-manager` 行，`servers` 写入 `gitlab-anyverse`（streamable-http）与 `playwright`（stdio）。
- 两条配置当前都不含密钥，不写 `~/.dsh/.credentials.yaml`；若日后需要鉴权，改走 `${credential:REF}` 模板。

## 3. 关键设计决策

1. **全局规则入口选 `~/.agents/AGENTS.md` 而非 `~/.dsh/AGENTS.md`**：共享资源只有一份、原生目录只放发现入口是本仓既定原则；`~/.agents` 同时是两端技能根，指向 `GLOBAL_AGENTS.md` 的软链与 `~/.codex/AGENTS.md` 同构，且不把本仓写进 DSH 的 profile 目录。
2. **不新增 skill 根**：DSH 已扫 `~/.agents/skills/`，再加 `customSkillDirs` 只会产生第二份目录与竞争；CC 独有技能若出现，软链进同一根即可。
3. **DSH review 编队按平台约束重排，不按降级处理**：独立 context 的来源是每个 reviewer 的新会话，这一点完整保留；损失仅是汇总位置在主会话，且汇总本就是机械套用 rubric。把它写成 ② 会误导后续读者以为「能力失败」。
4. **reviewer 配置与编排分离**：模型档在 `agents/dsh-review.toml`，编队规则在 SKILL；改档只改一处，符合既有「单一真源」模式。
5. **MCP 迁移保持最小等价**：原样搬 transport / url / command / args，不擅自加 header、不启用 `--headless` 之外的新参数。

## 4. 验收用例

| # | 用例 | 期望 |
| --- | --- | --- |
| A1 | 临时 HOME 中 `DSH_HOME` 不存在，跑 `deploy_dsh` | 不创建目录、不报错、返回 0 |
| A2 | 临时 HOME 中 `~/.dsh` 存在且 `~/.agents/AGENTS.md` 不存在 | 创建软链，目标为 `<repo>/GLOBAL_AGENTS.md` |
| A3 | 重复执行 | 输出「已跳过」（幂等） |
| A4 | `~/.agents/AGENTS.md` 是用户真实文件 | 备份为 `AGENTS.md.bak` 并创建软链 |
| A5 | `DSH_AGENTS_HOME` 指向自定义目录 | 软链建在该目录，且该根 `skills/` 下逐技能就位 |
| A6 | `bash -n install.sh` | 语法通过 |
| A7 | 临时 HOME 变量注入后 `CCG_INSTALL_LIB_ONLY=1` source | 只取函数定义，不触发主流程 |
| A8 | 写入 MCP patch 后 YAML 可解析且两条 server 完整 | `gitlab-anyverse` 为 streamable-http、`playwright` 为 stdio |

## 5. 风险与回退

- 安装脚本新增分支若误判 DSH 已安装，会在无 DSH 的机器上多建 `~/.agents/AGENTS.md`。以 `~/.dsh` 目录为信号可避免；即使误建，也只是共享根多一个指向本仓的软链，删除即可。
- 软链覆盖用户自建 `~/.agents/AGENTS.md` 会把原文件移为 `.bak`；这是 `link_item` 既有语义，与其他入口一致，日志有 warn。
- MCP profile patch 写坏会让该 profile 启动失败。写入前备份，写入后校验 YAML 与条目字段；失败按备份回退。
- review-loop 新增 DSH 分支不改变既有 CC / Codex 分支行为，回退只需撤回本节改动。
