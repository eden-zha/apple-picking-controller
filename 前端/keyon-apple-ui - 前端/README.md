# 苹果采摘前端 UI

本系统为真实机器人AI控制系统：
控制链采用 policy_runtime_service + robot_client 的闭环执行架构。
mock_task 仅用于UI兜底显示，不参与任何机器人控制。

## 前端定位

本前端是 SO-ARM101 苹果采摘系统的操作界面。前端只负责：

- 展示任务状态、机器人状态、policy 状态和运行日志。
- 发送目标采摘模式、开始、停止、复位等任务意图。
- 通过 HTTP / WebSocket 接收后端融合状态。

前端不直接控制机器人，不生成机械臂 action，不绕过后端调用硬件。

## 真实控制链

```text
frontend
  -> FastAPI backend
  -> task_control
  -> policy_runtime_service
  -> LeRobot ACT policy inference
  -> robot_client
  -> SO-ARM101 robot execution
```

## UI 展示链

```text
robot_status + backend_state + optional mock fallback
  -> status_fusion
  -> websocket / HTTP
  -> frontend UI
```

mock fallback 只用于页面展示兜底，不参与 action/control。

## local / remote 模式

前端可以把当前模式传给后端：

```json
{ "mode": "local" }
```

或：

```json
{ "mode": "remote" }
```

local：

```text
backend -> policy_runtime_service（本机进程） -> robot_client -> SO-ARM101
```

remote：

```text
backend -> HTTP -> Robot PC -> policy_runtime_service（远程进程） -> robot_client -> SO-ARM101
```

local 和 remote 都必须进入真实 AI 控制闭环，区别只在部署位置。

## 安装和运行

第一次运行：

```bash
npm install
npm run dev
```

默认开发地址：

```text
http://localhost:5173/
```

打包预览：

```bash
npm run build
npm run preview
```

## 主要文件

```text
src/App.jsx       # 主 UI 和交互逻辑
src/api.js        # 后端 API 封装
src/App.css       # 页面样式
src/index.css     # 全局样式
public/           # logo/icon 等静态资源
package.json      # 依赖和脚本
vite.config.js    # Vite 配置
```

## 后端 API 调用

前端通过 `src/api.js` 调用后端：

- `setTargetMaturity(targetMaturity)` -> `POST /set_target_apple`，请求体为 `{ "target_maturity": "red" | "yellow" }`
- `startTask(mode)` -> `POST /start_task`
- `stopTask(mode)` -> `POST /stop`
- `resetTask()` -> `POST /reset`
- `getStatus()` -> `GET /status`
- `getLogs()` -> `GET /logs`

## UI 数据说明

电量、天气、果筐容量、剩余时间、区域、路线等字段如果没有来自真实 `robot_status` 或后端状态源，只能作为 UI fallback 或展示占位。它们不得被解释为真实控制链已经执行对应动作。
