# 苹果采摘装置后端通信原型

这是一个基础可运行、后续可扩展的 FastAPI 后端原型，用于学生项目阶段的 UI 和后端通信演示。

当前版本只实现 UI 联调用的模拟状态机，不连接真实机械臂、小车、ROS、TCP 或数据库。当前真实功能只支持两种目标采摘模式：

* `red_only`：只采红苹果，对应前端按钮“只摘精品果”。
* `red_green`：红苹果和绿苹果都采，对应前端按钮“尽量多摘”。

前端按钮“红一点也摘”暂未接入，当前后端没有对应模式。

## 当前可用功能

* 设置目标采摘模式：`red_only` 或 `red_green`。
* 启动模拟采摘任务。
* 停止任务。
* 复位系统。
* 查询状态和日志。

## 暂未接入功能

* 区域选择。
* 路线选择。
* 成熟度多档策略。
* 真实小车导航。
* 真实机械臂控制。
* 真实果筐容量。
* 真实天气。
* 真实电量。
* 真实剩余时间。

如果后续接口中出现 `demo_stats`，必须明确包含 `is_mock_data: true`，表示这些数据只用于演示，不是真实传感器或业务数据。

## 接口列表

### `GET /status`

查询当前模拟状态。

返回示例：

```json
{
  "state": "IDLE",
  "progress": 0,
  "message": "等待任务开始。",
  "target_mode": "red_only",
  "current_step": "等待开始",
  "logs": []
}
```

字段说明：

* `state`：当前状态，可能为 `IDLE`、`RUNNING`、`DONE`、`STOPPED`、`ERROR`。
* `progress`：当前模拟任务进度，范围 `0-100`。
* `message`：当前状态提示。
* `target_mode`：当前选择的目标采摘模式，可能为 `red_only`、`red_green` 或 `null`。
* `current_step`：当前模拟步骤。
* `logs`：最近运行日志，最多保留 50 条。

### `POST /set_target_apple`

设置本轮任务目标采摘模式。推荐使用 `target_mode`。

请求体：

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

`target_mode` 可选值：

* `red_only`：只采红苹果，对应前端按钮“只摘精品果”。
* `red_green`：红苹果和绿苹果都采，对应前端按钮“尽量多摘”。

兼容旧版本请求：

```json
{
  "target_color": "red"
}
```

旧版 `target_color: "red"` 会被映射为 `target_mode: "red_only"`。不再推荐前端使用 `target_color`。

该接口只保存当前选择并写入日志，不实现区域选择、路线选择、成熟度多档策略、真实果筐容量、真实天气、真实电量或真实剩余时间。

### `POST /start_task`

启动模拟采摘任务。需要先通过 `POST /set_target_apple` 选择目标采摘模式。仅 `IDLE` 状态可以启动。

### `POST /stop`

停止正在运行的模拟任务。停止后状态变为 `STOPPED`，后台模拟进度不再继续更新。

### `POST /reset`

复位系统到 `IDLE`，进度恢复为 `0`，当前模拟步骤恢复为等待开始。复位不会清空当前已选择的 `target_mode`。

### `GET /logs`

查询最近运行日志。

## 状态设计

当前使用简单状态：

* `IDLE`：空闲，等待开始。
* `RUNNING`：任务运行中。
* `DONE`：任务完成。
* `STOPPED`：任务停止。
* `ERROR`：异常。

当前模拟任务流程为：

```text
IDLE -> RUNNING -> DONE
```

`RUNNING` 期间进度按 `0、20、40、60、80、100` 更新，每隔 1 秒更新一次。调用 `POST /stop` 后，后台模拟任务会停止，不会继续变成 `DONE`。

当前模拟步骤只用于 UI 联调展示，不代表真实机械臂、小车、路径或传感器状态。

## CORS

后端已允许以下前端开发地址跨域访问：

```text
http://localhost:5173
http://127.0.0.1:5173
```

## 安装依赖

需要 Python 3.8 或更高版本。建议使用虚拟环境：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

如果在 macOS 或 Linux 上运行，激活命令通常是：

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

## 快速测试

查询状态：

```bash
curl http://127.0.0.1:8000/status
```

设置“只摘精品果”：

```bash
curl -X POST http://127.0.0.1:8000/set_target_apple ^
  -H "Content-Type: application/json" ^
  -d "{\"target_mode\":\"red_only\"}"
```

设置“尽量多摘”：

```bash
curl -X POST http://127.0.0.1:8000/set_target_apple ^
  -H "Content-Type: application/json" ^
  -d "{\"target_mode\":\"red_green\"}"
```

旧版兼容请求：

```bash
curl -X POST http://127.0.0.1:8000/set_target_apple ^
  -H "Content-Type: application/json" ^
  -d "{\"target_color\":\"red\"}"
```

启动任务：

```bash
curl -X POST http://127.0.0.1:8000/start_task
```

查看进度：

```bash
curl http://127.0.0.1:8000/status
```

停止任务：

```bash
curl -X POST http://127.0.0.1:8000/stop
```

复位系统：

```bash
curl -X POST http://127.0.0.1:8000/reset
```

查看日志：

```bash
curl http://127.0.0.1:8000/logs
```

## 前端调用建议

前端页面应只展示当前后端真实可解释的控制项：目标采摘模式、启动、停止、复位、状态、日志。

示例：

```ts
await fetch("http://127.0.0.1:8000/set_target_apple", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ target_mode: "red_only" }),
});

await fetch("http://127.0.0.1:8000/start_task", {
  method: "POST",
});

const status = await fetch("http://127.0.0.1:8000/status").then((res) => res.json());
```

前端不要向后端请求或展示 `area`、`route_mode`、`battery`、`weather`、`basket_percent`、`estimated_remaining_minutes` 等真实数据字段；当前后端不提供这些真实能力。

## 文件结构

```text
app/
├── main.py
├── models.py
├── state_manager.py
└── mock_task.py
requirements.txt
README.md
PROJECT_CONTEXT.md
REQUIREMENTS_DRAFT.md
```

## 后续扩展方向

后续可以根据真实设备和算法接入情况逐步扩展：

* 将模拟任务替换为真实视觉识别结果。
* 在确认真实通信协议后，新增真实小车控制适配模块。
* 在确认真实通信协议后，新增真实机械臂控制适配模块。
* 在确认有真实数据来源后，再增加区域、路线、果筐容量、电量、天气、剩余时间等字段。
