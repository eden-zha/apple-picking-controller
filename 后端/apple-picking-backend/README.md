# 苹果采摘后端与 Robot PC 控制入口

本项目的主后端只负责接收前端指令、维护任务状态，并通过 HTTP 控制 robot PC。摄像头、训练好的识别/策略模型、SO-ARM101 机械臂控制程序都运行在 robot PC 上。

## 控制边界

主后端不直接读取 USB 摄像头画面。

主后端不直接运行 YOLO 或其他视觉模型。

主后端不直接控制机械臂串口、USB 或 SDK。

主后端只通过 HTTP 调用 robot PC：

```text
POST http://<robot-pc>:8000/robot/start
POST http://<robot-pc>:8000/robot/stop
```

## Robot PC 执行链路

robot PC 上运行 `后端/robot_pc_placeholder.py`，它现在是机器人电脑控制入口。

当 robot PC 收到：

```text
POST /robot/start
```

它会启动本机已经配置好的抓取主程序。这个抓取程序负责：

- 调用 robot PC 上连接的 USB 摄像头
- 加载并运行本机训练好的模型
- 识别苹果
- 驱动 SO-ARM101 机械臂执行抓取

当 robot PC 收到：

```text
POST /robot/stop
```

它会停止正在运行的抓取程序，并由抓取程序释放摄像头、模型推理进程和机械臂资源。

## Robot PC 环境变量

推荐配置：

```text
ROBOT_GRASP_START_CMD=python D:\robot\apple_grasp\run_grasp.py
ROBOT_GRASP_WORKDIR=D:\robot\apple_grasp
ROBOT_GRASP_STOP_CMD=python D:\robot\apple_grasp\stop_grasp.py
```

`ROBOT_GRASP_START_CMD` 指向 robot PC 本地的真实抓取程序。该程序内部可以运行 YOLO、LeRobot policy、摄像头采集和机械臂控制逻辑。

如果没有配置 `ROBOT_GRASP_START_CMD`，服务会保留原有占位 fallback：

```text
POLICY_SERVER_START_CMD=...
ROBOT_CLIENT_START_CMD=...
POLICY_RUNTIME_START_CMD=...
```

如果这些旧命令也没有配置，`/robot/start` 会进入 placeholder fallback，只用于联调 HTTP 链路，不代表真实机械臂已经运动。

## 主后端 remote 模式

主后端 remote 模式只负责调度 robot PC：

```text
frontend
  -> FastAPI 主后端
  -> HTTP /robot/start
  -> robot PC 抓取程序
  -> USB 摄像头 + 训练模型 + SO-ARM101
```

停止链路：

```text
frontend
  -> FastAPI 主后端
  -> HTTP /robot/stop
  -> robot PC 停止抓取程序并释放资源
```

## 后续状态回传

当前主链路只要求 start/stop。后续如果前端需要展示识别数量、抓取数量、相机帧率、机械臂状态或异常信息，可以在 robot PC 服务中增加：

```text
GET /robot/status
WebSocket /robot/status/ws
```

然后由主后端转发或融合这些状态给前端。

## 主后端接口

前端接口保持不变：

```text
POST /start_task
POST /stop
GET /status
```

主后端内部根据 local/remote 配置决定是否调用 robot PC。前端不需要知道摄像头、模型或机械臂程序运行在哪里。

