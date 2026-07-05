# 苹果采摘控制系统

本项目包含 React/Vite 前端和 FastAPI 后端，用于启动、停止和监控苹果采摘机械臂任务。

当前已经落地的主控制链路是：

```text
前端
  -> FastAPI 后端
  -> task_control
  -> lerobot_record_service
  -> run_lerobot_yellow.bat / run_lerobot_red.bat
  -> python -m lerobot.record
```

LeRobot record 进程内部负责连接机械臂、摄像头和 policy。后端负责启动和停止该外部进程，并维护前端需要的任务状态。

## 当前功能

- 选择目标成熟度：`red` / `yellow`。
- 点击开始任务后，根据目标成熟度启动对应 LeRobot record 脚本。
- 点击停止后，终止 LeRobot 外部进程并释放硬件资源。
- LeRobot 运行日志写入 `后端/apple-picking-backend/logs/lerobot_record.log`。
- 校准确认提示由后端监听，前端弹窗让用户选择继续或停止。
- 前端通过 HTTP/WebSocket 展示任务状态、policy 状态、运行日志和视觉状态。
- 前端“机器人状态”在 LeRobot 进程存在时显示“作业中”。
- 前端右上角时间使用运行前端设备的本地时间，显示到分钟。

## 目标成熟度与脚本

| target_maturity | 执行脚本 |
| --- | --- |
| `yellow` | `后端/apple-picking-backend/run_lerobot_yellow.bat` |
| `red` | `后端/apple-picking-backend/run_lerobot_red.bat` |

如果设置了环境变量 `LEROBOT_RECORD_SCRIPT`，后端会优先执行该脚本。否则根据 `target_maturity` 自动选择脚本。

## 主要目录

```text
.
├── README.md
├── README_TEAM.md
├── launcher.py
├── start.bat
├── 前端/
│   └── keyon-apple-ui - 前端/
└── 后端/
    └── apple-picking-backend/
        ├── app/main.py
        ├── app/task_control.py
        ├── app/services/lerobot_record_service.py
        ├── app/services/vision_service.py
        ├── run_lerobot_yellow.bat
        └── run_lerobot_red.bat
```

## 运行入口

开发联调时可以使用根目录 `start.bat`，由 `launcher.py` 启动后端和前端。

后端接口文档：

```text
http://127.0.0.1:8000/docs
```

前端开发地址：

```text
http://localhost:5173/
```

## 常用接口

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
