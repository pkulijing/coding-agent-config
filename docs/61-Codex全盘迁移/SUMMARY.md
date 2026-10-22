# Codex 全盘迁移

## 开发项背景

项目虽有双端安装入口，实际技能仍依赖 Claude Code 路径和工具：Codex review 被无条件降级，项目规则只有 CLAUDE.md，hooks 没有按原生 schema 注册。用户决定转为 Codex 主用，并将项目改名为 coding-agent-config、资源迁到中性路径、工作树迁到项目内 .worktrees。

## 实现方案

- 项目规则正文迁到 AGENTS.md，CLAUDE.md 只保留兼容引用。bootstrap/sync 覆盖新项目及既有根/子目录规则迁移，保留导入内容和冲突确认。
- 共享资源统一部署到 ~/.coding-agent，Codex 原生指令配置支持 CODEX_HOME，技能发现使用 ~/.agents/skills。自有旧入口迁移，第三方内容保留；用户配置迁移遵循 user-wins。
- start/finish/rebase 使用普通 Git 工作树与显式工作目录，不再以桌面托管创建替代 .worktrees 路径。迁移通过 git worktree move 完成，保留未提交内容。
- Codex review 使用独立 context，模型和 medium 思考档统一维护于 agents/codex-review.toml；CC 定义保留兼容。实际能力失败才逐档降级，不按平台名猜测。
- Codex hooks 改为原生三层配置，编辑事件解析支持多文件 patch、重命名目的路径和会话 cwd；只解析路径，不执行 patch 字符串。提交前 lint 门禁继续保留。
- 安装/自动更新/调度器改用 coding-agent-config 名称及中性路径，保留安装只能在主 checkout 运行、防止调度器卸载自身的防线。指令预算优先计算 AGENTS.md，避免兼容包装重复计入。
- 本机主目录已迁到 `/Users/wujie/Personal/coding-agent-config`，安装从主 checkout 完成，自动同步任务已注册为 `com.coding-agent-config.auto-update`；共享资源和技能入口经实际解析均指向新目录。旧第 37 轮的未跟踪开发记录完整保留，旧源码路径软链零残留。
- GitHub 仓库已改为 [pkulijing/coding-agent-config](https://github.com/pkulijing/coding-agent-config)，origin 同步更新；历史开发记录不批量重命名。

验证产物：本目录的安装、调度器、hook、预算和工作树目录迁移沙盘共 30 项通过；原预算 41 项与调度器 14 项回归通过，platform_issue 自检和引用检查通过。所有调度器测试使用临时 HOME 和命令桩，不注册真实服务。CLI 0.163.0 原生 hooks/list 已验证正确 schema 能列出 hook、旧 schema 静默返回空列表；信任状态单独核对。

## 局限性

- 首次安装或修改 hook 后须通过 Codex /hooks 审阅信任；安装不代替用户信任，不将“已注册”描述为“已触发”。
- Codex 通用 reviewer 的只读要求由任务书约束，不能宣称具备 CC disallowedTools 的结构性限制；模型和思考档显式传入。
- 既有 claude.ai 云端任务不自动转换为 Codex 自动化；其历史能力说明保留明确的平台作用域。
- 已打开的聊天可能保留原项目目录和技能快照，仓库目录改名后需从新路径重新打开项目/聊天。
- 不批量修改其他业务仓库的规则文件；它们可通过 sync 的迁移流程接入。

## 后续 TODO

- 在新目录打开项目，并在 /hooks 中完成信任后验证实际编辑触发。
- 如仍需云端定期开发，再单独设计 Codex 自动化的授权与调度，不沿用旧平台参数。

## 可沉淀项

本轮已将中性共享路径、Codex review、原生 hook schema 与工作树目录规则沉淀为当前技能和配置；暂无需跨仓另提的事项。
