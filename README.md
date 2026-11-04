# coding-agent-config

以 Codex 为主要运行端的 Coding Agent 配置仓库，集中维护开发规范、技能、独立 review、脚本、hooks 和跨项目模板。共享资源统一从 `~/.coding-agent/` 访问，Codex 可在没有 Claude Code、没有 `~/.claude/` 的机器上独立使用。

项目规则正文为 [`AGENTS.md`](AGENTS.md)，`CLAUDE.md` 仅通过 `@AGENTS.md` 提供兼容入口。全局规则见 [`GLOBAL_AGENTS.md`](GLOBAL_AGENTS.md)，开发项以 GitHub/GitLab issue 为单一真源。

## 部署与路径

| 内容 | 路径 | 行为 |
| --- | --- | --- |
| 共享技能、脚本、模板、领域规则、hooks、review 定义 | `~/.coding-agent/{skills,scripts,templates,playbooks,hooks,agents}` | 链接到本仓同名目录，只有一份内容 |
| 稳定仓库入口 | `~/.coding-agent/global-repo` | 访问模板 Git 历史和安装脚本 |
| Codex 全局指令与配置 | `${CODEX_HOME:-~/.codex}/AGENTS.md`、`config.toml` | 指令软链；配置保留用户内容、合并托管 hook 块 |
| Codex 用户技能发现 | `~/.agents/skills/` | 逐技能软链，保留第三方技能；迁移本仓旧发现入口以免重复 |
| 用户真实配置 | `~/.coding-agent/config.env` | 旧配置迁移保留原件，已设值不覆盖 |
| 开发工作树 | `<项目>/.worktrees/round<N>-<英文短描述>` | `/start` 用原生 Git 创建，按轮次隔离 |
| 自动同步状态与日志 | `~/.coding-agent/`、`logs/auto-update.log` | macOS launchd / Linux systemd，任务名使用 coding-agent-config |

Codex 原生配置和发现目录遵循产品要求；共享技能中的资源路径不依赖某个 Agent 的目录。已有 CC 安装仍可注册兼容指令、技能和配置，但不是 Codex 运行前提。

## 安装

安装 jq 后，在主 checkout 运行 `bash install.sh`。安装脚本拒绝在 linked worktree 内执行，以免全局链接指向随后被删除的工作树。重复执行幂等，用户配置保留；自动更新会拉取 Git 并重新安装。

Codex hooks 使用原生嵌套配置与 `apply_patch` 事件。首次安装或修改命令后，需要在 Codex 的 `/hooks` 中审阅信任；安装完成不等于事件已经获准运行。格式化 hook 是 best-effort，提交前 lint 仍为门禁。

默认工作树使用项目内 `.worktrees/`，不调用桌面托管 worktree 创建工具。桌面托管工作树有自己的位置和归档机制，只有用户显式选择托管时才使用；它与本仓 `/start` 的普通 Git 工作树分开管理。

## 兼容与迁移

- `/bootstrap` 创建 `AGENTS.md` 正文和 `CLAUDE.md` 兼容引用；`/sync-project-config` 检查已有根/子目录规则，迁移时保留内容和导入关系。
- Codex review 使用 `agents/codex-review.toml` 的模型/思考档和原生子 agent 工具，独立 context、范围和只读约束显式传入。CC 命名 agent 仍使用 `agents/*.md`。
- 旧用户配置和可识别的自有入口按需迁移；不删除第三方技能或其他 Agent 自身的数据。
- 历史开发记录保留原名和原始实验。claude.ai 云端任务属于旧平台运行范围，仓库改名不会自动将它们转换为 Codex 自动化。

## GLOBAL_AGENTS.md 内容概览

`GLOBAL_AGENTS.md` 定义了所有项目通用的开发规范：

| 模块                      | 内容                                                                                                                                                                                                                                                 |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **核心开发模式**          | 需求 → 计划 → 执行 → 总结的四步协作流程，每个开发项在 `docs/` 下留档（PROMPT.md / PLAN.md / SUMMARY.md）；每轮默认在独立 git worktree 内进行，支持多轮并行                                                                                           |
| **git 规则**              | 中文 semantic commit message，AI 提交须带 Co-authored-by（按执行 Agent 选身份：CC → `Claude` / Codex → `OpenAI Codex`），`.gitignore` 按目录拆分                                                                                                     |
| **环境变量管理**          | `.env.local`（真实值，gitignore）+ `.env.example`（占位符，提交），禁止泄露密钥                                                                                                                                                                      |
| **领域规则文档**          | 语言 / 栈 / 流程的具体细则下沉到 `playbooks/<topic>.md`（两端统一为 `~/.coding-agent/playbooks/`）；本宪法只保留"指针 + 触发条件"，**这些文件默认不在上下文里**，Agent 命中条件时必须在动手前主动 Read                                    |
| **Python 开发规则**       | 指针到 [`playbooks/python.md`](playbooks/python.md)：uv 管依赖 / ruff / pypi index（清华 + aliyun pytorch-wheels）/ src 布局 + uv_build（含 hatchling、多包 workspace 两个 escape hatch）/ Python 风格细则 / 测试约定                                        |
| **Python 打包发布规则**   | 指针到 [`playbooks/python-packaging.md`](playbooks/python-packaging.md)：含前端产物的成员 wheel 化（hatchling + `artifacts` glob）/ 自托管 GitLab Registry 两坑（`UV_SYSTEM_CERTS` + `--check-url` 不兼容）/「同版本号不覆盖」的两个形态（`pip install --target` 与 `uv tool install`）/ 应用内更新自检骨架 / 装进隔离目录与正式版并存                       |
| **前端开发规则**          | 指针到 [`playbooks/frontend.md`](playbooks/frontend.md)：npm 走 npmmirror / Biome（前端的 ruff）/ React 19 + Vite 6 + TS strict / tailwind v4 CSS-first / shadcn-ui / 落 `frontend/` 子目录，与后端正交                                                      |
| **ROS 2 开发规则**        | 指针到 [`playbooks/ros2.md`](playbooks/ros2.md)：colcon 工作空间（包落 `src/`）/ ament_cmake + ament_python / package.xml format 3 / CMakeLists ament-first（依赖消费三步法 + 导出 + install 路径）/ 纯逻辑 / ROS 薄壳分层 / 新增包检查清单                  |
| **lark-cli 文档创作规则** | 指针到 [`playbooks/lark.md`](playbooks/lark.md)：lark-cli 创作飞书云文档默认加署名行（`⚡ Crafted with lark-cli · <YYYY-MM-DD>`）+ docx 实操技巧（署名落位 / 媒体置顶 / 内容文件相对路径）                                                                   |
| **飞书 bot 后端规则**     | 指针到 [`playbooks/feishu-bot.md`](playbooks/feishu-bot.md)：lark-oapi 长连接 at-least-once 送达 → 按 `message_id` / `event_id` 幂等去重（线程安全 + 有界，附最小骨架）+ 卡片回调 `card.action.trigger` 需在开发者后台配「接收回调」订阅，否则点击无任何回调 |
| **LLM 应用开发规则**      | 指针到 [`playbooks/llm-app.md`](playbooks/llm-app.md)：接 LLM 前先分清「多步 Agent」（执行结果会回传给模型，此时只返回第一个 tool_call 是正确行为；回传的具体形态随 provider 而异）与「一次性任务拆分」（无第二轮，必须换成单 tool + `steps` 数组），错配会**静默漏步**且只在「有依赖的请求」上翻车 + 实测符合率对照（错配 5% / 75%，改结构后 95% / 100%；调参与只改 prompt 措辞都救不回来）+ LLM 组件单测必须统计性、不能用 fake 替模型作答                                                                                       |
| **Shell 脚本开发规则**    | 指针到 [`playbooks/shell.md`](playbooks/shell.md)：「注释在 shell 眼里不是注释」一族的固定坑（双引号串内中文注释禁字面 `"`、`$var` 紧贴 CJK 一律 `${var}`、**未加引号 heredoc 里的注释同样会被命令替换执行**）+ 只在远端 / CI 跑的脚本必须配本地沙盘测试（含**生成物怎么写断言、桩必须在 stdout 维度同构**）+ 非交互式执行（ssh / 定时器 / CI）不继承 profile、PATH 里没有 `~/.local/bin` + **`timeout` 不带 `-k` 兜不住、带了 `-k` 也治不了 shebang 垫片** + **`pkill -f` / `pgrep -f` 会连发起它的那层 shell 一起杀（ssh 下表现为退出码 255 + 后续步骤一条都不执行），模式里插方括号破自匹配** + 给用户手动执行的长命令一律写成脚本                                                                                                  |
| **云端 Routine 环境规则** | 指针到 [`playbooks/cloud-routine.md`](playbooks/cloud-routine.md)：claude.ai Routines 云端 sandbox 实测能力矩阵（gh 未装 / REST 403 / 仓库 CLAUDE.md 才进系统提示 / 无输出回路）+ 指令 / 工具链 / 平台能力三层组合推荐                                       |
| **定时无头 Agent 规则**   | 指针到 [`playbooks/scheduled-agent.md`](playbooks/scheduled-agent.md)：**本机**定时唤起无头 agent（launchd / systemd timer + `claude -p`）的四层架构（OS 定时器 / wrapper / 无头 agent / 确定性脚本）+ macOS·Linux 差异速查 + 实战坑清单（宿主唯一权威副本 / PATH 显式 export / 最小 allowedTools / 通知回路闭环 / **`Type=oneshot` 默认永不超时 × timer 见 active 即静默略过 = 永久停摆**） |
| **开发项管理**            | issue 为**单一真源**（GitHub / GitLab 自动双轨），三轴 label（`type:*` / `area:*` / `priority:*`），三件套 skill：`/backlog` `/start` `/finish`；无本地索引，open 项速览走按 priority 过滤的 saved query                                             |
| **跨项目共享配置**        | `templates/_common/` + stack 模板（如 `python-uv`）由 `/bootstrap`（新项目）和 `/sync-project-config`（老项目 adopt / 拉新）统一管理                                                                                                                 |

## Skills

基线 `settings.base.json` 中预置了 `permissions.allow: ["Skill(*)"]`，让所有 slash command 默认放行，避免反复弹权限确认。

本仓库提供以下 skill。`/backlog` `/start` `/finish` 三件套配合 `/commit` 形成完整的「issue 驱动」开发闭环；小到「改个函数、说清楚即可」的改动走轻量流 `/quick`（不落 docs、不开 worktree、不进计划模式，直接改 → 自动 commit）；需求本身还模糊、要先讨论出方案的，走 `/design`（落 `docs/design/<主题>/`，在主题独立 worktree 中维护讨论记录与方案，持续归档为同主题一个提交，不写业务代码、不开轮）；其余按需调用。执行阶段 Agent 自主判断开发单元完成即 `/commit` 收口，**每次 commit 前自动经 `/review-loop`**（委派独立 context 的 orchestrator 子 agent 并行扇出多个独立 reviewer 角度，置信过滤 + 探针验证；发现高置信正确性问题就修、跑测试+happy-path 验证、复审，迭代到「运行验证通过 + 无高置信 correctness 问题」才放行；2 轮不收敛自动留痕放行）——人类 review 前移到 `/finish`，面对的是每个 commit 都已过独立 review 的干净分支。**编队规格的单一真源是 `/review-loop` skill 与 `agents/*.md`，此处不复述。**

| Skill                  | 用途                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/backlog`             | 把一条想法走 issue templates 创建成 issue（GitHub / GitLab 自动判定，含三轴 label）—— issue 即单一真源，不写任何本地索引                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `/start`               | 开新一轮开发：**先与远端对齐**（`git fetch` + 查目标 issue 是否已被做掉：issue 自身 `state` / 已合入的关闭 commit / 远端在途分支三个信号，命中就停下报告让人拍板），再建独立 git worktree（`.worktrees/round<N>-<英文短描述>`，**整串纯 ASCII、短描述 `[a-z0-9-]` 且 ≤ 20 字符**——GitHub 网页端导航不进非 ASCII 分支名的文件树）+ 同名分支、建 `docs/<编号>-<描述>/`、撰写 PROMPT.md，进入计划模式撰写 PLAN.md 等用户确认后再写代码。轮次编号取**五源并集**（本树 docs / 本地在途分支 / 其它 worktree / 远端已合入 docs / 远端在途分支），避免多设备并行撞号；远端对齐的三条失败路径（无 origin / fetch 失败 / issue 拉不到）一律只提示不阻断。支持 `#<issue 号>` / GitHub or GitLab issue URL（推荐），也支持自由描述；`--no-worktree` 跳过 worktree 在当前分支直接干                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `/finish`              | 收尾本轮：撰写 SUMMARY.md → 反思跨项目可沉淀流程（任意项目都跑，逐条确认后可直接向 coding-agent-config 跨仓库提 issue） → 关联并关闭 issue（如有 `Closes #N`，GitHub / GitLab 均原生支持；「刻意不做」项归档为带 `wontfix` 的 closed issue） → `/devtree` → 必要时同步 README → `/commit` → worktree 轮自动收尾（rebase → FF 合并主分支 → 二次确认后清理 worktree/分支/tag，不自动 push）                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `/quick`               | 轻量开发流（三档里最轻）：不落 docs / 不开 worktree / 不进计划模式，直接改代码 → 自动 `/commit` 收尾。默认当前分支直接改，`--branch` 切轻量分支 `quick/<ascii 短描述>`，`#<issue>` 会拉 issue 详情指导改动（详情只进上下文、不落文档）+ 收尾带 `Closes #N`。适合「小函数改一下、说清楚即可」的小改；要文档追踪 / 计划讨论走 `/start`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `/design`              | 讨论式方案设计：需求本身还模糊时，在多轮对话里逐步收敛出框架级方案。落 `docs/design/<主题>/`（不编号）：`DISCUSSION.md` 记背景输入 / Agent 分析判断 / 用户决策与否决项（即时追加），`DESIGN.md` 是方案快照（`讨论中` / `已定稿` / `已搁置`）。默认主题独立 worktree、同主题单提交归档，定稿或搁置后合入；不写业务代码、不拆 issue、不进 DEVTREE、不写 SUMMARY；`--resume <主题>` 定位原工作树或分支跨会话续聊。以后落地某部分走 `/start` 并引用该方案 |
| `/routine-dev` | 自动开发目标明确的 issue，无需逐条授权；P0 参与排序，开放讨论拒收。允许文档、skills、templates、scripts、hooks，自主计划、实现、验证，一次一个待人工合入 PR、最多尝试三条。保留四条红线和三项远端写操作，支持 `--dry-run`；详见下文。 |
| `/routine-slim`        | 云端 routine：按**增长阈值**触发（`context_budget.py delta --threshold 15`，比 4 周前涨超 15% 才动手，否则空转退出），把指令面按**三板斧**精简一轮并出 PR。三板斧 = 已有单一真源的重复表述去重（留指针）／成组同向细则上提为一句判断原则／事故 WHY 的过程叙事压成结论一句；**明确不做 ablation 删除**。**只允许「搬走」不允许「蒸发」**——PR 描述强制三列表格（删了什么 / 依据哪条判据 / 现在从哪读得到）+ `check-refs` 零失效引用。安全边界：`GLOBAL_AGENTS.md` 与本仓 `AGENTS.md` **只报告不动手**，永不碰自己 / `/routine-dev` / `agents/` / `.github/` / `install.sh` / `scripts/` / `hooks/` / `templates/` / `docs/`。每周日 01:00 UTC 定时，本机可 `--dry-run` 试跑。详见下文「指令面的定期精简」 |
| `/commit`              | 分析当前变更，自动生成中文 semantic commit message 并提交，末尾按执行 Agent 附加 Co-authored-by（CC → `Claude` / Codex → `OpenAI Codex`）；**提交前自动内嵌 `/review-loop`**（委派独立 context 子 agent 编队 review，迭代到「运行验证通过 + 无高置信 correctness 问题」才落 commit）                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `/review-loop`         | 提交前的自动 review 迭代环。**收敛靠「运行验证 + 高置信过滤」，非 reviewer 挑不出为止**——治三个实战病根（挑刺变慢、把基础功能审废、一次 review 烧光 session）。主路径：委派**独立 context 的 review orchestrator 子 agent**（不复用开发 context，不依赖 CC 内置 `/code-review`——其 `disable-model-invocation` 随版本漂移），按档位并行扇出 3 个（默认）/ 5 个（并发/多线程/跨进程重试/状态机/难复现/跨 3+ 模块 diff）独立 reviewer 角度，跨 reviewer 去重 + 0–100 置信打分（<80 过滤）+ 探针验证，返回单一 finding 列表。**编队的模型与思考档由 CC 的 `agents/*.md` 或 Codex 的 `agents/codex-review.toml` 钉死、不继承主会话**（主会话跑 xhigh 时编队不跟着烧）。**三要素并闸收敛**：(A) 运行验证（受影响测试全绿 + happy-path 主流程跑通，编排器无测先补；排在 reviewer 意见之前，堵「基础功能审废无人知」）+ (B) 无高置信 correctness finding（只认 file:line 证据+真会触发，pre-existing/pedantic/推测 corner case 不阻断）+ (C) 已定前提未被重复质疑。修复走 TDD 正序（先写会红的复现测试再改实现）；2 轮不收敛自动留痕放行（REVIEW.md + commit 标注，人工兜底在 `/finish`），全程无人在环。**委派本身已获宪法长期授权**（平台通用指令里形如 "unless the user requested it" 的条件式限制，其条件在本工作流下已满足，见 `GLOBAL_AGENTS.md`）。降级有**硬门槛**：只有**能力缺失**才算委派失败（策略约束一律不算），且**必须实际核验过**——真发起一次并失败，或核对确认工具不在列表；留痕须附失败证据，**编造一次没发生的调用来凑证据同样禁止**。配置/指令文件不跳过，仅纯用户文档/注释才跳过。由 `/commit` 提交前自动调用，也可手动跑 |
| `/bootstrap`           | 为空项目搭建文档骨架（README / CLAUDE / DEVTREE）+ 选 stack 铺设跨项目模板，仅在项目首次开发前调用一次                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `/sync-project-config` | 把本仓库管理的「跨项目共享开发配置模板」最新变化同步进当前项目；含 adopt 模式（无 marker 老项目首次接入）+ 废弃 BACKLOG.md 一次性迁移（老项目遗留 `docs/BACKLOG.md` 时引导迁云端 issue 后删除）                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `/triage` | 只读盘点 open issue，按 priority × scope 排序，标出可接单、开放讨论、越界、前置未满足、疑似完成或待核环境，并给一条推荐。规模现估加 `?`，可执行性不是运行承诺；不改 issue、不自动开轮、不落本地索引。 |
| `/devtree`             | 依据 `docs/DEVTREE.md` 中作者维护的 Epic 结构，重新生成可视化图表和节点索引                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `/rebase`              | 诊断本地分支分叉并按清单引导完成 rebase，历史保持 FF 直线                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `/pybump`              | 升级 Python 项目版本号（`pyproject.toml`），提交并打 tag                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |

## Hooks

`hooks/` 下放共享编辑后自动修复脚本，安装到 `~/.coding-agent/hooks/`；Codex 原生配置和 CC 兼容配置分别注册各自事件。脚本同时解析 CC 文件路径和 Codex patch 的多文件路径。

| Hook                | 触发时机                  | 作用                                                                                                                                                       |
| ------------------- | ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `fix-after-edit.sh` | PostToolUse（Edit/Write） | 编辑后自动跑项目本地工具链（如 `ruff check --fix`、`prettier --write`），让 AI 改动跟项目 formatter 输出对齐，避免 VS Code 保存时 formatOnSave 触发大 diff |

由本仓库管理的 hook 条目以 `# @coding-agent-config:<hook-name>` 注释作为身份标记；`install.sh` 通过这个标记做集合差分（增 / 删 / 同名替换），不影响用户手动添加的 hook。

## Scripts

`scripts/` 下是被 SKILL.md 显式调用的稳定脚本（非 hook、非 skill），由 `install.sh` 软链到 `~/.coding-agent/scripts/`，SKILL.md 通过绝对路径 `$HOME/.coding-agent/scripts/<name>` 引用。

| Script              | 用途                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `platform_issue.py` | 跨平台 issue / label / repo helper：封装 `gh` ↔ `glab` 双轨调用，按 `git remote get-url origin` 自动 dispatch。被 `/backlog` `/start` `/finish` `/triage` `/bootstrap` `/sync-project-config` 调用；`issue-view` 归一输出含 `state` / `stateReason`（两端只有 `open` / `closed` 两值，判据挂在两端词形一致的 `closed` 上，判不出一律算 `open`；`stateReason` 为 GitHub 独有，区分「做完了」与「有人决定不做」，供 `/start` 开轮远端对齐消费）；`issue-list` 列 open issue（归一 json 数组，schema 与 `issue-view` 一致，供 `/triage` 消费）；`issue-comment` 给 issue 补材料（两端连子命令名都不同：`gh issue comment --body-file` ↔ `glab issue note -m`，长正文走 argv 不经 shell 故无需转义；GitLab 侧取不到 URL 时只 warn 不报错，因为评论已发出）；`issue-create` 支持 `--repo` 跨仓库提 issue（配合 `--platform`，供 `/finish` 把可沉淀项提到 coding-agent-config）——跨仓库创建强制带 ≥1 个 `--label`（零 label 直接拒绝，确需裸提才加 `--allow-no-label`），`label-list` 亦支持 `--repo` 以便创建前校验目标仓库 label。零第三方依赖（仅 stdlib），含 `--self-test`。完整契约（dispatch / color 转换 / exit 2/3/4 降级）见同目录 [`platform_issue.md`](scripts/platform_issue.md)，多个 skill 引用此单一真源 |
| `context_budget.py` | 指令面预算量化，零第三方依赖（仅 stdlib）。`measure` 出每文件字符 / token / 常驻-懒加载分类；`delta --since <ref>` 与历史版本比增长率（**基线由 git 历史算出，不落状态文件、不打 tag**），`--threshold` 供 routine 当闸；`check-refs` 校验跨文件引用可达性，是「只允许搬走不允许蒸发」的机械兑现。被 `/routine-slim` 调用。**token 估算系数由 CC `/context` 实测标定**（中文按英文经验值 4 字符/token 估会低估约 3 倍），换模型或大改文风后需重新标定；单测 41 项在 [`docs/52-指令面精简与定期化/test_context_budget.py`](docs/52-指令面精简与定期化/test_context_budget.py) |
| `user-config.sh`    | 用户可配置项的可 source 库：`ccg_seed_user_config`（user-wins seed，缺省才填/补缺追加）、`ccg_read_config`（安全解析，不 blind `source`）、`ccg_apply_git_default_branch`。被 `install.sh` source，未来 hook/skill 可复用。详见 [docs/27-用户可配置项机制/DESIGN.md](docs/27-用户可配置项机制/DESIGN.md)                                                                                                                                                                                                                                                                                                                                            |
| `auto-update.sh`    | 多设备自动同步主脚本：跑 `git fetch` → ff-only `git pull` → `bash install.sh`，由 OS 调度器（launchd/systemd）触发，30min 节流。详见下文「多设备自动同步」                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |

### 私有化部署 GitLab 的 glab 证书问题

如果 `glab auth login` 报错形如 `x509: certificate signed by unknown authority` 或 `tls: failed to verify`，多半是私有化部署的 GitLab 用了自签或内部 CA 签发的证书。**永久修复**（不要用 `skip_tls_verify` 类降级方案）：把服务器证书加到系统信任库。

1. 抓证书：

   ```bash
   openssl s_client -showcerts -connect your-gitlab-host.com:443 </dev/null 2>/dev/null \
     | openssl x509 -outform PEM > gitlab.crt
   ```

2. 加到系统信任库：
   - **macOS**：打开 Keychain Access → 把 `gitlab.crt` 拖进 **System** keychain → 双击该证书 → Trust 段设为 **Always Trust**
   - **Linux (Ubuntu/Debian)**：
     ```bash
     sudo cp gitlab.crt /usr/local/share/ca-certificates/
     sudo update-ca-certificates
     ```

加完后重新 `glab auth login` 即可。

## 跨项目共享模板

`templates/` 下维护「跨项目共享开发配置模板」，由 `install.sh` 软链到 `~/.coding-agent/templates/`，供 `/bootstrap` 与 `/sync-project-config` 在目标项目中铺设 / 同步。

| 模板                   | 适用项目                                                                     | 内容（节选）                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ---------------------- | ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `_common/`             | 所有项目（其他 stack 自动叠加）                                              | 通用 issue templates（GitHub + GitLab 双轨）、`.github/labels.yml` 三轴 label、`.prettierrc` / `.prettierignore`（豁免 DEVTREE.md 免表格对齐）等                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `python-uv/`           | Python 项目（uv + ruff）                                                     | `.gitignore` / `.pre-commit-config.yaml` / `.vscode/` 配置片段（`extensions.json` + `settings.json` 的 `*.json.fragment`，合并进项目根 `.vscode/`：ruff 推荐 + `[python]`/`[markdown]` formatOnSave）/ `pyproject.toml` 四个片段（`[tool.ruff]` + `[tool.uv]` python-preference=only-managed + `[[tool.uv.index]]` 清华源 + `[tool.pytest.ini_options]` src 布局 pythonpath/testpaths） / `tests/` + `configs/` 骨架（与 src/ 平级）/ CI workflow（GitHub Actions `lint.yml` + GitLab CI `.gitlab-ci.yml`，后者为**变体组** `.variant.docker`/`.variant.shell`，bootstrap/sync 按 runner 类型选一个落地；两端均含 **ruff + pytest 两个 job** —— lint 只证明静态无错、证明不了行为没回归，守护测试没有门禁就只是注释。无用例时 pytest 退出码 5 视作跳过，一旦有测试就必须跑） |
| `python-uv-workspace/` | Python **多包单仓**（uv workspace），落工作区根、与单包 `python-uv` **互斥** | 虚拟根（`pyproject.toml` 无 `[project]`、仅 `[tool.uv.workspace] members=["packages/*"]`）+ 共享配置上提到根的 fragments（`[tool.uv]` only-managed / `[[tool.uv.index]]` 清华源 / `[tool.ruff]` 含 `extend-exclude` / `[tool.pytest.ini_options]` `--import-mode=importlib` + 列全各成员 `pythonpath`·`testpaths` / `.vscode/settings.json` `extraPaths`+`defaultInterpreterPath`）/ `packages/` 下两参考成员 `example_core`（库，纯逻辑可独立单测）+ `example_app`（应用，演示 `[tool.uv.sources] workspace=true` 跨成员依赖，各成员 `tests/` 无 `__init__.py`）/ `stack.yml`（`default_path: .`）       |
| `react-vite/`          | 前端项目（React + Vite），落 `frontend/` 子目录、与后端正交                  | `package.json`（React 19 + Vite 6 + TS strict，依赖版本写死）/ `.npmrc`（npmmirror）/ `biome.json`（前端的 ruff）/ `components.json`（shadcn new-york/neutral）/ `vite.config.ts`（`/api`·`/ws` proxy 范式）/ `tsconfig.json` / `index.html` / `src/` 基础件（`main.tsx` + `index.css` tailwind v4 CSS-first + theme-provider/mode-toggle 暗色可切 + shadcn Button + App 占位）/ `.vscode/` 配置片段（`extensions.json` + `settings.json` 的 `*.json.fragment`，合并进**项目根** `.vscode/`：Biome 推荐 + 语言作用域 formatOnSave）/ **自动门禁**：`.pre-commit-config.yaml.fragment`（`repo: local` 跑 biome + tsc，合并进项目根，与后端栈 hooks 取并集）+ GitHub Actions `frontend-lint.yml`（故意不叫 `lint.yml`，避免与后端栈在 `__root__` 撞名）+ `.gitlab-ci.yml.fragment`（往变体组已选中的那份里加一个 `frontend` job）/ `stack.yml`（`default_path: frontend`）                              |
| `ros2/`                | ROS 2 项目（colcon 工作空间，可含多个 ROS 包），落工作空间根                 | 工作区级配置落 `__root__`（`.gitignore` colcon 产物 + `.ws/`/compile_commands 软链 / `ruff.toml` / `.clang-format` Google 100 列 / `.vscode/` 片段：ruff + clangd + cmake + ROS 扩展与语言作用域设置）/ `__subpath__/src/` 下两个参考包：`ros2_cpp_pkg`（ament_cmake，演示 ament-first CMake / 依赖消费导出 / install 路径 / 纯逻辑 + ROS 薄壳分层 + gtest）与 `ros2_py_pkg`（ament_python，纯逻辑 + 节点冒烟测）/ `stack.yml`（`default_path: .`）。Python 与 C++ 合一个 stack（一仓即一工作空间、可含多包，共享根配置）                                                                                 |

**平台双兼容**（round 14 引入，round 15 完成 skill 端双轨适配）：模板内容同时含 GitHub（`.github/...`）与 GitLab（`.gitlab/...` + `.gitlab-ci.yml`）两套等价文件，bootstrap / sync 一并落地——对端文件在另一平台等同于死文件，互不干扰。其中 `.gitlab-ci.yml` 是**变体组**（round 43 引入通用「变体组」机制）：模板存 `.variant.docker`（docker executor runner）/ `.variant.shell`（本地 shell runner，脚本装 uv、复用 `before_script` 用 YAML 锚点而非 `!reference`）两支，bootstrap/sync 初始化时按 runner 类型交互选一个落地为 `.gitlab-ci.yml`、选择记进 marker `stacks[].variants`——因为会被 GitLab 真实执行的配置不能多变体并存让用户手删。**变体组与 YAML fragment 并存**：`.gitlab-ci.yml` 本体由后端栈的变体组提供，前端维（`react-vite`）改以 `.gitlab-ci.yml.fragment` 往**已选中的那份**里加一个 job——前端与 runner 类型正交，要的不是「再来一个变体」；落地顺序因此固定为「变体先落地、fragment 后合并」，且 fragment 内禁用 YAML 锚点（锚点作用域是单个文档，合并后会重名或悬空）。`.pre-commit-config.yaml` 走的是**另一条路径**（别照搬）：后端栈那份是走普通复制落地的**基础文件**，前端维只出一份 `.pre-commit-config.yaml.fragment` 往它里面合；纯前端项目则由该 fragment 直接创建。要点是两维都得往同一个根文件贡献 hooks——少了任何一维，那一维就没有本地闸门。skill 中真正调命令行的步骤（如 labels 同步、issue 创建 / 查看）由 `scripts/platform_issue.py` 按 `git remote get-url origin` 自动 dispatch 到 `gh` / `glab`，SKILL.md 不直接调平台 CLI。`.github/labels.yml` schema 跨平台一致，GitLab 项目下也读同一份（不复制 `.gitlab/labels.yml`）。详见 [docs/11-跨项目共享模板与sync-skill/SCHEMA.md](docs/11-跨项目共享模板与sync-skill/SCHEMA.md) 末尾「关于平台双兼容」一节。

工作流：

- **新项目** → `/bootstrap` 选 stack（**可多选**，如后端 `python-uv` + 前端 `react-vite` 叠加），自动写入相关配置 + 生成 `.agent-template.yml` marker
- **已有老项目** → `/sync-project-config` 进入 adopt 模式补全 marker 并铺模板
- **模板更新后** → 在项目目录跑 `/sync-project-config` 拉新（AI 智能 merge，per-file 用户决策；normal sync 不重跑 stack bootstrap）

**python-uv stack 自动 bootstrap**（round 17 引入，round 25 改用 `uv init --package`）：`/bootstrap` 选 `python-uv` 与 `/sync-project-config` 走 adopt 路径时，除了落配置文件，还会自动跑 `uv init --package`（已有 `pyproject.toml` 时跳过）+ `uv add --dev pytest pytest-cov ruff` + 必要时 `uv tool install pre-commit` + `pre-commit install`。`--package` 让 uv 直接落标准 src 布局（`src/<pkg>/__init__.py` + 含 `[build-system] uv_build` 的 `pyproject.toml`）；模板配套 fragment 把 `[tool.pytest.ini_options] pythonpath=["src"] testpaths=["tests"]` 合并进 pyproject。新项目跑完 `/bootstrap` 立即可 `uv run pytest` / `git commit`，不需要再手敲命令。用户可选「只要配置不要装依赖」跳过整段。详见 [docs/17-python-uv模板自动bootstrap/SUMMARY.md](docs/17-python-uv模板自动bootstrap/SUMMARY.md) 与 [docs/25-python模板与子CLAUDE机制/SUMMARY.md](docs/25-python模板与子CLAUDE机制/SUMMARY.md)。

**python-uv-workspace stack 自动 bootstrap**（round 36 引入）：多包单仓（uv workspace）与单包 `python-uv` **互斥**、二选一。`/bootstrap` 选 `python-uv-workspace` 与 `/sync-project-config` 走 adopt 路径时，**不**跑 `uv init --package`（那会在虚拟根写出 `[project]` + `src/` 破坏 workspace 形态）——虚拟根 `pyproject.toml` 由本 stack 的 workspace fragments（`uv-workspace` / `uv` / `uv-index` / `ruff` / `pytest`）合并而成、成员包随模板 `packages/*` 复制就位，随后 `uv add --dev pytest pytest-cov ruff` 在虚拟根写 `[dependency-groups] dev` 并触发 `uv sync`（把各成员 editable 装入、解析跨成员 `workspace=true` 依赖）。跑完即可 `uv run pytest` 跑全树。布局细则见 [`playbooks/python.md` §2.2](playbooks/python.md)。

**react-vite stack 自动 bootstrap**（round 30 引入）：`/bootstrap` 选 `react-vite` 与 `/sync-project-config` 走 adopt 路径时，整套前端模板复制到 `frontend/` 子目录后，自动在 `frontend/` 跑 `npm install`（`.npmrc` 已固化 npmmirror 源，依赖走国内镜像）。前端 / 后端是正交两维、可同仓叠加（如 `python-uv` 落根 + `react-vite` 落 `frontend/`），marker 各记一条 `stack` + `path`。用户可选「只要文件不装依赖」跳过 `npm install`。详见 [docs/30-前端栈规则与scaffold模板/SUMMARY.md](docs/30-前端栈规则与scaffold模板/SUMMARY.md)。

## 多设备自动同步

每次换设备都手动 `git pull && bash install.sh` 很烦。本仓库把这件事交给 **OS 调度器**（[scripts/auto-update.sh](scripts/auto-update.sh)，30min 节流）：

| 触发方                                                    | 时机              | 输出                                                                            |
| --------------------------------------------------------- | ----------------- | ------------------------------------------------------------------------------- |
| **OS 调度器**（macOS launchd / Linux systemd user timer） | 登录跑 + 每小时跑 | 完整日志 → `$AGENT_HOME/logs/auto-update.log`（默认 `~/.coding-agent/`），stdout 静默 |

> 曾另有一条 `SessionStart` hook 在每次会话启动时也跑一次同步。因为它绝大多数时候被同一个 30min 节流戳挡掉、什么都不做就退出，却仍要付出进程拉起 + `git fetch` 的启动延迟，已移除；同步全部由调度器承担。**未注册调度器的环境**（容器、云端 sandbox——`install.sh` 在无 dbus 容器里 systemd 注册本就会失败）因此没有自动同步，按其惯常做法在会话内显式 `git pull && bash install.sh` 即可。

**`bash install.sh` 末尾自动调 [scheduler/install.sh](scheduler/install.sh)** 注册 OS 调度器（macOS 写 `~/Library/LaunchAgents/com.coding-agent-config.auto-update.plist` + `launchctl load -w`；Linux 写 `~/.config/systemd/user/` + `systemctl --user enable --now`）。失败 warn 不阻塞主 install。

> macOS 侧的注册**不是无条件 unload + load**：plist 内容未变且 job 已加载时直接跳过，正被该 job 承载时只更新 plist、把重注册推迟到下次登录。因为 `launchctl unload` 会杀掉该 job 名下**全部**进程 —— 而 `install.sh` 常常正是由这个 job 拉起的，就地重注册等于自杀。成败也不看 `launchctl load` 的退出码（它失败时照样返 0），改查 `launchctl list`。来龙去脉见 [docs/58-调度器自杀式重注册/SUMMARY.md](docs/58-调度器自杀式重注册/SUMMARY.md)。

**关键行为**：

- dirty working tree / non-fast-forward / 网络错误 → 跳过 + 写日志 + **不更新时间戳**（下次重试）
- `install.sh` 未成功跑完（被强杀或非零退出）→ 留下 `$AGENT_HOME/.auto-update-inflight` 标记，下次运行**告警并补跑**。没有它的话，此时 `git pull` 往往已成功，下次会走「已是最新」直接退出，部署就永久停在半截；标记里的时间戳是**最初**那次失败的时间，好看出「已经坏了多久」
- 只在 master 分支自动 pull
- 第一台设备首次仍要手动 `git clone + bash install.sh`（自举的硬限制）
- 正在跑的旧 Claude session 不会自动应用新配置，需 `/exit` 重开

**逃生舱**：取消调度器注册跑 `bash scheduler/uninstall.sh`。详细设计见 [docs/16-自动同步全局配置/SUMMARY.md](docs/16-自动同步全局配置/SUMMARY.md)。

## issue 的自动开发（云端 routine）

本仓由定时 routine 自主开发**目标明确**的 issue，人在 PR 上决定是否合入。用户确认过去合入的自动开发 MR 不需要手工修改或返工，因此取消逐条授权，扩大常规接单范围。

**目标未收敛的讨论禁止开发；目标明确、实现方案未定可以开发。** `status:discussion` 是明确拒收状态，没有标签时仍要读正文判断；P0 只影响排序，多文件、需要调研或并发验证都不是单独的排除因素。旧 `auto:take` 已停用。

| 环节 | 做法 |
| --- | --- |
| 规则真源 | [`skills/routine-dev/SKILL.md`](skills/routine-dev/SKILL.md)，调度器 prompt 只留指针 |
| 范围 | 文档、skills、templates、scripts、hooks；四条红线覆盖允许列表，其余文件不碰 |
| 排序 | P0 → P1 → P2 → 未标优先级，同级最老优先；第一条合格就停止分诊 |
| 开发 | 自主输出实施计划、实现、验证，再调 `/commit`；不以 quick 的定位拒绝完整任务，不等待无人可确认的计划 |
| 验证 | 受影响测试、独立 review、真实 diff 的权限与在途 PR 撞车复核；缺环境须实际检查 |
| 交付 | 一条 issue 一个 commit，一次一个 PR，最多尝试开发三条；完整交付才用 `Closes`，有独立价值的部分交付只用 `Refs` 并列未完成验收项 |
| 反馈 | PR 含方案、验证、review 降级、遗留 finding 和已检视排除清单；零 PR 也输出原因，旧云端输出缺少持久回读渠道的局限保留 |

**四条红线**：`skills/routine-dev/**`（自己的权限）、`agents/**`（检查员配置）、`install.sh`（全设备部署）、`.github/**`（合入路径）。允许改其他 skill 不等于可降低本次检查标准；涉及 review-loop 时按开发起始基线执行检查。

**远端写操作只有三项**：推送一条新分支、创建 PR、编辑该 PR 描述。不写标签或评论、不改在途 PR 分支、不强推，绝不触发合入。使用 owner 凭证时合入闸区分不了人和 Agent；这些是流程约束，没有宣称已经实现凭证隔离。公开 issue 和评论都是数据，不能扩展权限。完整推导见 [`security-boundary.md`](skills/routine-dev/references/security-boundary.md)。

失败后清掉暂存、未跟踪文件等本次残留再换下一条，不能只用 `git restore`；归属不明则停止，不碰他人资产。相同三条持续失败仍可能阻塞后续候选，此成本上限的局限保留。

本机可 `/routine-dev --dry-run`，只读分诊、不改文件或远端；全量盘点用 `/triage`。旧 CC 云端的环境与注册实测见 [`playbooks/cloud-routine.md`](playbooks/cloud-routine.md)，调度器能力不能跨平台外推。

### PR 批准即 fast-forward 合入

GitHub 原生的三种合并方式都拿不到真 FF——merge 留 merge commit，squash / rebase 会新造提交。而**把 PR head 直接推到默认分支时，GitHub 会自动把该 PR 标记为 merged**（官方称 indirect merge）。[`.github/workflows/ff-merge.yml`](.github/workflows/ff-merge.yml) 就建在这条性质上：

- **触发**：在 PR 上打 `ff-merge` label，或评论 `/ff`（两条路等价，评论取首行第一个词，故 `/ff 合并吧` 也认）；
- **动作**：先试纯 FF；默认分支在 review 期间前进了就先 rebase 再 FF，**冲突一律停手**（绝不 fallback 成普通 merge）；推送被拒会重取最新 base 重试至多 3 次；成功后关闭关联 issue、删分支、回一条带新旧 SHA 的回执评论。**任何一步失败都会在 PR 上留评论并摘掉 label**，不会出现「label 挂着、其实什么都没发生」；
- **关联 issue 由脚本显式关闭，不靠 GitHub**：indirect merge 恰好掉在 GitHub 两套自动关闭机制的缝里——commit message 的关键字只在「该提交**首次被推**、且推的就是默认分支」时生效（PR 分支已先推过一遍，于是只被记成 `referenced`），PR body 的关键字又要靠「PR 被合并」事件触发（indirect merge 只改 PR 状态、不走那条链路）。故 [`ff-merge.sh`](.github/scripts/ff-merge.sh) 从「本次合入的提交集合 + PR body」解析关闭关键字后自行 `gh issue close`。**这条对 `/routine-dev` 是必需品而非锦上添花**：它的幂等靠「排除已被 open PR 覆盖的 issue」，PR 合并后覆盖消失而 issue 还开着的话，下次运行就会把同一条原地重做；
- **安全**：本仓是公开仓、也是云端 agent 的信任根，故硬校验**发起人 == 仓库 owner**；两个事件都用「workflow 文件恒取自默认分支」的那一档（`pull_request_target` / `issue_comment`），PR 内容改不了将要合并它的这段逻辑；rebase 路径会把 PR 内容落进工作区，但该 job **全程不执行工作区里的任何文件**。

于是 `master` 上既没有 merge commit、也不会被改写 SHA，与 `/rebase`、`/finish` 的 worktree 收尾保持同一套 FF 直线历史纪律。

**唯一的硬边界**：**触及 `.github/workflows/` 的 PR 走不了这条路**——Actions 的 `GITHUB_TOKEN` 被 GitHub 服务端硬性禁止推送 workflow 文件，且 `permissions:` 块里没有可声明的对应 scope，提权也绕不过。这类 PR 会收到一条说明评论，请在本地 `git merge --ff-only` 后直推。`/routine-dev` 产出的 PR 天然不会命中（`.github/` 在它的禁止落点清单里）。

## 指令面的定期精简（云端 routine）

本仓所有文档与 skill 的迭代长期是**单向增长**——只加不减。实测指令面（`GLOBAL_AGENTS.md` + `skills/*/SKILL.md` + `playbooks/*.md`）总字符数：2026-04 是 32,495，2026-07 是 162,562，**四个月 4.8 倍，中间没有任何一次净减**。

round 52 对照 Anthropic《[The new rules of context engineering for Claude 5](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models)》（其自述砍掉 Claude Code 系统提示 80%+ 而编码 eval 无可测量损失）逐条核到本仓，得到三条与直觉不同的结论：

1. **痛点不是常驻 token。** round 51 让 playbooks 退出常驻后，剩下的绝大部分是懒加载。真痛点是**单次加载密度**与**只增不减的棘轮**。
2. **最大头是「重复」不是「冗长」。** 同一套 review 判据曾写在 6 个地方；`sync-project-config` 里明写着「与 bootstrap Step 3.3.7 **同一份，改动时两处同步**」，`commit` 里明写着「细节以 `/review-loop` 为**单一真源**」——然后复述了 700 字符。
3. **本仓的文档密度是资产不是负债。** 每条规则背后都挂着一次真实事故的代价。LLM 精简器最容易干的事恰恰是把「为什么」删掉只留「是什么」，**盲目按字数精简会精准删掉最值钱的部分**。

于是 [`/routine-slim`](skills/routine-slim/SKILL.md) 的判据被钉成两张清单，且**先在 round 52 真刀真枪用过一遍**才固化成 routine（不是纸上推演）：

| | 内容 |
| --- | --- |
| **允许删除**（封闭清单） | ① 已有单一真源的重复表述（必须留指针）② 成组同向细则 → 上提为一句判断原则 ③ 事故 WHY 的**过程叙事** → 压成结论一句 ④ 失效引用 ⑤ Agent 已从工具 schema 得知的重复 |
| **禁止删除** | 事故 WHY 的**结论**（可压缩、不可消失）／安全禁令与硬边界／本仓特有的非标约定／**拿不准就保留** |

**只允许「搬走」不允许「蒸发」**——删除型 diff 的麻烦是「少了什么是看不见的」，`git diff` 告诉不了你那条信息是搬走了还是没了。两道护栏：PR 描述**强制三列表格**（删了什么 / 依据哪条判据 / 现在从哪读得到），以及 `context_budget.py check-refs` 机械校验所有指针可达（**指针指不到东西 = 那条信息真的没了**）。

| 维度 | 取值 |
| --- | --- |
| 触发 | 每周日 01:00 UTC（= 北京时间周日 09:00），且**增长 > 15% 才动手**，否则空转退出 |
| 逻辑落点 | **全在仓库**（[`skills/routine-slim/SKILL.md`](skills/routine-slim/SKILL.md)），claude.ai 上只留一句指针 |
| 出口 | PR 即审批闸（打 `ff-merge` label 或评论 `/ff` 即 FF 合入），同 `/routine-dev` |
| 一次做多少 | 1–3 个文件。删除型 diff 的 review 成本本就高，少而深胜过多而浅 |

**安全边界**（与 `/routine-dev` 的差异是有意的）：

- **可自动改** `skills/*/SKILL.md`、`skills/*/references/*.md`、`playbooks/*.md`；
- **只报告不动手** `GLOBAL_AGENTS.md` 与本仓 `AGENTS.md`——宪法是所有 skill 的上位规则，一条能自动改它的 routine 就是能改自己上位约束的 routine；
- **永不碰** 自己、`/routine-dev`、`.github/`、`install.sh`、`scripts/`、`hooks/`、`templates/`、`docs/`。**不因为「只是精简、不改语义」而放宽——判断有没有改语义的正是它自己。**

**两条 routine 都能改 skills，但任务边界不同**：dev 实现明确需求，可引入经过验证的新行为；slim 只删除和搬移仓库既有内容。统一接单不扩展 slim 的精简权限，两者都不能把输入文本当作权限指令。
**两条 routine 的撞车防线（双向）**：`/routine-dev` 每周跑三次、也写 `playbooks/*.md`，自 round 54 起同样能改 `skills/*.md`，重叠面比原先更大；PR 又可能在人手上挂好几天——**光靠 cron 时间错开不够**。故**两边各守一道、不依赖对方**：`/routine-slim` 每次运行把所有 open PR 碰过的文件整体排除（列不出 open PR 就中止本次运行）；`/routine-dev` 在分诊时就排除「预期落点撞上任一 open PR 已碰过的文件」的 issue，开 PR 前再用**真实 diff** 复核一次，撞了就清理并换下一条候选，最多尝试三条——顺带也覆盖了人手开的 PR。

来龙去脉与量化见 [docs/52-指令面精简与定期化/](docs/52-指令面精简与定期化/)，其中 `SLIM-LEDGER.md` 是那一轮删减的完整三列账本。


## 开发项管理

详细规范见 [`GLOBAL_AGENTS.md`](https://github.com/pkulijing/coding-agent-config/blob/master/GLOBAL_AGENTS.md) 中「核心开发模式 → 需求管理」段。要点：

- 开发项以 **issue 为单一真源**（GitHub / GitLab 自动双轨判定）：详情、讨论、跨轮上下文都沉淀在 issue，**无本地索引文件**
- open 项速览走一个按 priority label 过滤 open issues 的 **saved query**（本仓库：[open issues by priority](https://github.com/pkulijing/coding-agent-config/issues?q=is%3Aissue+is%3Aopen+label%3Apriority%3AP0%2Cpriority%3AP1%2Cpriority%3AP2)），消除 BACKLOG.md 与云端 issue 的双写和 drift
- 三轴 label：`type:*`（feat/bug/refactor/perf/test/docs）、`area:*`（项目特异）、`priority:*`（P0/P1/P2）；**刻意决定不做**的项归档为带 `wontfix` 的 closed issue
- **`status:discussion`（三轴之外）**：目标尚未收敛，禁止自动开发；没有标签时仍按正文判断。明确目标的实现方案可以由 Agent 自主选择，P0 不是排除因素。
- 工作流：`/backlog` 起新想法 → `/start <issue#>` 开新轮 → 执行中 Agent 自主 `/commit` 收口（每次 commit 前自动经 `/review-loop`：委派独立 context 子 agent 编队 review，默认 3 reviewer、复杂 diff 升 5 reviewer，深审模型按当前端配置，迭代到「运行验证通过 + 无高置信 correctness 问题」）→ `/finish` 收尾时 PR/commit 写 `Closes #N` 自动关 issue（GitHub / GitLab 均原生支持）
