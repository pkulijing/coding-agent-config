# 技能与 review 规则核验

## 审阅范围与保留

已阅读全部 16 份 SKILL.md、8 份 references 和 3 份 agent 任务书。paper-read、pybump、backlog 与 bootstrap 的主体保留：其格式、发布、确认和初始化约定仍承担具体个人选择，不能仅因步骤多而删除。design 保留隔离、单提交归档和历史改写授权，仅调整归档真源说明。

review-loop 保留默认 3 reviewer、重档 5 reviewer、独立 orchestrator、全部角度、模型与思考档来源、逐档能力核验降级、置信 80 门槛、运行验证、两轮留痕放行、TDD 及安全守护测试 mutation。agents frontmatter 和 codex-review.toml 不变。angles 仅删除模型性能泛化和统计旁注，实际核查条目不减少。

## 主要变化

- finish 只为有具体跨项目价值的候选增加沉淀记录，无候选不询问；候选仍需确认才能跨仓建 issue。Step 2 的 wontfix 确认和既有 worktree 收尾权限不变。
- routine-slim 取消增长门槛，允许普通约束退役；仍限制 1–3 文件、保持白黑名单、在途 PR 排除与远端三项权限、人工合入。使用起始 SHA 的审查规则。`--force` 兼容为无需跳阈值的空操作，不扩权。
- README 触发条件放回 finish 入口，判断覆盖本轮已提交改动；关闭 issue 使用新增 helper 契约，部分交付不写关闭关键字。
- sync 新模板内容改从记录的 Git HEAD 读取，与其“不同步未提交模板”契约一致。
- start 修正远端 docs 的树路径，编号识别可选 codex 前缀；主分支探测只去除 origin 前缀，不截断带斜线的分支名。
- 全局退出的重叠实现取舍细则归 finish worktree reference，rebase/start 接回该真源，保留人工确认、备份 tag 与弃因记录。
- 删除 review、rebase、triage、devtree 等的重复解释和事故叙述；rationale 只留设计边界，历史由 Git 保留。

## 已执行检查

- `uv run --no-project scripts/context_budget.py check-refs` 首次因默认 uv cache 沙箱写权限失败；使用临时 UV_CACHE_DIR 重试成功。脚本当前覆盖的路径无失效项。
- `git diff --check -- skills agents` 通过。
- 临时 Git 仓库沙盘通过：建立 `docs/64-topic`，确认 `git ls-tree --name-only <SHA>:docs` 返回子目录；两次提交模板后再修改工作树，确认 `git show <旧/新SHA>:templates/example.txt` 分别返回提交快照、不读取未提交内容；将 origin/HEAD 指向 `origin/feature/base`，确认仅剥 origin 前缀保留完整主分支名。沙盘隔离 HOME/Git 全局配置与 locale，结束即删除，未增加测试框架。
- 人工核对 start → commit → finish、两条 routine → commit/review 的入口与主要失败出口，保留 Step 编号、rationale 1–6 小节及现有调用引用；移除对已重组 Python/frontend 数字章节的依赖。
- agent 配置差异仅正文说明，不改变 frontmatter；本轮正式 review 由主 agent 按起始基线另行执行。

这是静态契约与引用核对，不证明模型质量、实际调度运行或外部平台写入已验证。未运行多模型重复任务、A/B 或基准题库，也未修改线上调度注册。
