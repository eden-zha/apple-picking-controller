# 真实机器人 AI 控制架构

本系统为真实机器人AI控制系统：
控制链采用 policy_runtime_service + robot_client 的闭环执行架构。
mock_task 仅用于UI兜底显示，不参与任何机器人控制。

## Control Path

```text
frontend
  -> FastAPI backend
  -> task_control
  -> policy_runtime_service
  -> LeRobot ACT policy inference
  -> robot_client
  -> SO-ARM101 robot execution
```

职责边界：

- `frontend`：发送任务意图、目标模式和停止请求；不直接生成机器人动作。
- `FastAPI backend`：提供 HTTP/WebSocket API，维护任务状态。
- `task_control`：编排任务生命周期，并调用 policy runtime。
- `policy_runtime_service`：唯一 AI 推理入口，负责加载并运行 LeRobot ACT policy。
- `robot_client`：唯一硬件执行入口，负责读取机器人状态并发送动作。
- `SO-ARM101`：真实机械臂执行端。

`mock_task` 不在控制链中，不生成 action，不驱动任何硬件。

## Realtime Closed Loop

```text
robot_client.get_state() / get_observation()
  -> policy_runtime_service.run_policy(observation)
  -> LeRobot ACT policy inference
  -> robot_client.send_action(action)
  -> SO-ARM101
  -> robot_client.get_state() / get_observation()
```

如果机器人断连、观测缺失、policy 加载失败或动作发送失败，系统应进入暂停、停止或错误状态。不得用 `mock_task` 替代真实控制。

## UI Fusion Path

```text
robot_status + backend_state + optional mock fallback
  -> status_fusion
  -> websocket / HTTP
  -> frontend UI
```

UI fusion 只影响展示，不影响控制逻辑。mock fallback 只用于页面兜底显示，不能参与 `policy_runtime_service -> robot_client` 执行链。

## Local Mode

```text
backend
  -> policy_runtime_service（本机进程）
  -> robot_client
  -> SO-ARM101
```

local 模式用于本机部署真实 AI 控制闭环。

## Remote Mode

```text
backend
  -> HTTP
  -> Robot PC
  -> policy_runtime_service（远程进程）
  -> robot_client
  -> SO-ARM101
```

remote 模式用于把 policy runtime 和 robot client 部署到 Robot PC。主后端不得绕过远程 `policy_runtime_service` 直接调用机器人硬件。

## Required Configuration

Policy model:

```text
LEROBOT_POLICY_MODEL_PATH=D:\path\to\outputs\train\...\pretrained_model
POLICY_INFERENCE_HZ=20
```

Remote policy runtime:

```text
POLICY_RUNTIME_REMOTE_URL=http://<robot-pc-host>:8000
```

Local robot client options:

```text
LOCAL_ROBOT_CLIENT_URL=http://127.0.0.1:<robot-service-port>
SO_ARM101_ROBOT_FACTORY=your_module:create_robot
```

The direct Python factory must return an object compatible with:

```text
connect() optional
get_observation() or capture_observation()
send_action(action) or set_action(action)
disconnect() optional
```

## Status Contract

`GET /status` should expose:

- `backend_state` / `task_state`
- `robot_status`
- `policy_status`
- `logs`

If `robot_status.source = "mock_fallback"` appears, it means display-only fallback.
