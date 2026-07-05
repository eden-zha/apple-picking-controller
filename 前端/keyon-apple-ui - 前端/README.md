# 前端说明

这是苹果采摘机器人系统的 React/Vite 前端。前端负责展示状态、发送任务意图和处理用户交互，不直接连接机械臂、摄像头或 LeRobot。

当前控制链路：

```text
前端
  -> FastAPI 后端
  -> task_control
  -> lerobot_record_service
  -> run_lerobot_*.bat
  -> python -m lerobot.record
```

## 前端职责

- 选择目标成熟度：成熟果 `red` 或半成熟果 `yellow`。
- 发送开始、停止、复位等任务指令。
- 显示任务状态、机器人状态、policy 状态、视觉状态和运行日志。
- 通过 WebSocket 接收后端实时状态。
- 在 LeRobot 校准确认时显示弹窗，并把用户选择发送给后端。

前端不生成机械臂 action，不绕过后端控制硬件。

## 安装和运行

```bash
npm install
npm run dev
```

默认开发地址：

```text
http://localhost:5173/
```

构建检查：

```bash
npm run build
```

本地预览构建产物：

```bash
npm run preview
```

## 主要文件

```text
src/App.jsx       # 主 UI 和交互逻辑
src/api.js        # 后端 API/WebSocket 封装
src/App.css       # 页面样式
src/index.css     # 全局样式
public/           # logo/icon 等静态资源
package.json      # 依赖和脚本
vite.config.js    # Vite 配置
```

## 后端 API

前端通过 `src/api.js` 调用后端：

```text
POST /set_target_apple
POST /start_task
POST /stop
POST /reset
GET  /status
GET  /logs
GET  /policy/status
POST /policy/calibration/continue
GET  /vision/status
WebSocket /ws/status
WebSocket /ws/vision
```

## 状态显示

“机器人状态”当前显示逻辑：

- 如果 `policy_status.running` 为 true，显示“作业中”。
- 否则如果 `robot_status.running` 为 true，显示“运行中”。
- 否则显示“未运行”。

右上角时间来自运行前端的设备本地时间，显示到分钟。

## 运行日志

顶部“运行日志”入口可悬停预览，也可点击固定。该入口已适配不同窗口宽度。

## 校准确认弹窗

当后端在 LeRobot 输出中检测到校准确认提示时，会通过 `policy_status.pending_interaction` 通知前端。前端弹窗提供：

- 继续：调用 `POST /policy/calibration/continue`。
- 停止：调用停止任务流程。

## UI 数据说明

电量、天气、果筐容量、区域、路线等页面元素如果没有来自后端真实状态源，只作为 UI 展示或占位，不代表控制链已经执行对应动作。
