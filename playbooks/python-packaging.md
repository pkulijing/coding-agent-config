# Python 打包、发布与安装

仅在制作 wheel、发布 registry 或向目标机安装时读取。开发工具偏好见 `playbooks/python.md`。

## 构建与验收

- 发布包的 Python、依赖范围和资源清单以 pyproject 为真源。先检查构建 backend 原生能力；仅需额外构建步骤时再换 backend 或加 hook。
- wheel 含前端产物时，先完成前端构建，再检查 wheel 内实际包含 dist；在干净安装环境从包资源路径读取，不依赖源码 checkout。
- 锁文件测试与用户从包元数据重新解析依赖是两条路径。发布前验证安装后的主入口和受影响功能，记录实际解析版本；mock 不能代替真实 import。
- 更新工具或 daemon 前核对目标机已有版本与入口，避免覆盖正在使用的正式版。安装成功后核对实际执行文件、版本和关键资源。

## 私有 registry

确认服务地址、项目标识、凭据来源与发布权限，不猜内部参数。凭据使用环境或工具的安全认证配置，不写入 requirements、仓库文件或日志。

保留 TLS 验证。内部 CA 使用工具支持的 CA 文件或系统证书机制；不把 `verify=False`、`--trusted-host`、`--allow-insecure-host` 当默认安装配方。uv 当前证书参数见 [uv TLS 文档](https://docs.astral.sh/uv/concepts/authentication/certificates/)；Requests 可用 CA bundle，见 [SSL 验证](https://requests.readthedocs.io/en/latest/user/advanced/#ssl-cert-verification)。

发布前按目标 registry 核对索引/上传 URL 与幂等选项；不要假设 PyPI 的行为适用于自托管 GitLab。发布后的可下载与可安装需要另验，不能只看上传退出码。

## 隔离试装与更新

- uv 工具试装与正式版并存时，同时指定 `UV_TOOL_DIR` 与 `UV_TOOL_BIN_DIR`，通过 `uv tool dir` 和 `uv tool dir --bin` 核对；试装入口用绝对路径，不加入正式 PATH。
- 同版本开发产物重装须核对安装器是否复用旧版本，按原生 reinstall/upgrade 选项处理，再检查实际产物。
- 使用 `pip install --target` 时，先检查目标目录冲突与更新语义，不以命令成功推断旧文件已替换。
- 应用内更新查询先区分网络失败、无可用版本和已有最新版；使用规范版本比较与平台原生接口，不默认解析 wheel 文件名 HTML。升级动作与重启按产品既有授权执行。
