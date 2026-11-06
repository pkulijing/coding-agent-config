# ROS 2 开发规则

适用于 ROS 2 包、colcon 工作空间、ament 与 launch。产品仓的统一构建、交叉编译和设备配置以该仓库约定为准。

## 布局与依赖

- 默认工作空间根放构建配置，包放 `src/`，使用 `ros2` stack 模板；build/install/log 与 compile_commands 等产物忽略。
- package.xml 使用 format 3，包目录、包名与 CMake project 一致，版本采用语义化版本。按实际编译/运行/测试需求声明依赖。
- C++ 默认 ament_cmake，Python 默认 ament_python；需要 CMake 装配能力时再选 ament_cmake_python。不要仅为解决一个未核实的 hook 问题切构建系统。
- 依赖同时核对 package.xml、查找/链接与下游导出。公共接口的依赖须可被下游解析，不以“第三方库”作为不导出的理由。
- 构建参数优先作用于 target，不覆盖工具链注入的 flags。第三方 SDK 的可选性由功能契约决定，缺少必需 SDK 应失败，不能统一降为 WARNING。

## Python 与私有依赖

ROS 环境遵循目标发行版的解释器与依赖策略，不能机械套开发机 uv 环境。现有项目的 requirements/rosdep 流程优先；仅在确需自定义 rosdep key 时添加它。

私服 URL 与认证由部署配置提供。token 不进入 requirements 或版本库；内部 CA 配置信任，不默认跳过证书校验。发布/安装细则仅在相关任务读取 `playbooks/python-packaging.md`。

同一纯 Python 包被 uv 与 colcon 消费时，分别验证两套构建元数据与安装后 import；不要假定某一套安装成功就证明另一套也可用。

## 逻辑与验证

业务逻辑尽量独立于 ROS，节点负责协议转换与调度。Python 测试按 `playbooks/python.md`，缺 ROS 运行时的集成用例可明确 skip，纯逻辑用例照常运行。

使用仓库原有构建入口；通用流程为 colcon build/test，并检查 test-result。确认测试实际开启，新增包需验证依赖、安装位置、节点入口与配置资源。具体 ament API 按目标 ROS 发行版官方文档查询，不复刻版本相关教程。

## launch 参数

实现“命令行覆盖 YAML”时，先定义缺省与显式空值是否不同；只将用户提供的覆盖加入参数，按节点契约解析类型。非法 bool/数值应报告，不把任意字符串静默转成 false。验证未传、合法覆盖和非法输入三条路径。
