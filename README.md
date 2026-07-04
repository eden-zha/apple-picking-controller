# 苹果采摘真实机器人 AI 控制系统

本系统为真实机器人AI控制系统：
控制链采用 policy_runtime_service + robot_client 的闭环执行架构。
mock_task 仅用于UI兜底显示，不参与任何机器人控制。

## 系统定位

本项目用于连接 React/Vite 前端、FastAPI 后端、ACT policy 推理服务和 SO-ARM101 机械臂执行端。系统的核心不是 mock 或仿真控制，而是真实机器人 AI 闭环：

```text
frontend
  -> FastAPI backend
  -> task_control
  -> policy_runtime_service
  -> LeRobot ACT policy inference
  -> robot_client
  -> SO-ARM101 robot execution
```

强制约束：

- `policy_runtime_service` 是唯一 AI 推理入口。
- `robot_client` 是唯一机械臂硬件执行入口。
- `mock_task` 只允许服务 UI fallback 显示，不参与 action/control。
- 前端只发起任务意图和模式选择，不直接控制机器人。

## 苹果成熟度分级控制

前端成熟度选项通过统一字段 `target_maturity` 进入后端和 policy runtime：

| UI 选项 | 后端字段 | Policy input |
| --- | --- | --- |
| 成熟果（红苹果） | `target_maturity: "red"` | `target_maturity="red"` |
| 半成熟果（黄苹果） | `target_maturity: "yellow"` | `target_maturity="yellow"` |

`task_control` 不再使用旧的“只红/多摘/半摘”策略分支。local 和 remote 模式均将同一个 `target_maturity` 传给 `policy_runtime_service`，由推理循环把该字段注入 policy input；`robot_client` 接口保持不变。yellow apple 表示半成熟果控制策略，要求 policy 选择黄苹果目标执行采摘。

## local / remote 模式

local 和 remote 是同一套 AI 控制系统的两种部署方式，不是“真实/模拟”的区别。

local 模式：

```text
backend
  -> policy_runtime_service（本机进程）
  -> robot_client
  -> SO-ARM101
```

remote 模式：

```text
backend
  -> HTTP
  -> Robot PC
  -> policy_runtime_service（远程进程）
  -> robot_client
  -> SO-ARM101
```

## UI 展示链

UI 状态展示与机器人控制链分离：

```text
robot_status + backend_state + optional mock fallback
  -> status_fusion
  -> websocket / HTTP
  -> frontend UI
```

mock fallback 只用于页面兜底显示，例如机器人状态暂不可用时保持 UI 可读；它不会生成动作，也不会进入 `policy_runtime_service -> robot_client` 执行链。

## 主要目录

```text
.
├── README.md
├── README_TEAM.md
├── CHATGPT_README.md
├── launcher.py
├── start.bat
├── 后端/
│   ├── robot_pc_placeholder.py
│   └── apple-picking-backend/
│       ├── README.md
│       ├── REAL_ROBOT_ARCHITECTURE.md
│       ├── PROJECT_CONTEXT.md
│       ├── REQUIREMENTS_DRAFT.md
│       └── app/
│           ├── main.py
│           ├── task_control.py
│           ├── status_fusion.py
│           ├── services/policy_runtime_service.py
│           └── adapters/robot_client.py
└── 前端/
    └── keyon-apple-ui - 前端/
```

## 运行入口

开发联调时可双击根目录 `start.bat`，由 `launcher.py` 启动 FastAPI 后端和 Vite 前端。后端接口文档默认在：

```text
http://127.0.0.1:8000/docs
```
