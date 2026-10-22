# Codex 全盘迁移

## 用户需求

> /start 这个项目之前是用 Claude Code 做的，我现在需要全盘迁到 Codex 。系统排查一下有哪些 Codex 不兼容的地方并做适配。
>
> 我当前开发中发现有一点，就是我的 start 技能的行为变了：原来我都把 worktree 放到当前项目的 .claude/worktrees 目录下，但自从改用 Codex 之后，它都放到了全局 home 下面的 Codex 隐藏目录里，其实挺不方便的。

## 目标

让 Codex 能独立使用本仓库提供的全局配置和开发工作流，无需安装 Claude Code 或依赖 `~/.claude/`。系统检查指令发现、技能、review、hooks、安装更新、模板和自动化中的平台耦合，并对适用能力做适配。

`/start` 默认在每个项目的 `.worktrees/round<N>-<英文短描述>` 下创建工作树，保留轮次命名习惯。

用户后续确认：项目与 GitHub 仓库改名为 `coding-agent-config`；共享资源统一使用 `~/.coding-agent/`；`AGENTS.md` 为正文，`CLAUDE.md` 只保留兼容入口。

## 约束

- 先形成计划并经用户确认，再修改实现。
- 以 Codex 为完整可用的目标端，兼容仍有价值的 Claude Code 部署；不擅自卸载或删除旧配置。
- 对平台能力实际核对，不把 Claude Code 的参数、事件、配置或工具名直接套给 Codex。
- 迁移实现与验证在独立 worktree 内进行；全局安装只能从主 checkout 执行。
- 历史开发记录保留原貌；修改当前生效的规则和使用说明。
