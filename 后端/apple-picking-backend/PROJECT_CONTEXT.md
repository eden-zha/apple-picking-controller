# 项目背景与系统边界

本系统为真实机器人AI控制系统：
控制链采用 policy_runtime_service + robot_client 的闭环执行架构。
mock_task 仅用于UI兜底显示，不参与任何机器人控制。

## 1. 项目背景

本项目是具身智能方向的小组项目，目标是通过 UI、后端、ACT policy 和 SO-ARM101 机械臂完成真实苹果采摘控制闭环。

系统面向真实机器人执行。UI 负责发起任务意图和展示状态，真实动作必须由 policy runtime 推理后交给 robot client 执行。

## 2. 标准控制链

```text
frontend
  -> FastAPI backend
  -> task_control
  -> policy_runtime_service
  -> LeRobot ACT policy inference
  -> robot_client
  -> SO-ARM101 robot execution
```

组件职责：

1. `frontend`：展示状态，发送目标模式、开始、停止、复位等任务意图。
2. `FastAPI backend`：提供 API 和 WebSocket，维护任务状态。
3. `task_control`：统一编排任务生命周期。
4. `policy_runtime_service`：唯一 AI 推理入口，加载并运行 LeRobot ACT policy。
5. `robot_client`：唯一机械臂硬件接口，读取观测并发送动作。
6. `SO-ARM101`：真实执行端。

## 3. UI 展示链

```text
robot_status + backend_state + optional mock fallback
  -> status_fusion
  -> websocket / HTTP
  -> frontend UI
```

展示链和控制链分离。mock fallback 可以帮助 UI 在状态源暂不可用时保持可读，但它不能生成 action，不能控制机械臂，也不能替代 policy runtime。

## 4. local / remote 部署

local：

```text
backend -> policy_runtime_service（本机进程） -> robot_client -> SO-ARM101
```

remote：

```text
backend -> HTTP -> Robot PC -> policy_runtime_service（远程进程） -> robot_client -> SO-ARM101
```

local / remote 是同一套 AI 控制系统的不同部署方式，控制语义保持一致。

## 5. 当前原则

1. 所有真实控制都必须经过 `policy_runtime_service`。
2. 所有硬件执行都必须经过 `robot_client`。
3. `mock_task` 只用于 UI fallback，不参与任何控制链。
4. 前端不直接控制机器人。
5. remote 模式下 Robot PC 必须运行远程 policy runtime。
6. 当真实机器人、观测或 policy 不可用时，系统应进入暂停、停止或错误状态。
