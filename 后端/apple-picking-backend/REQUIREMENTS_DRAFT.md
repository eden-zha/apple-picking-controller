# 后端需求说明

本系统为真实机器人AI控制系统：
控制链采用 policy_runtime_service + robot_client 的闭环执行架构。
mock_task 仅用于UI兜底显示，不参与任何机器人控制。

## 1. 当前目标

后端必须支撑真实 SO-ARM101 机器人 AI 控制闭环，是任务控制、policy 推理入口和机器人执行入口之间的协调层。

## 2. 必须支持的能力

- 查询当前系统状态、机器人状态和 policy 状态。
- 接收 UI 启动任务指令。
- 接收 UI 停止任务指令。
- 接收 UI 复位系统指令。
- 接收 UI 选择目标采摘模式指令。
- 通过 `task_control` 进入真实控制链。
- 通过 `policy_runtime_service` 执行 LeRobot ACT policy 推理。
- 通过 `robot_client` 读取 SO-ARM101 观测并发送动作。
- 通过 `status_fusion` 向 UI 提供融合状态。
- 在状态源不可用时允许 UI fallback 显示，但不允许 fallback 参与执行。

## 3. 标准控制链

```text
frontend
  -> FastAPI backend
  -> task_control
  -> policy_runtime_service
  -> LeRobot ACT policy inference
  -> robot_client
  -> SO-ARM101 robot execution
```

## 4. 标准展示链

```text
robot_status + backend_state + optional mock fallback
  -> status_fusion
  -> websocket / HTTP
  -> frontend UI
```

## 5. local / remote 行为

local：

```text
backend -> policy_runtime_service（本机进程） -> robot_client -> SO-ARM101
```

remote：

```text
backend -> HTTP -> Robot PC -> policy_runtime_service（远程进程） -> robot_client -> SO-ARM101
```

local 和 remote 只表示部署位置不同，不能改变控制链语义。

## 6. 接口需求

- `GET /status`：返回后端任务状态、robot_status、policy_status 和日志。
- `POST /set_target_apple`：设置目标采摘模式。
- `POST /start_task`：启动真实 policy 控制任务。
- `POST /stop`：停止真实 policy 控制任务。
- `POST /reset`：复位后端任务状态。
- `GET /logs`：返回运行日志。
- WebSocket：推送 `status_fusion` 的融合状态。

## 7. 禁止项

- local 模式必须描述为本机真实 policy 闭环部署。
- 禁止把 remote 模式描述为没有 policy runtime 的 robot PC。
- `mock_task` 只能用于 UI fallback 展示。
- 禁止让 frontend 直接控制机器人。
- 禁止让 fallback 进入 action / control chain。
