# Codex 全盘迁移计划

状态：用户已确认，执行中。

## 已确认的迁移方向

- 项目与 GitHub 仓库改名为 `coding-agent-config`，本地目录收尾时同名迁移。
- `AGENTS.md` 为项目规则正文，`CLAUDE.md` 仅作兼容引用。
- 所有共享资源统一从 `~/.coding-agent/` 访问；Codex 原生配置和技能发现入口按其规定部署。
- 工作树目录统一为项目内 `.worktrees/`，不再沿用 `.claude/worktrees/`。
- 保留历史记录和凭据、用户配置；不卸载其他软件。

## 一、范围与基线

- 开轮主 checkout：`/Users/wujie/Personal/claude-code-global`；目标目录为同级 `coding-agent-config`。
- 分支：`round61-codex-migration`。
- worktree：主 checkout 下 `.worktrees/round61-codex-migration`。
- 已执行 `git fetch origin`；本地 `master` 与 `origin/master` 均为 `932f9bd`，无分叉。按本地目录、在途分支、其他 worktree 与远端目录/分支五源检查，本轮编号为 61。
- 本机 CLI 实测：`codex-cli 0.163.0`。桌面会话工具包含 `collaboration.spawn_agent`，支持指定独立 context、模型和思考档；不能把 CLI 与桌面会话能力直接视为完全相同。

本轮优先打通 Codex 独立安装和需求、计划、执行、review、提交、总结全过程，并检查其余技能的实际入口。保留必要的 CC 兼容入口；不批量改写 `docs/` 历史，不部署新的定时任务，不自动转换已有 claude.ai 云端任务。

## 二、初步排查结果

| 领域 | 已取得的证据 | 拟处理 |
| --- | --- | --- |
| worktree | `skills/start/references/worktree-create.md` 已指定项目内目录；当前桌面 `create_worktree` 工具没有路径入参；官方文档说明托管 worktree 默认位于 `$CODEX_HOME/worktrees` | 明确区分技能创建的普通 Git worktree 与桌面托管 worktree，默认用原生 Git 在项目内创建；同步 start/finish/rebase 的路径、复用、防嵌套和清理规则 |
| 项目指令 | 本仓只有 `CLAUDE.md`；bootstrap 也只生成此入口；官方 AGENTS 文档说明非默认文件名需要配置 fallback | 为本仓和新建/接入项目提供 Codex 可自动发现的入口，单一内容源，避免复制漂移；兼容已有子目录规则，核对指令长度与截断风险 |
| 技能发现与资源路径 | `install.sh` 把技能部署到 `~/.codex/skills`，大量 skill 正文仍调用 `~/.claude/scripts`、`templates`、`global-repo`；官方当前文档列出用户技能目录 `~/.agents/skills` | 核对当前 CLI 和桌面支持的发现路径，使用中性共享资源根；保证仅有 Codex 目录时可以运行；迁移自有旧软链，保留第三方技能，避免同名重复 |
| review | `skills/review-loop/SKILL.md` 明示 Codex 必降级本端自审；本会话实际有子 agent 工具；`agents/*.md` 是 CC 格式 | 建立 Codex 原生独立 context review 路径，按可用工具传递编队规格与只读要求，保留收敛和两轮上限，真正能力缺失时才降级并留证 |
| hooks | `codex.config.base.toml` 使用 CC 风格 `PostToolUse` 与 `Edit\|MultiEdit\|Write`，注释仍为“待 issue #8 实测校正”；脚本只读 `.tool_input.file_path` | 核对 Codex 当前配置、事件和 payload；支持则正确注册并验证，不支持则移除假生效承诺，并在 commit 验证流程中显式保证格式化与 lint |
| 安装与更新 | 当前双轨安装只检查固定 home，注释断言 Codex 无 agent 概念；`scripts/auto-update.sh` 默认 `AGENT_HOME=$HOME/.claude` | 检查纯 Codex 安装、资源软链、配置合并、重复安装、自更新路径和用户自定义配置保护；保留 worktree 内禁止 install 的防线 |
| 其他技能与模板 | bootstrap/sync/backlog/triage/finish/quick 等都有 CC 路径；start 要求进入计划模式；部分 playbook 依赖 CC 工具和定时入口 | 全量分类当前生效文件中的路径、命令、模型名、工具名、平台专属能力；共享流程改为端适配，CC 专属功能标明作用域，Codex 没有的能力给出经过验证的替代或明确边界 |
| 文档与安全边界 | README 和 CLAUDE 包含已不适用的兼容结论；两条 routine 对规则、reviewer、安装和自动合入有安全约束 | 更新当前说明、全局规范和 DEVTREE；只做平台适配，不放宽 routine 的授权、写权限、禁止自改边界 |

以上是开轮取证，不把尚未验证的 hook schema、配置字段或模型映射写成已实现结论。

## 三、实施顺序

1. 完成审计矩阵：逐文件记录问题、证据、优先级、修复位置、验证方式以及平台专属边界。读取涉及的领域 playbook、skill-creator 与 review rationale；核对原生 Codex 配置及工具能力。
2. 先写安装、配置和路径解析的失败用例，再修改实现。用临时 HOME/配置目录及临时 Git 仓隔离副作用。
3. 适配指令和技能入口、公共资源定位、项目内 worktree 创建与收尾。普通 worktree 不自动注册为桌面托管 worktree，避免路径与生命周期再次被桌面接管；每次命令显式指定工作目录。
4. 适配 Codex review 编队及 hook/格式化行为。模型与思考档必须有可维护的单一真源；具体模型先核对可用能力与当前规则，不把 CC 模型名传给 Codex。不降低 review 角度、独立 context、置信过滤、运行验证或两轮上限要求。
5. 扫清其他当前生效 skill、playbook、模板、脚本与配置中的平台假设；对确属 CC 专属的行为保留明确分支，不做机械全文替换。
6. 跑受影响测试和端到端沙盘，委派独立 context review 后自主提交开发单元。完成 `SUMMARY.md`（背景、实现方案、局限、后续 TODO），更新 DEVTREE 和 README。
7. 按 finish 既有规则进入最终收尾。合入后从主 checkout 安装，不能从本轮 worktree 重指全局软链；全局落地前展示具体变更。未获相应授权的删除、push、云端任务迁移不执行。

关键能力假设若实测失效且涉及不同代价的交付路线，按宪法停下，列证据、选项和建议后等待确认。

## 四、关键验证用例

| 输入/条件 | 应有结果 |
| --- | --- |
| 临时 HOME 只有 Codex，无 `.claude` | 技能与资源完整可发现，可运行公共 helper，不依赖 CC 安装 |
| HOME 同时有 CC 和 Codex，含第三方技能与用户配置 | 两端均能运行；重复安装幂等，第三方内容保留，无自有同名重复技能 |
| 有自定义 `CODEX_HOME` | 全局资源与配置按已定义的路径语义定位；不误写默认目录 |
| 普通项目运行 `/start` | 创建项目内 `.worktrees/round<N>-*`，分支和中文 docs 目录符合规则 |
| 已在 linked worktree、分支轮次已占用、路径含空格 | 防嵌套有效；轮次重算；路径引用正确；不污染主树 |
| 原项目只有 CLAUDE.md，或已有 AGENTS.md/子目录规则 | Codex 自动加载正确规则，已有内容不丢失、不产生双份真源 |
| Codex 有子 agent 能力 | 实际委派独立 context reviewer，正确传递范围、模型和思考档，不能直接按平台名降级 |
| 委派真实失败或工具确实缺失 | 走有证据的降级路径，明确损失属性；策略限制不伪装成能力缺失 |
| 合法与非法 hook 配置、实际编辑 payload | 下游解析和触发实测成立；配置被解析不等于 hook 已触发 |
| worktree 中调用安装 | 拒绝且全局软链目标不变 |
| 更新/调度沙盘 | 固定网络、时钟、HOME、外部命令返回；不读真实凭据，不注册真实定时器 |

纯指令迁移以行为演练和独立 review 验证；避免只断言特征字符串的伪测试。测试中的网络、时钟、HOME、配置及 CLI 都显式隔离。

## 五、已核对的外部材料与局限

- [官方 worktree 文档](https://learn.chatgpt.com/docs/environments/git-worktrees)：默认根为 `$CODEX_HOME/worktrees`，可通过 Settings > Worktrees > Worktree root 修改。该设置不等于技能可以自动按当前项目动态选根，因此本轮采用明确的原生 Git 路径。
- [官方技能发现文档](https://learn.chatgpt.com/docs/build-skills)：当前列出 `~/.agents/skills` 与仓库 `.agents/skills`，支持软链。已有 `~/.codex/skills` 在本会话确实可见，迁移需核对兼容路径而非直接删除旧目录。
- [官方 AGENTS 文档](https://learn.chatgpt.com/docs/agent-configuration/agents-md)：支持 `project_doc_fallback_filenames`；规则加载存在长度限制，需纳入验证。
- `codex --version` 与 `codex --help` 已实测。对临时配置尝试 `codex --strict-config features list`，返回 `--strict-config is not supported for codex features`；该调用没有验证 hook 配置。实施时需选用真正解析并校验配置的入口和事件触发证据。
