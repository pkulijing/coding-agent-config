# issue-close 核验

## 原生能力

2026-11-06 本机实际读取 `gh issue close --help`、`gh help exit-codes`、`glab issue close --help`、`glab issue view --help`：版本分别为 gh 2.92.0、glab 1.93.0。GitHub 支持 `--reason "not planned"`；GitLab close 只有 repo 等通用参数，没有原因字段；两端 view 支持 JSON 和 repo。

另读取 [GitHub CLI v2.92.0 close 源码](https://raw.githubusercontent.com/cli/cli/v2.92.0/pkg/cmd/issue/close/close.go)：已关闭 issue 直接成功返回，不更新原因。因此 helper 关闭后回查 state，GitHub 还查 stateReason；不会因原生命令 exit 0 就宣称已按指定原因关闭。

尝试读取 GitLab main 与 v1.93.0 的 close 源码，Web 返回 Cache miss；没有以此推断失败实现。GitLab 参数依据本机帮助，结果通过关闭后读取 JSON 状态确认；未验证真实远端写操作。

## 自动验证

- 先添加 `test_issue_close.py` 并运行，因缺少 issue-close 子命令出现预期红态。
- 实现后 11 个测试方法通过（包含两平台及多组异常子用例）：默认完成、not-planned、跨仓关闭/回读目标一致、关闭失败、回读失败、空/无效 JSON、状态未关闭、原因不符、未知平台、非法原因、CLI 缺失。
- 通过 main 入口验证参数解析与命令分发；所有外部调用均打桩，不读取真实身份、网络、时钟或 HOME。
- 原 helper `--self-test` 通过。

命令使用 `UV_CACHE_DIR=/private/tmp/round64-uv-cache uv run --no-project python -B`，分别运行本目录 `test_issue_close.py` 和 `scripts/platform_issue.py --self-test`。临时缓存用于避开沙箱不可写的默认 uv 缓存；没有改变用户 uv 配置。

## 交付限制

GitLab 不存储 close reason；helper 明确报告此平台差异，不自动发评论。回查失败意味着结果未确认，可能已经关闭。测试证明本地编排与错误传播，不证明远端权限、服务可用性或用户凭据正确。

## context_budget 引用范围适配

`playbooks/references/*.md` 纳入当前扫描和历史 delta 的共同口径；因此把正文搬进 reference 不会被误报为同等体量的删除。check-refs 支持其完整仓库路径、共享 HOME 前缀，以及 playbook 入口的相对 `references/*.md`。仍只检查原有的反引号路径白名单，不扩展到通用 Markdown 解析。

先写本轮 `test_context_references.py`，6 项均在实现前呈预期红态，随后全部通过；原第 52 轮 41 项和第 61 轮 context 迁移 9 项全部通过。历史测试未修改。测试覆盖扫描/历史范围一致、搬移体量不变、完整/共享路径、相对入口、reference 内部断链和 JSON 估算说明。

旧 token 系数、数值字段与可选 threshold 退出码保持兼容。文本输出与 JSON 的 `token_estimate_note` 明确标注历史估算、非当前模型实测；阈值结果只报告体量，不再指示是否应精简。
