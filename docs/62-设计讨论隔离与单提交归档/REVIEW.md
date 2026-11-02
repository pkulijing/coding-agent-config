# 提交前 review

## 第一轮

- 编队：独立 context orchestrator；重档五角度（普通 reviewer 四个、deep reviewer 一个），按并发槽位分批完成。
- 配置：`agents/codex-review.toml`；orchestrator 与普通 reviewer 为 `gpt-6.1-sol / medium`，deep 为 `gpt-6-astra / medium`。未降级。
- 范围：本工作树全部改动及紧邻上下文，包括新 reference、计划文档和 Git 沙盘。
- 边界核验：single-branch clone 的窄 fetch refspec 会漏取远端主题；手动 fetch 到 remote-tracking 名称后，缺相应 fetch 映射时 `--track` 仍会被 Git 拒绝。最终规则要求先列全远端 heads、取回候选，并在必要时为此分支追加精确映射。
- 验证：窄 refspec 场景先复现失败，再核对取回主题、建立跟踪及 upstream；修复后 9 组沙盘通过。
- 场景推演：主树有三类无关改动、主题仅在远端且无发布历史改写授权时，恢复隔离树后保留最新文档，原归档 SHA 不变，不 amend、不 push、不另建快照。主线前进场景按提交范围核对后可进入 rebase + FF。
- 返回：五角度完成，修复复核后 clean，无置信度 ≥80 的遗留 finding。

## 第二轮

- 同一重档编队，范围收窄为远端列举、候选取回、跟踪映射及其沙盘修复；检查是否消除边界问题或引入新问题。
- 结果：五角度复审 clean，窄 refspec 问题已消除，未发现修复引入的置信度 ≥80 的问题。未降级，无未收敛遗留。
