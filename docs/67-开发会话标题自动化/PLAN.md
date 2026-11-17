# 开发会话标题自动化计划

状态：用户已确认；实现、验证及独立 review 完成，审查记录见 REVIEW.md。

## 方案

### 1. 会话标题工具

新增 `scripts/codex_session_title.py`，提供设置开发轮次标题与追加完成状态的窄接口。

- 当前会话 ID 取 `CODEX_THREAD_ID`；轮次和中文描述由调用技能显式传入，不靠扫描其他聊天猜测。
- 使用 `codex app-server daemon version` 的结构化输出发现已运行服务的控制 socket；支持显式指定 socket 以适配其他主机部署。缺少信息时报告所缺参数，不探测其他账号或服务地址。
- 通过成熟 WebSocket 库连接现有 Unix socket，完成原生初始化并核对当前会话；用 `thread/name/set` 设置标题，随后读取实际标题核验。
- 使用 Python 与 uv 管理运行和所需依赖；不手写生产 WebSocket 协议栈。具体依赖入口在实施时按仓库现有方式落地。
- 对 RPC 错误、超时、连接中断、无法读回和读回不一致分别给出非零状态及简洁诊断。写入后失联按结果未知处理，不宣称成功。
- 更新操作有总超时，连接和子进程按实际使用情况释放；不自动启动、重启或更新服务，不开监听端口。
- 完成后标题固定为 `r<N>-<中文描述>-已完成`，重复执行不叠加后缀。

### 2. 接入开发生命周期

- `/start`：在用户确认 PLAN、准备开始实施时，对 Codex 当前会话调用标题工具。仅生成待确认计划时不标记已开始执行。
- `/finish`：在适用的提交及收尾步骤成功后更新同一会话的完成标题；仍有必需动作失败或等待确认时不标记完成。
- 技能先检查脚本路径和运行前提；非 Codex 环境不执行此能力。失败明确说明并保留开发现场，不能静默替换为改聊天记录。
- 在 README 说明标题格式、触发时点、运行依赖与失败时的限制。共享脚本与既有技能内容沿原目录软链部署，无需新增 skill 或扩大 routine 权限。

### 3. 验证与交付

- 先列正常、边界、异常用例并跑红，再做最小实现。
- 使用临时 HOME、命令桩和本地 WebSocket fixture 验证真实工具入口与实际 RPC，不依赖开发者真实账号、现有会话或外网。
- 独立 context 的提交前 review 依现行 `/review-loop` 执行；随后完成 SUMMARY、相关 README 与开发树更新，按开发工作流提交。
- 实际会话改名只在计划确认后进行：本轮开始标题为 `r67-开发会话标题自动化`；完成标记只在本轮实际完成时设置。

## 关键验收用例

| 条件 / 输入 | 预期结果 |
| --- | --- |
| 轮次 31，描述“修复视频卡顿”，执行开始更新 | RPC 目标是明确的当前会话，读回标题为 `r31-修复视频卡顿` |
| 同一轮执行完成更新，再执行一次 | 标题均为 `r31-修复视频卡顿-已完成` |
| 中文、空格及引号等字符 | 通过结构化 JSON 传输，保持输入含义，不形成 shell 代码 |
| 会话 ID 缺失、轮次或描述无效 | 写入前失败，不搜索并选择其他聊天 |
| 无运行中服务、socket 缺失、CLI 非零或输出无效 | 明确错误，不启动服务，不落数据库 |
| RPC 错误、通知先于响应、无响应或连接断开 | 按请求 ID 处理响应；有界结束，报告实际结果 |
| 写入返回成功但读回不一致 / 读回失败 | 不报告验证成功，区分失败与结果未知 |
| 主入口在隔离 fixture 中执行 | 实际完成发现服务、初始化、定位会话、设置标题、读回验证的全链路 |
| `/start` 计划未确认，或 `/finish` 尚未完成必要动作 | 不提前更新为实施中或已完成 |
| 桌面 App 和手机远程打开同一会话 | 分别核对开始标题和完成标题；无法直接观察的一端记为待人工核验 |

## 可行性证据与限制

2026-11-17 在本机完成短小只读沙盘：从 `codex app-server daemon version` 取得 `socketPath`，通过该 Unix socket 发送 HTTP Upgrade，验证 WebSocket 握手后发送 `initialize` / `initialized` 和 `thread/read`（`includeTurns: false`），返回当前 `CODEX_THREAD_ID`，并包含 `name` 字段。结果为 `status=readable`、`sameThread=true`；当前返回的 `name` 为 null。

此前直接向 `codex app-server proxy` 写 JSONL 的探针两次超时。官方实现表明它只是 stdio 与 Unix socket 的原始字节转发，不能省略 WebSocket 握手；正确握手的只读探针已成功。正式工具直接使用库的 Unix socket WebSocket 客户端，避免复用错误的协议假设。

来源：

- [Codex App Server](https://learn.chatgpt.com/docs/app-server)：初始化、Unix socket WebSocket 传输及 `thread/name/set`。
- [CLI proxy 分派实现](https://github.com/openai/codex/blob/main/codex-rs/cli/src/main.rs) 与 [stdio-to-uds 实现](https://github.com/openai/codex/blob/main/codex-rs/stdio-to-uds/src/lib.rs)：proxy 仅转发字节；上游 main 仅作机制参考，实际兼容性以已安装版本实测为准。
- [Remote connections](https://learn.chatgpt.com/docs/remote-connections)：手机远程访问连接主机上的聊天和工具。

已证实的是本机现有服务可读取当前会话；真实改名、广播给客户端及桌面和手机的显示刷新仍属于实施阶段验收，不能提前认定成功。其他操作系统或未暴露本地控制 socket 的部署不由本次 Linux 实测推断支持；若需要不同且有额外代价的接入方式，先说明证据并确认方向。
