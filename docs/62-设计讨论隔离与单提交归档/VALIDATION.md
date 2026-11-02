# 验证记录

## 验证边界

本轮修改的是自然语言技能和流程规则，没有新增生产执行器。`test-design-git.sh` 验证所依赖的原生 Git 操作与数据保全条件，不证明任意 Coding Agent 会自动正确执行全部规则。授权识别、主题歧义和引用分类等行为需要独立 review 与场景推演；未将关键词匹配作为这些行为的自动测试。

测试仅操作临时仓库和本地 bare 远端，固定身份、提交时钟、locale，并隔离 HOME、用户 Git 配置与 hooks。不会连接 GitHub，也不会重写本仓库既有提交。

## 已运行

2026-11-02，执行 `bash docs/62-设计讨论隔离与单提交归档/test-design-git.sh`，9 组场景全部通过：

1. 多次 amend 后单主题提交数仍为 1；主树 staged、unstaged、untracked 内容和 index 不变。
2. 两个主题交替互不污染；移除主题工作树后可从原分支恢复同一归档提交。
3. 完整 index 清单能检出夹带路径，主题归档保持不变。
4. 已发布提交 amend 后普通 push 被拒；过期的显式 SHA lease 被拒，远端并发更新仍在。
5. single-branch clone 的默认 fetch 不会取回主题；显式列全远端 heads 并取回候选后，可恢复原文档和提交。
6. 在临时分支整理交错的两个主题提交，最终 tree 不变；其他开发提交的完整 message、patch-id 保留，原分支与 backup 引用不变。
7. 主线前进后 rebase + FF，只引入一个主题提交；确认文件一致与提交可达后可安全清理主题工作树及分支。
8. 混合提交的完整路径清单包含其他代码，不能当作纯主题提交。
9. 同主题文件 rebase 冲突后可 abort，旧 tip、原文档字节、干净状态和工作树保留。

另已通过 `bash -n`、`git diff --check`，design 和 commit 两个技能的 `quick_validate.py` 校验。仓库 `.prettierignore` 忽略所有 Markdown；Prettier 检查未实际格式化或验证这些正文，不将其作为排版正确的证据。

## 后续真实使用验证

- 从一个实际项目新开 design，核对发现入口可加载 reference，并观察跨会话恢复、提交归属与 Agent 署名。
- 已发布主题缺授权、旧主题交错历史、已合入主题重开时，应停在具体授权边界并报告保存位置；本轮不在真实远端制造这些历史。
- CC / Codex 共用同一份规则；本轮在 Codex 完成实现与审查，未声称已经在 CC 真实会话端到端验证。
