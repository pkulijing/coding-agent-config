# 总结：DSH 作为第三个使用端

## 背景

本仓原本只服务 Codex 与 CC。DSH 的发现语义与两端部分重合：skill 根、`AGENTS.md`/`CLAUDE.md` 候选都兼容，但用户全局规则链（`$DSH_HOME/AGENTS.md` → `<agentsHome>/AGENTS.md`）没有任何入口指向 `GLOBAL_AGENTS.md`；review-loop 也只有 CC / Codex 两种委派入口。本轮把 DSH 接成第三个使用端，同时把实测到的平台差异写进规则与文档。

## 实现

### 安装与部署（`install.sh`）

- 新增 `deploy_dsh()`：仅当 `${DSH_HOME:-$HOME/.dsh}` 存在时，把 `${DSH_AGENTS_HOME:-$HOME/.agents}/AGENTS.md` 链到本仓 `GLOBAL_AGENTS.md`。
- 不在 `~/.dsh` 下再放一份：DSH 的全局链本来就按「harness home → 共享 agents 根」读取，写共享根一份即可；`~/.agents` 同时是 Codex 与 DSH 的技能根，共享资源只有一个 owner。
- 不重复部署技能投影：默认 agents 根下 `deploy_codex` 已逐技能链到 `~/.agents/skills/`（DSH rank 500 扫描该根）；只有覆盖 `DSH_AGENTS_HOME` 时，DSH 的技能根随之改到该根的 `skills/`，此时 `deploy_dsh` 补一次 `deploy_skills`，否则该路径会静默丢光全部共享技能。
- 幂等与用户文件保全沿用 `link_item` 既有语义（已正确则跳过；真实文件移为 `.bak` 并 warn）。

### review 编队（`skills/review-loop/SKILL.md`、`agents/dsh-review.toml`）

- 新增 `agents/dsh-review.toml`：`[reviewer]` 与 `[deep_reviewer]` 两个角色的 provider/model/reasoning_effort。本机唯一 route 为 `deepseek-account/deepseek-flash`，思考档没有 medium，普通 reviewer 取 `high`、深审取 `max`。
- 不设 `[orchestrator]`：实测 DSH 的委托深度上限为 1，子 agent 再调 `subagent` 会被拒（`current 1, maximum 1, remaining levels 0`），orchestrator 子 agent 无法扇出。
- Step 3 编队约束补 DSH 真源；Step 4 新增「DSH 委派入口」：主会话按档位表**直接并行起 N 个 reviewer**（`subagent`，不是 `subagent_fork`），主会话承担 orchestrator 的汇总职责；每次调用显式传 provider/model/reasoning_effort，禁止继承主会话档位；只读由任务书约束并如实声明。
- 资源预检、Step 5 ② 的模型传参说明同步补 DSH；`references/rationale.md` 增加「平台编队形态」：深度上限改变编排位置，不改变角度、模型档与 rubric，不构成减配。
- README 与 AGENTS.md 的部署表、review 规格段同步登记。

### MCP 迁移（DSH profile，不在仓库内）

`~/.dsh/profiles/desktop/cordis.patch.yml` 追加：

```yaml
- id: mcp-manager
  config:
    servers:
      gitlab-anyverse:
        transport: streamable-http
        url: https://gitlab.anyverse.work/api/v4/mcp
      playwright:
        transport: stdio
        command: npx
        args:
          - '-y'
          - '@playwright/mcp@latest'
          - '--headless'
          - '--isolated'
```

写入前备份为 `cordis.patch.yml.bak.<时间戳>`。Playwright 与 GitLab 的 MCP 工具在写入后即为当前会话可见（`mcp__playwright__*`、`gitlab-anyverse` 资源服务器），说明 profile 已热加载且字段被接受。

## 验证

| 项 | 结果 |
| --- | --- |
| `bash -n install.sh` | 通过 |
| 新增 `docs/69-DSH三端配置接入/test_dsh_deploy.py`（7 用例，全部走 `CCG_INSTALL_LIB_ONLY=1` 函数级入口：主流程未触发、无 `~/.dsh` 跳过、`DSH_HOME` 指向不存在目录跳过、存在时建链、二次运行 dentry 不变、用户文件备份、自定义 agents 根同时部署规则与技能） | 7/7 通过 |
| 隔离 HOME 整装沙盘（默认根 / `DSH_AGENTS_HOME` 自定义根） | 两次均 exit 0；默认根建链且 16 个技能就位；自定义根建链并部署 16 个技能，默认根的 `AGENTS.md` 未被写入（该根的 16 条技能链由 `deploy_codex` 照常部署，不是 `deploy_dsh` 的重复投影） |
| 既有 `docs/61-Codex全盘迁移/test_install_migration.py`（17 用例，隔离 HOME 全量安装） | 17/17 通过，无回归 |
| MCP profile | YAML 解析通过；写入后两个服务器在会话中可用 |
| 全局规则生效 | `~/.agents/AGENTS.md` 建链后由 DSH 的全局链读取；实际生效需新会话，本轮不重启应用 |

## 局限

- DSH 的子 agent 没有结构性只读限制，review 的「只读」仅由任务书约束；这一点与 Codex 分支一致，已在 SKILL 中如实写明。
- DSH 的 review 编队没有独立 context 的 orchestrator，汇总在主会话；每个角度的审查仍在独立 context 中，已在 SKILL 与 rationale 中写明边界。
- 本机只有 `deepseek-flash` 一个 route，review 无法做到跨模型；这与 `references/rationale.md` §3 的既有边界一致。
- hooks 未迁移：`fix-after-edit` 在 DSH 侧不存在，提交前 lint 继续作为门禁。
- CC 的 `permissions` 清单在 DSH 无等价物，靠 sandbox + 审批；`git push --force` 等硬禁令不再被清单拦截。

## 后续 TODO

- `docs/DEVTREE.md` 的「Epic 结构」是作者维护区，本轮未擅自加入 69（该区自 68 轮起未同步，66/68 也缺）；建议作者确认归入「多 Agent 兼容」后跑 `/devtree` 重生成图表与索引。
- 若 DSH 提供文件型 hooks（或 `dsh-hooks-*` 包进入安装包），再把 `fix-after-edit.sh` 接成 `tools/result` 观察者。
- DSH 若开放 `customSkillDirs` 的 profile 级配置，可评估是否需要单独挂载 CC 独有技能目录；当前共享软链已足够。
- 视 DSH 版本升级，复核委托深度上限与子 agent 只读能力；若上限放开，可回到「orchestrator 子 agent」编队。
