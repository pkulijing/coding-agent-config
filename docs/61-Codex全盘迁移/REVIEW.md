# 独立 review 记录

## 方式与范围

两轮重档审查均覆盖五个角度：契约与装配、缺陷定向扫描、项目规范、Git 历史上下文、状态机及资源生命周期。orchestrator 和各 reviewer 使用独立 context，普通角色为 gpt-6.1-sol / medium，深审为 gpt-6-astra / medium。全部操作锚定本轮工作树，审查包含新文件；只读由任务书约束，不宣称有工具级写入禁令。

## 收敛结果

第二轮五个角度均 clean，无置信分不低于 80 的 correctness finding 遗留。修复范围通过运行验证，未触及两轮上限后的留痕放行或自审降级。

运行验证：新增 30 项沙盘、原预算 41 项、原调度器 14 项回归通过；原调度器测试由 verify_legacy_scheduler.py 复用，更新模块 label、区分旧/新任务查询，并以进程桩替代宿主 ps，不修改历史测试。platform_issue 自检、引用检查和 Shell 语法检查通过；16 个技能均通过官方 quick_validate。

## 原生能力核对

CLI 0.163.0 在临时 HOME/CODEX_HOME 中启动 app-server --strict-config，经 initialize 与 hooks/list 返回一个 PostToolUse hook，matcher 为 ^apply_patch$，命令引用 ~/.coding-agent/hooks/fix-after-edit.sh，enabled=true，trustStatus=untrusted，无警告和错误。没有读取真实凭据、没有发起模型调用、没有代替用户信任 hook。

官方依据：[Hooks](https://learn.chatgpt.com/docs/hooks)、[技能发现](https://learn.chatgpt.com/docs/build-skills)、[AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)、[工作树](https://learn.chatgpt.com/docs/environments/git-worktrees)。

## 技能行为演练

独立新 context 在临时 HOME/Git 仓中执行 start，到计划确认处停止。无 origin 时正确降级，实际创建项目内普通 Git 工作树，未写实现；据演练明确空项目从 0 编号、新建本地忽略文件自身也忽略，避免主树出现未跟踪的忽略文件。

## 本机部署核验

主目录与两个 linked worktree 的 Git 元数据已迁移并验证；资源及两端技能软链均解析到新目录，不存在指向旧源码路径的残留链接。Codex 指令预算为 65536，主工作树干净。新 launchd label 已通过安装器加载查询和 plist 检查；未代替用户信任 hook。
