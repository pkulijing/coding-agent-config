# Round 77 · 将 routine-dev 的文件边界判定移入可测试的只读 helper

> 读者：维护 `coding-agent-config` 与 `routine-dev` 的开发者与审阅者 · 如何以确定性、只读、fail-closed 的方式校验 `routine-dev` 的文件路径边界与在途 PR 撞车
> 来源：[Issue #204](https://github.com/pkulijing/coding-agent-config/issues/204) — 将 routine-dev 的文件边界判定移入可测试的只读 helper

## 目标

将 `skills/routine-dev/SKILL.md` 中原本依赖 Agent 按文字执行的确定性文件校验逻辑（封闭白名单、四条红线覆盖、在途 PR 文件并集聚合与撞车检查）下沉为小型、纯标准库、只读的 CLI helper `scripts/check_routine_boundaries.py`，覆盖「分诊/组批预期落点」与「提 PR 前实际 `git diff`」两道检查，并用自动化测试固定边界语义。

本轮不改变 `routine-dev` 的现有授权边界，不写 Git 或远端，不替代独立身份隔离，也不涉及 `/start` 并发编号（#183）。

## 关键决策

1. **严格保持现行授权不变**
   - 封闭白名单精确匹配现行 `skills/routine-dev/SKILL.md` 规则：`GLOBAL_AGENTS.md`、`README.md`、`playbooks/*.md`（仅一级 `.md`，不含 `playbooks/references/*.md`）、`docs/**`、`skills/**`、`templates/**`、`scripts/**`、`hooks/**`。
   - 四条红线（`skills/routine-dev/**`、`agents/**`、`install.sh`、`.github/**`）优先级高于白名单，并采用大小写不敏感匹配以防大小写不敏感文件系统上的变体绕过；白名单保持精确大小写匹配。
   - 路径归一化拒绝空路径、NUL 字节、绝对路径、反斜杠及 `..` 路径段，避免路径穿越或分隔符绕过。
2. **实际 diff 采用 `git diff --name-status -z <base>...<head>`**
   - 替代 `git diff --name-only`：重命名（`R*`）与复制（`C*`）同时提取旧路径与新路径纳入全部检查，防止通过移出红线或重命名冲突文件绕过校验；删除（`D`）同样受检。
   - `-z` NUL 分隔保证含空格、中文、引号、方括号、通配符或换行符的特殊文件名无损解析，不受 `core.quotepath` 影响。
3. **在途 PR 输入采用 fail-closed 完整性契约**
   - 仍由现有平台入口（`gh pr list` / GitHub MCP）负责列 PR 与完整分页，helper 不重复封装平台抓取。
   - `--open-prs <path|->` 必传，支持完整性信封 `{"complete": true, "prs": [...]}` 或配合 `--pr-limit <N>` 的平台原生数组；`complete` 非 `true`、数组条数达到 `--pr-limit`、PR 缺少 `files` 或 `files` 为 `null`/非列表、`filesTruncated: true`、`filesComplete: false`、或 `changedFiles > len(files)` 均直接报错停止，不把残缺输入当作无冲突。
   - 单个 PR 文件项兼容字符串、`{path, previousPath}`（GraphQL）、`{filename, previous_filename}`（REST/MCP），重命名同样收齐新旧路径。
4. **单文件纯标准库风格与退出码分工**
   - 沿用 `scripts/check_routine_identity.py` 的风格：JSON 输出到 stdout，错误摘要到 stderr；退出码 `0` 表示通过，`1` 表示存在边界违规或 PR 冲突，`2` 表示输入不完整、格式错误或底层只读 git 命令失败。

## 实施提纲

1. **TDD 先写测试**：新增 `tests/test_routine_boundaries.py`，覆盖白名单/红线优先级与大小写变体、共享登记文件（`AGENTS.md` 被拒、`README.md` / `templates/MECHANICS.md` 允许且参与撞车）、非法路径、在途 PR 聚合与完整性 fail-closed、以及基于真实临时 git 仓库的重命名/删除/特殊文件名端到端沙盘用例。
2. **实现只读 helper**：新增 `scripts/check_routine_boundaries.py`，提供纯函数 API 与 CLI 入口（支持 `--path`/`--paths-file`/`--paths-json` 预期落点模式与 `--git-diff-base` 实际 diff 模式）。
3. **接入 `skills/routine-dev/SKILL.md`**：在 Step 0 明确 open PR 抓取须含 `files` 与 `changedFiles`（或完整性信封）；在 Step 1.3 / 1.4 接入预期落点校验；在 Step 2「提 PR 前最终复核」改用 helper 的 `--git-diff-base` 模式，校验非 0 即阻断发布。
4. **全量验证与 review**：运行 `bash scripts/check.sh`，并通过 `/review-loop` 复审收敛后提交。

## 验收

- `tests/test_routine_boundaries.py` 覆盖重命名、删除、特殊文件名、共享文件、PR 输入缺失/截断及红线覆盖，全部通过。
- `bash scripts/check.sh`（全量 pytest、`docs_lint.py`、`context_budget.py check-refs`）全部通过。
- `scripts/check_routine_boundaries.py` 不执行任何 Git 写操作或网络/远端调用，验证失败时返回非 0 并在 `skills/routine-dev/SKILL.md` 中明确阻断后续发布动作。
