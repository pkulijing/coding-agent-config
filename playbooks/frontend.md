# 前端开发规则

适用于前端代码、Web UI 与 React/Vite/TypeScript 项目。前后端是独立维度，默认前端放 `frontend/`。

## 1. 环境与工具

- 使用 npm，默认源为 npmmirror；Biome 负责格式与 lint，TypeScript strict。具体参数和依赖范围以 `templates/react-vite/__subpath__/` 的配置为准，不在本文另存版本基线。
- 从前端工作目录执行项目的 `npm run lint`、`npm run typecheck`、`npm run build`；多 workspace 按各自脚本验证。
- 模板使用纯 JSON 的 `biome.json`；如需注释，采用 Biome 支持的 `biome.jsonc`，不要添加伪注释键。配置发现方式见 [Biome 配置](https://biomejs.dev/configuration/configure-biome/)。
- worktree 的依赖准备和临时软链清理按 `skills/start/references/worktree-create.md`，运行门禁前确认依赖可用。

## 2. 布局与个人默认值

采用 `react-vite` stack 模板：`src/` 放源码，`@/` 指向 src；更改 alias 时同时更新构建与 TypeScript 配置。

- Tailwind 使用 v4 CSS-first 和 Vite 插件，主题在 CSS 定义。
- shadcn 使用 new-york / neutral，组件由 CLI 按 `components.json` 生成；新增组件使用 `npx shadcn@latest add <name>`，className 组合用 `cn`。
- 默认深色，可切 light/system，并持久化选择。
- 编辑器配置合并到仓库根 `.vscode/`，不在前端子目录维护第二份；合并机制见 `templates/MECHANICS.md`。

## 3. 项目边界

- 前后端并存时，开发 proxy 的后端地址来自项目配置；无权威地址时询问，不探测猜测。纯前端项目移除无用代理。
- 规则豁免须有具体代码理由与最小范围。WebGL/canvas 不是豁免 React Hook 调用规则的理由；不要按目录关闭 `useHookAtTopLevel`。见 [React Hooks 规则](https://react.dev/reference/rules/rules-of-hooks)。
- 自定义输入组件的 label 使用明确的 `htmlFor` / `id` 关联。
- 持有 WebGL、音频、连接、观察器或定时器的组件，验证卸载清理与异步加载结束后的释放。具体释放 API 查实际库版本，不把某个组件的清理配方套到所有资源。

## 4. 验证

组件与纯逻辑测试可用 Vitest + Testing Library，遵循全局 TDD 契约；引入时补齐配置与 test 脚本。编排型页面至少有一条 happy-path 渲染冒烟。

运行项目类型检查、lint 和构建；交互改动检查实际页面。资源组件应覆盖重复挂载/卸载和加载途中退出，功能测试与截图不能替代生命周期验证。
