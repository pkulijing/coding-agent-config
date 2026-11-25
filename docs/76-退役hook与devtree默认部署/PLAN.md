# 76. 退役 fix-after-edit hook 与 devtree 默认部署

> 读者：本仓维护者 · 记录退役默认 `fix-after-edit` hook 与停止 `devtree` 默认注册的范围、迁移取舍与验收标准
> 来源：[退役 fix-after-edit hook 与 devtree 的默认部署 (#203)](https://github.com/pkulijing/coding-agent-config/issues/203)

## 目标

1. 退役默认 `fix-after-edit` hook，不新增替代 hook：移除脚本、Codex 与 Claude Code 基线注册及相应使用/信任提示，保留提交前 lint 门禁与验证。
2. 保留足够的老配置迁移逻辑，使早期安装的托管旧定义不再指向已删除脚本，同时保全用户自定义 hook。
3. 停止在各端技能发现入口默认注册已冻结的 `devtree`，清理可证明归属本仓的旧 `devtree` 软链；保留 `skills/devtree/SKILL.md` 源码与 `docs/DEVTREE.md` 历史冻结文档。

## 关键决策

- **`merge_toml()` 在基线无 marker 块时主动移除旧托管块**：原实现遇到无 marker 块的基线会跳过合并，导致老机器 `~/.codex/config.toml` 残留指向已删除 `fix-after-edit.sh` 的条目。改为检测并备份移除旧 `# >>> (claude-code-global|coding-agent-config) managed >>>` 块，保留块外用户配置；无旧块时静默跳过。保留 `migrate_legacy_codex_hooks()` 继续清理历史 `hooks.json` 与无标记 flat TOML。
- **`merge_settings()` 清理变空的 `.hooks` 键**：基线移除 `"hooks"` 后，升级仍按 `MANAGED_MARKER_REGEX` 剔除托管条目并保留第三方 hook；若 `.hooks` 原先非空、剔除托管项后变为空对象，顺带移除 `.hooks` 键（若用户原本即为空对象则不动）。
- **随脚本删除清理 `hooks/` 软链而不留空壳目录**：删除 `hooks/fix-after-edit.sh` 后仓库不再保留 `hooks/` 目录；`deploy_shared()` 与 `ccg_repair_legacy_resources()` 在仓库无 `hooks/` 时清理可证明归属本仓的旧 `~/.coding-agent/hooks` 与 `<agent_home>/hooks`（及 `fix-after-edit.sh`）软链，避免升级后遗留断链，不触碰用户自建目录或第三方文件。
- **`deploy_skills()` 复用 `design` 的精确归属判定扩展至 `devtree`**：在 `RETIRED_SKILLS=(design devtree)` 中统一处理清理、跳过默认部署以及 `legacy` 目录排除，覆盖 Codex、DSH（含自定义 `DSH_AGENTS_HOME`）、Claude Code、Antigravity 全部发现入口，并保全第三方同名软链和真实目录。
- **严格守住 scope**：不修改 `docs/**`（含冻结的 `docs/DEVTREE.md`）、`skills/devtree/SKILL.md` 正文、`skills/routine-dev/`、`skills/routine-slim/`、`.github/labels.yml`。

## 实施提纲

1. 删除 `hooks/fix-after-edit.sh` 与 `tests/test_hook.py`；从 `codex.config.base.toml` 和 `settings.base.json` 移除默认 hook 注册。
2. 更新 `install.sh`：改造 `merge_toml()`、`merge_settings()`、`deploy_shared()`、`ccg_repair_legacy_resources()`、`deploy_skills()`，移除结尾 Codex `/hooks` 信任提示。
3. 更新 `README.md` 与 `AGENTS.md` 中的部署与使用说明。
4. 更新并补充 `tests/test_install_migration.py`、`tests/test_retired_design.py`、`tests/test_antigravity_deploy.py`、`tests/test_dsh_deploy.py` 中的沙盘验收测试。
5. 运行 `bash scripts/check.sh` 与 `/review-loop` 后提交。

## 验收

在临时 `HOME` 沙盘中覆盖并验证：

1. **全新安装**（Codex / Claude Code / DSH / Antigravity）：无 `fix-after-edit` hook、无 `~/.coding-agent/hooks`、各端技能发现入口均无 `devtree`（其他技能正常注册，且仓库保留 `skills/devtree/SKILL.md` 与 `docs/DEVTREE.md`）。
2. **老配置升级**：Codex（旧 marker 块、旧 `hooks.json`、旧 flat TOML）、Claude Code（旧托管 hook 标记）、旧 `~/.coding-agent/hooks` 断链与各端旧 `devtree` 软链全部清理并保留备份。
3. **重复安装幂等**：二次执行不改文件、不新增备份。
4. **第三方保全**：用户自定义 Codex / Claude Code hook、未带本仓标记的同名脚本条目、第三方 `devtree` 软链与真实目录、用户自建 `hooks` 目录全部原样保留。
5. **仓库统一检查**：`bash scripts/check.sh` 全部通过（pytest、`docs_lint.py`、`context_budget.py check-refs`）。
