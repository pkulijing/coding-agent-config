# 全局沟通规范

> 读者：使用和维护共享配置的开发者 · 如何选择对话语言并核验沟通效果
> 来源：[Improve Codex communication: friendly personality and global collaboration guidelines](https://github.com/pkulijing/coding-agent-config/issues/196) 和用户在本轮对话批准的修订方案

## 目标

用用户正在使用的语言交流，语言不明确时使用英语。让架构讨论给出清楚的判断，让明确授权的开发任务落实到实现和验证。

## 关键决策

- 会话语言和项目文档语言分别规定。用户可以明确指定语言，项目文档默认简体中文。
- 将 issue 的英文协作准则逐字放入共享的全局入口，各项目和技能即可继承。工程、测试、审查和授权沿用既有规则。
- Codex 已将 `personality` 列为兼容配置，`friendly` 已失去切换风格的作用。按批准方案，仅修改全局说明。[官方配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)

## 实施提纲

调整 `GLOBAL_AGENTS.md` 的语言段，在其后加入原文。使用既有全局软链接部署，按开发起始版本审查，并在交付时给出对照结果。

## 验收

- 核对英文、中文、语言不明确和明确指定回复语言的规则，以及文档语言默认值。逐字比对 issue 原文与部署入口。
- 固定模型、推理档、提示词和初始项目，分别用旧版和新版说明运行一次架构讨论和一次已授权修复。比较回答是否清楚、术语是否自然、判断是否有理由、行动是否符合意图。检查架构讨论期间的文件状态以及修复后的实际测试结果。
