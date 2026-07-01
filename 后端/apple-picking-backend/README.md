# 苹果采摘后端：真实机器人 AI 控制系统

本系统为真实机器人AI控制系统：
控制链采用 policy_runtime_service + robot_client 的闭环执行架构。
mock_task 仅用于UI兜底显示，不参与任何机器人控制。

## 后端定位

本目录是 FastAPI 后端。它接收前端任务请求，维护任务状态，并通过 `task_control` 进入真实 AI 控制闭环：

```text
frontend
  -> FastAPI backend
  -> task_control
  -> policy_runtime_service
  -> LeRobot ACT policy inference
  -> robot_client
  -> SO-ARM101 robot execution
```

关键边界：

- `policy_runtime_service` 是唯一 AI 推理入口。
- `robot_client` 是唯一机械臂执行入口。
- `mock_task` 不参与控制链，只能作为 UI fallback 展示数据。
- 前端不能直接控制机器人，只能通过后端 API 发起任务意图。

## 接口列表

### `GET /status`

返回融合后的系统状态，来源包括后端任务状态、机器人状态、policy 状态和可选 UI fallback。

字段语义：

- `state` / `task_state`：后端任务状态，例如 `IDLE`、`RUNNING`、`DONE`、`STOPPED`、`ERROR`。
- `robot_status`：来自 `robot_client` 或 `status_fusion` 的机器人状态。
- `policy_status`：来自 `policy_runtime_service` 的推理状态。
- `logs`：最近运行日志。

如果状态中出现 `mock_fallback`，只表示展示层兜底。

### `POST /set_target_apple`

设置本轮任务目标采摘模式。推荐使用 `target_mode`：

```json
{
  "target_mode": "red_only"
}
```

或：

```json
{
  "target_mode": "red_green"
}
```

`target_color` 仅为旧字段兼容，后续不推荐新前端继续使用。

### `POST /start_task`

启动采摘任务。请求体可传：

```json
{ "mode": "local" }
```

或：

```json
{ "mode": "remote" }
```

无论 local 还是 remote，最终都必须进入真实 policy + robot_client 执行闭环。

### `POST /stop`

停止正在运行的任务。停止请求由 `task_control` 传递到当前部署方式对应的 policy runtime / robot client，不能由前端直接控制硬件。

### `POST /reset`

复位后端任务状态。复位不代表机器人硬件已完成物理复位；真实硬件状态必须以 `robot_client` 返回为准。

### `GET /logs`

查询最近运行日志。

## local / remote 定义

### local 模式

```text
backend
  -> policy_runtime_service（本机进程）
  -> robot_client
  -> SO-ARM101
```

local 代表本机部署真实 AI 控制闭环。

### remote 模式

```text
backend
  -> HTTP
  -> Robot PC
  -> policy_runtime_service（远程进程）
  -> robot_client
  -> SO-ARM101
```

remote 代表 policy runtime 和 robot client 部署在 Robot PC。Robot PC 必须承载远程 `policy_runtime_service`。

## UI 展示链

```text
robot_status + backend_state + optional mock fallback
  -> status_fusion
  -> websocket / HTTP
  -> frontend UI
```

`status_fusion` 负责把控制链状态整理给 UI。UI 展示链不反向改变机器人控制逻辑。

## 文件结构

```text
app/
├── main.py
├── models.py
├── state_manager.py
├── task_control.py
├── status_fusion.py
├── mock_task.py
├── services/
│   └── policy_runtime_service.py
└── adapters/
    └── robot_client.py
requirements.txt
README.md
REAL_ROBOT_ARCHITECTURE.md
PROJECT_CONTEXT.md
REQUIREMENTS_DRAFT.md
```

## 安装依赖

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

macOS / Linux：

```bash
source .venv/bin/activate
```

## 启动服务

```bash
uvicorn app.main:app --reload
```

默认服务地址：

```text
http://127.0.0.1:8000
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

## 配置项

```text
LEROBOT_POLICY_MODEL_PATH=D:\path\to\outputs\train\...\pretrained_model
POLICY_INFERENCE_HZ=20
POLICY_RUNTIME_REMOTE_URL=http://<robot-pc-host>:8000
LOCAL_ROBOT_CLIENT_URL=http://127.0.0.1:<robot-service-port>
SO_ARM101_ROBOT_FACTORY=your_module:create_robot
```

## 快速测试

```bash
curl http://127.0.0.1:8000/status
curl -X POST http://127.0.0.1:8000/set_target_apple ^
  -H "Content-Type: application/json" ^
  -d "{\"target_mode\":\"red_only\"}"
curl -X POST http://127.0.0.1:8000/start_task ^
  -H "Content-Type: application/json" ^
  -d "{\"mode\":\"local\"}"
curl -X POST http://127.0.0.1:8000/stop ^
  -H "Content-Type: application/json" ^
  -d "{\"mode\":\"local\"}"
```
