# 苹果采摘系统：团队使用说明

本系统为真实机器人AI控制系统：
控制链采用 policy_runtime_service + robot_client 的闭环执行架构。
mock_task 仅用于UI兜底显示，不参与任何机器人控制。

## 项目说明

本项目包含：

- React/Vite 前端 UI：位于 `前端` 目录下。
- FastAPI 后端：`后端\apple-picking-backend`。
- AI 推理层：`policy_runtime_service`，负责调用 LeRobot ACT policy。
- 机器人执行层：`robot_client`，负责向 SO-ARM101 发送动作。
- Windows 一键启动脚本：`start.bat`。

真实控制链统一为：

```text
frontend
  -> FastAPI backend
  -> task_control
  -> policy_runtime_service
  -> LeRobot ACT policy inference
  -> robot_client
  -> SO-ARM101 robot execution
```

`mock_task` 不是控制系统，只能作为 UI fallback 的展示数据来源。

## 首次使用前的准备

请先安装：

- Python 3.12，或其他 Python 3.10+ 版本。
- Node.js LTS（自带 npm）。
- 建议安装 VS Code，方便查看和调试项目。

不要复制或依赖其他成员电脑上的 `venv`。Python 虚拟环境包含本机路径和平台相关文件，应由每位组员在自己的电脑上创建。

## 首次运行

以下命令均在项目根目录打开终端后执行。

1. 进入后端目录，创建并激活自己的虚拟环境：

   ```bat
   cd /d "后端\apple-picking-backend"
   python -m venv .venv
   .venv\Scripts\activate.bat
   ```

2. 安装后端依赖：

   ```bat
   python -m pip install -r requirements.txt
   ```

3. 返回项目根目录，进入当前前端项目目录并安装前端依赖：

   ```bat
   cd /d "..\..\前端\keyon-apple-ui - 前端"
   npm.cmd install
   ```

4. 返回项目根目录，双击 `start.bat`。脚本会自动调用 `launcher.py`，启动后端和前端，并打开 <http://localhost:5173>。

后端接口文档默认地址为 <http://127.0.0.1:8000/docs>。

## 运行模式说明

local 和 remote 是同一套 AI 控制系统的两种部署方式，控制语义保持一致。

### local 模式

```text
backend
  -> policy_runtime_service（本机进程）
  -> robot_client
  -> SO-ARM101
```

### remote 模式

```text
backend
  -> HTTP
  -> Robot PC
  -> policy_runtime_service（远程进程）
  -> robot_client
  -> SO-ARM101
```

remote 模式下，主后端只负责把任务请求送到 Robot PC 上的 policy runtime，不允许绕过 policy runtime 直接驱动机器人。

## UI 展示链

UI 状态展示链为：

```text
robot_status + backend_state + optional mock fallback
  -> status_fusion
  -> websocket / HTTP
  -> frontend UI
```

mock fallback 仅用于状态展示兜底，不生成 action，不参与 `policy_runtime_service -> robot_client -> SO-ARM101` 执行闭环。

## 当前可用能力

- 设置目标采摘模式：`red_only` / `red_green`。
- 开始采摘任务。
- 紧急停止任务。
- 查询任务状态、机器人状态、policy 状态和运行日志。
- 通过 local 或 remote 部署方式进入同一套真实 policy + robot_client 闭环。

## 当前 UI 展示项说明

A/B/C 区域、路线、电量、天气、果筐容量、剩余时间等页面元素属于展示层数据。只有来自真实 `robot_status` 或明确标注为 mock fallback 的数据才应展示；mock 数据不代表控制系统已经执行对应动作。

## 环境变量

常用配置：

- `LEROBOT_POLICY_MODEL_PATH`：LeRobot ACT policy 模型路径。
- `POLICY_INFERENCE_HZ`：policy 推理频率，例如 `20`。
- `POLICY_RUNTIME_REMOTE_URL`：remote 模式下 Robot PC 的 policy runtime 地址。
- `LOCAL_ROBOT_CLIENT_URL`：local 模式下 robot_client 服务地址。
- `SO_ARM101_ROBOT_FACTORY`：可选的本机 SO-ARM101 Python 工厂函数。

## 验证方式

1. 打开 <http://127.0.0.1:8000/docs>，确认 FastAPI 后端运行。
2. 打开前端页面，设置采摘目标并点击开始采摘。
3. 查看 `/status`、WebSocket 或页面状态，确认状态来自 `status_fusion`。
4. 检查日志中任务进入 `task_control -> policy_runtime_service -> robot_client` 链路。
5. 如机器人或 policy 不可用，系统应进入暂停、错误或 UI fallback 展示状态。
