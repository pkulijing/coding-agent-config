# routine-slim 候选规则只读预演

2026-11-06，使用本轮工作树的候选技能执行 `--dry-run` 语义。当前分支为 round64-harness-reset，工作树包含本轮未提交改动；只读例外允许预演，正常写入前置仍未满足。本次未运行 fetch、切分支、创建 PR 或修改远端。

1. 读取近四周 Git 变更涉及的 skills/playbooks，以及本轮已整理的入口；未以字符增长率决定是否盘点。
2. GitHub 连接器 `search_prs` 以仓库 pkulijing/coding-agent-config、open 状态、is:pr is:open、上限100查询，返回空列表。此时没有需要追加查询文件集的 open PR；若返回页数或完整性不明，应停止而非据部分列表继续。
3. 检查三个有界样本：paper-read 的输出格式、pybump 的版本规则、quick 的确认/提交出口。前两者承担明确个人选择；quick 的分支与关闭关键字约定仍有工作作用，不因重复术语就取消。
4. 禁止路径 routine-slim 自身、routine-dev、agents 等不进入候选。全局入口只能报告；新 playbooks/references 不在既有写白名单，也不借入口拆分纳入。

本次样本未选出需要另做主题 PR 的候选；没有为证明清理有产出而强行删除。预演验证了无增长阈值、有界选择、保护项排除与无候选退出的文案路径，不证明定时平台已加载新版或已实跑完整写入流程。
