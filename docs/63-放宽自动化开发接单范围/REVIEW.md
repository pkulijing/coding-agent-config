# 提交前独立审查

## 编队与范围

按开发起始基线的 review-loop 默认档执行：1 名 orchestrator，3 名 reviewer 分别覆盖契约与装配、缺陷扫描、规范合规。新建上下文均使用 `fork_turns=none`、`gpt-6.1-sol`、`medium`；第二轮沿用各独立 reviewer 上下文。槽位限制下分两批运行，未减少角度，无降级。

审查根固定为本轮 `.worktrees/round63-auto-dev-scope`，范围为 git status/diff 的全部改动及必要接壤文件，包含新增开发文档。只读、不提交、reviewer 不再派生由任务书约束，工具未结构性强制只读。

已定前提：取消逐条授权及 P0 拒收，允许明确目标的多文件开发和实现选型；开放讨论拒收；保留四条红线与人工合入。上述用户已拍板取舍不作为 finding。

## 第一轮

角度①发现 1 条高置信问题，置信 94：新增部分交付使用 `Refs #N`，但在途 issue 集合仍只识别 Closes。同 issue 已有部分交付 PR、后续计划修改不同文件时，issue 幂等与文件相交两项检查都会漏过。

已修复：在途集合同时解析完整交付关闭关联与部分交付 Refs，明确部分交付仍占用同一 issue。场景验收增加“同 issue、不同文件、Refs 部分交付 PR”对照。

角度②与③无高置信 finding。

## 第二轮

同档三角度复核修复是否消除、是否引入问题，并审查新增 DRY-RUN、SUMMARY 和基线冻结操作说明。三名 reviewer 均 clean，orchestrator 返回无置信 ≥80 的 correctness finding。

没有未收敛遗留，无独立 context 或模型/思考档降级。

## 运行与结构验证

- Python 3.12 执行引用检查：无失效引用。
- labels YAML 与三个 skill frontmatter 解析及结构检查通过。
- git diff 空白检查通过。
- 本轮无新增运行代码；场景分诊是规则推演，未冒充云端或真实开发端到端测试。
- 仓库没有适用于本次变更的项目级语言 lint 配置；未修改模板内的示例项目，按 commit skill 跳过未命中的语言 lint。
