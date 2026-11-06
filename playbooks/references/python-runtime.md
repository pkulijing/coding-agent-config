# Python 专项运行边界

只在对应任务读取相关小节，不是 Python 开发的通用必读清单。

## 子进程与 CLI 环境隔离测试

`subprocess(..., env=mapping)` 用该映射替换默认环境继承；Click `CliRunner` 的 env 是覆盖。表达“未设置”应显式清除目标变量，不以“不传”或空串冒充缺失。见 [Python subprocess](https://docs.python.org/3/library/subprocess.html#subprocess.Popen) 与 [Click testing API](https://click.palletsprojects.com/en/stable/api/#testing)。

## 已有文件同一性

保护已有文件、防止覆盖或去重时，使用文件系统同一性判断，不能仅比较路径字符串。Python 的 [Path.samefile](https://docs.python.org/3/library/pathlib.html#pathlib.Path.samefile) 可判断已有路径是否指向同一文件；无法访问会抛异常。

文件尚不存在时，先明确操作需要保护的对象和竞态条件，不以字符串归一化声称已解决同一性。测试分别指定大小写/链接等条件，权限错误不能被当作“不是同一个”。

## Rich 外部输出

将用户或外部命令文本交给 Rich 时，关闭 markup 解析或使用 `rich.markup.escape`；逐字透传另关闭自动高亮。可信的程序自有 markup 才启用解析。按项目 Rich 版本核对选项，不把转义后的内容再次当 markup 拼接。

## Uvicorn 长连接退出

WebSocket、SSE 或流式服务显式设置有限的 `timeout_graceful_shutdown`，按部署排空预算选值。该参数限制连接/任务等待，不是整个进程退出上限：lifespan、应用资源和子进程收尾仍需有界。

验收保持真实长连接，分别通过实际启动路径发送 Ctrl-C / SIGTERM，核对退出时间、清理副作用与子进程，不只检查空服务退出。

依据：[Uvicorn config](https://github.com/encode/uvicorn/blob/master/uvicorn/config.py)、[shutdown 实现](https://github.com/encode/uvicorn/blob/master/uvicorn/server.py)。接入时核对项目实际版本。
