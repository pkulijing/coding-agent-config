# 为已有 CLI 添加自然语言入口

本模板使用仓根 `.claude-plugin/marketplace.json` 指向 `./plugin`，插件根保留 `.claude-plugin/plugin.json` 与 `skills/`。`example-cli` 是待替换的示例命令，模板不提供该 CLI；接入时先核实真实 CLI 的原生能力与失败语义，再改写 skill，不能把示例命令当成已经可用的业务功能。

通过 bootstrap 或 sync 的 adopt 选择 `cli-plugin` stack 可落地本目录。它可以与现有语言 stack 叠加，不创建或覆盖根级 pyproject、README 或语言依赖。目标文件或软链已存在时，遵守模板冲突确认流程。

## 接入与共用正文

1. 将两份清单中的 `example-cli` 改为实际插件名，替换 marketplace 名、owner 与描述。保留 source 相对 marketplace 根解析的语义；plugin 内容要随仓库一起分发。
2. 按 CLI 用例拆 skill；将 `example-status` 目录、frontmatter 的 name、正文命令与参数一起替换。每新增一个 skill，同步建立 `.agents/skills/<name>` 指向 `../../plugin/skills/<name>` 的相对软链。修改测试中示例路径，使变异测试仍指向一个真实 skill。
3. CC 从插件的 `skills/` 发现内容；Codex 从项目 `.agents/skills/` 的链接读取同一份正文。两边使用各自的调用入口，skill 正文保持平台中立，不依赖 CC 的工具名、hooks 或 `${CLAUDE_PLUGIN_ROOT}`。这些链接是本地发现入口，不是 Codex 插件市场清单。
4. 不支持软链接的平台应先解决 Git 的 symlink 支持并重新检出；不得把链接变成内容漂移的第二份正文。结构测试会拒绝断链或被复制为普通目录的入口。

CC 可在本地项目根用 `claude --plugin-dir ./plugin` 加载，在会话中使用 `/example-cli:example-status`。Codex 使用 `$example-status`。改名后相应替换名称；需要安装到 marketplace 时，另按当前 CC 官方安装流程执行，本模板不自动注册市场或改用户配置。

## 结构验证与行为验收

在接入项目根运行：

```bash
uv run --no-project --with pytest --with pyyaml pytest -q plugin_tests/test_plugin_structure.py
claude plugin validate ./plugin
claude plugin validate .
```

第一条只提供测试所需的临时依赖，不把 Python 加入被包装 CLI 的业务依赖。已有 pytest / PyYAML 环境可用项目自己的测试入口。原生 validate 需要 CC；缺少它时只能声明结构测试结果，不能宣称 CC 加载已验证。

测试校验本模板约定的仓内相对 source、清单名称一致、非空 skill 集、YAML frontmatter 与 Codex 链接，并用临时目录分别损坏 JSON、source、名称、description、SKILL.md、链接，验证它们确实被拦住。它不是完整的平台 schema 验证器，不校验远程 source、自定义组件路径或 CLI 业务行为；扩展这些形态时应同时调整测试与原生校验。

行为验收须在两端分别确认 skill 可见，调用真实 CLI 的最小只读操作，再覆盖非零退出、响应体错误与空结果范围。写操作另验 dry-run 和授权路径。结构全绿不能替代这一步，也不能证明提示词一定被遵守。

依据：[CC manifest](https://code.claude.com/docs/en/plugins-reference)、[CC marketplace](https://code.claude.com/docs/en/plugin-marketplaces)、[Codex 本地 skill 发现](https://developers.openai.com/codex/skills/)。发布时再核对当前平台约定；本脚手架不复制 CLI 业务逻辑。
