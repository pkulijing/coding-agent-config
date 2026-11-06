# 领域规则核验

核验日期：2026-11-06。覆盖十份领域入口、三份按场景 reference，以及前端 Biome 模板的一处行为修正。下述核验用于判断具体规则，不构成模型质量评估。

## 具体技术依据

| 对象 | 已读取的依据 | 结论与处理 |
| --- | --- | --- |
| subprocess env | [Python Popen](https://docs.python.org/3/library/subprocess.html#subprocess.Popen)，env 参数段 | 非 None 映射替换默认环境继承；删除与 Click 混为一谈的表述 |
| Click env | [Click testing API](https://click.palletsprojects.com/en/stable/api/#testing)，CliRunner env 参数 | env 为覆盖；保留未设置变量须显式清除的测试要求 |
| React Hooks | [React 规则](https://react.dev/reference/rules/rules-of-hooks)、[Biome useHookAtTopLevel](https://biomejs.dev/linter/rules/use-hook-at-top-level/javascript/) | WebGL 目录不是非顶层 Hook 的例外；删除模板对应 off 覆盖，保留其他配置 |
| Biome 配置 | [配置发现](https://biomejs.dev/configuration/configure-biome/)、[配置参考](https://biomejs.dev/reference/configuration/) | 支持 json/jsonc，配置从工作目录等位置查找；模板仍保持 JSON，不再声称注释必然静默回落。依赖范围以实际 package.json 为准 |
| TLS | [uv TLS](https://docs.astral.sh/uv/concepts/authentication/certificates/)、[Requests SSL](https://requests.readthedocs.io/en/latest/user/advanced/#ssl-cert-verification) | 支持自定义 CA；绕过验证不作为私服默认方案。ROS requirements 不放 token，移除 verify=False 等通用配方 |
| uv 隔离工具 | [uv 环境变量](https://docs.astral.sh/uv/reference/environment/)，UV_TOOL_DIR/UV_TOOL_BIN_DIR | 两项分别控制工具与入口目录；保留试装与正式版隔离，不固定某一机器默认目录 |
| Path 同一性 | [Path.samefile](https://docs.python.org/3/library/pathlib.html#pathlib.Path.samefile) | 保留已有文件判断及不可访问错误；删除不存在路径可凭字符串归一化兜底的配方 |
| Rich | [Console API](https://rich.readthedocs.io/en/stable/reference/console.html)，markup/highlight 参数；本机 cydev 环境 rich/console.py print 签名 | 保留外部文本关闭 markup/高亮的条件要求，移到专项 reference |
| Uvicorn | [config](https://github.com/encode/uvicorn/blob/master/uvicorn/config.py)、[server](https://github.com/encode/uvicorn/blob/master/uvicorn/server.py)，并核对本机 teleop-operator 环境对应源码 | 默认 graceful timeout 为 None，任务等待后还有 lifespan；保留有界退出要求，移到长连接场景。settings 网页获取超时后已取到源码，不以失败代替核实 |
| shell 启动环境 | 本机 /usr/share/man/man1/bash.1 的远程 shell daemon 启动段 | 旧版 man 已存在按调用方式读取 bashrc 的分支；删除“所有非交互 ssh 一律不读”的绝对断言，改为按真实入口核验环境。GNU 在线手册两条 URL 获取超时，不声称核实所有当前 shell 版本 |
| systemd oneshot | [上游 systemd.service.xml](https://github.com/systemd/systemd/blob/main/man/systemd.service.xml)，TimeoutStartSec 段 | oneshot 默认不设启动超时；保留显式上限和内部收尾预算。官网 man 获取超时后读取上游源码 |

## 取舍与路由

- 保留个人工具、布局、OO/import/命名、前端主题与 shadcn、飞书文档署名等默认值。版本号由模板/项目配置承担，不替用户统一升级依赖。
- Python 运行专项、LLM 编排和 shell 进程管理分成三个 reference，入口明确限定场景；普通 Python 改动和一次文本 API 调用不递归加载它们。
- Lark 历史 SVG 编译补丁、ROS 构建系统教程与特定私服配方、旧模型成功率/耗时表不再作为执行指令；具体任务查对应技能或当前工具文档。没有新增事故档案。
- 云端能力矩阵不再当当前事实；仅 claude.ai Routines 场景加载该入口，实际能力须核验。移除旧“两轮人工闸”副本，不改变 review 标准。
- Python 编排入口至少一条 happy-path、远端高影响脚本本地沙盘、资源清理和已有工作保护仍保留。

## 静态验证

模板 biome.json 经 Node JSON.parse 通过，检查未残留 useHookAtTopLevel 的 off 覆盖。领域文件与两份模板改动的 git diff --check 通过。

使用模板指定的 Biome 2.5.0，在临时目录复制基线与新版配置，针对同一份 src/gl/check.tsx 运行 `biome lint --vcs-enabled=false`（临时沙盘不依赖 Git ignore）：条件内调用 useState 在基线配置退出 0，新版配置报 useHookAtTopLevel 并退出 1；改为组件顶层调用后退出 0。未改变规则开关的命令行选项，验证覆盖实际目录 override 行为。

Biome 离线缓存不可用（ENOTCACHED），沙箱网络获取返回 EPERM；经工具授权后下载至临时 npm 缓存完成上述验证。未安装到项目或用户全局依赖，也未运行整个前端构建；本次仅修改 lint 配置，没有应用源码变更。

引用审查覆盖三个新增 reference 的入口、Python 编排标题、模板 smoke 注释与 shell 沙盘 §4。全仓引用检查由主任务统一执行。
