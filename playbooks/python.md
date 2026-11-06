# Python 开发规则

适用于 Python 代码、项目依赖与风格选择。本文保留个人默认值；已有项目的明确约定优先。共享入口为 `~/.coding-agent/playbooks/python.md`。

## 1. 环境与工具

- 项目依赖使用 uv：`uv add`，运行使用 `uv run`，格式与检查使用 ruff。开发项目不使用裸 `pip install` 或 `uv pip install` 修改依赖。
- Python 由 uv 管理，项目默认 `python-preference = "only-managed"`；具体版本取项目配置。
- 普通包默认清华 PyPI 镜像。torch/CUDA 的版本与轮子源属于目标设备和项目配置；不要把某台设备的组合变成所有项目默认值。
- 外部独立应用使用它自己的依赖清单与隔离环境，可用 `uv pip install -r requirements.txt`；不把整套上游应用依赖塞进本项目。资源路径优先用应用原生配置。
- lint/format 不改上游或 vendored 源码；仓库含此类目录时配置 ruff 的 `extend-exclude` 与 `force-exclude`，并检查实际文件范围。

## 2. 项目骨架

新建包默认 src 布局，`src/<pkg>/`、`tests/`、`configs/` 平级，默认 uv_build。具体配置使用 `templates/python-uv/`，不要在规则中另存版本副本。

只有需要 uv_build 不支持的构建能力时才切 backend，先核实当前 backend 的原生能力。

### 多包 workspace

使用 `templates/python-uv-workspace/`：虚拟根维护 workspace 配置，成员包各自有 pyproject。根不运行单包 `uv init --package`。本地成员依赖用 workspace 声明，发布时另查包元数据是否完整。

## 3. 开发风格

- 偏好面向对象管理有生命周期的状态与资源；简单计算仍可用函数。不因出现嵌套字典就强制重构。
- 默认包内绝对 import；包层次深或需频繁整体迁移时可以相对 import。
- 文件围绕一个核心类时，文件名用该类名的 snake_case；多个协作类用主导类或概念命名。
- 注释说明当前行为与非显然原因，不复述代码或开发轮次。上游 workaround 可保留必要来源链接。
- 外部鸭子类型优先用 Protocol 表达需要的接口，不为标注引入重型运行时依赖。类型声明不代替运行时输入校验；容错依接口契约决定。

### 编排入口验证

拼装多个组件的编排器 / facade 至少有一条最小 fixture 的 happy-path integration test，实际调用主入口；只测 helper 不能验证装配完成。

## 4. 测试

TDD 与环境隔离要求以全局宪法“测试先行（TDD）”为准。

- pytest 测试落 `tests/`，使用 `uv run pytest`；测试配置沿用项目模板。
- 外部协议、坐标与单位等 fixture 使用独立真值，不复用被测代码推导输入与期望。
- 对环境分支，在被测模块读取变量的位置显式控制条件，分别测各分支。真实网络、时钟、HOME 和缓存不是默认测试输入。
- `subprocess(..., env=mapping)` 用该映射替换默认环境继承；Click `CliRunner` 的 env 是覆盖。表达“未设置”应显式清除目标变量，不以“不传”或空串冒充缺失。见 [Python subprocess](https://docs.python.org/3/library/subprocess.html#subprocess.Popen) 与 [Click testing API](https://click.palletsprojects.com/en/stable/api/#testing)。
- mock 验证程序如何处理返回值，不能证明真实 SDK 接口或模型行为。按交付风险保留实际接口与主入口验证，真机前提缺失则明确记录未验证范围。

## 按场景加载

- 做 wheel、registry 发布或目标机安装：读 `playbooks/python-packaging.md`。
- 操作已有文件同一性、Rich 外部输出或 Uvicorn 长连接退出：只读 `playbooks/references/python-runtime.md` 对应小节。
- 做 LLM 调用：读 `playbooks/llm-app.md`。不因使用 Python 就加载 LLM、ROS 或 GPU 细则。
