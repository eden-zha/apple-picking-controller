# 后端说明

这是苹果采摘控制系统的 FastAPI 后端。后端负责接收前端指令、维护任务状态、启动/停止 LeRobot 外部进程，并通过 HTTP/WebSocket 向前端返回状态。

当前主链路：

```text
前端
  -> FastAPI 后端
  -> app/task_control.py
  -> app/services/lerobot_record_service.py
  -> run_lerobot_yellow.bat / run_lerobot_red.bat
  -> python -m lerobot.record
```

后端负责启动和停止 LeRobot record 外部进程。机械臂、摄像头和 policy 由 LeRobot record 进程负责。

## 主要文件

```text
app/main.py                         # FastAPI 路由和 WebSocket
app/task_control.py                 # 任务开始/停止编排
app/status_fusion.py                # UI 状态融合
app/services/lerobot_record_service.py
                                    # LeRobot 外部进程启动/停止/状态
app/services/vision_service.py      # OpenCV YOLO 视觉服务代码
run_lerobot_yellow.bat              # yellow policy 启动脚本
run_lerobot_red.bat                 # red policy 启动脚本
logs/lerobot_record.log             # LeRobot stdout/stderr 日志
```

## 启动后端

```bat
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

如果机器上存在多个 Python 环境，应显式使用已配置 LeRobot 的 Python。

接口文档：

```text
http://127.0.0.1:8000/docs
```

## LeRobot 脚本选择

`lerobot_record_service` 按以下优先级选择启动脚本：

1. 如果设置了 `LEROBOT_RECORD_SCRIPT`，执行它指向的 `.bat`。
2. 否则根据 `target_maturity` 选择：
   - `yellow` -> `run_lerobot_yellow.bat`
   - `red` -> `run_lerobot_red.bat`
3. 如果脚本不存在，返回明确错误：

```text
LeRobot record script not found: <path>
```

后端不再 fallback 到代码里写死的长命令。

## Windows 启动方式

Windows 下执行 `.bat` 的方式为：

```text
cmd.exe /d /s /c call <script_path>
```

工作目录为后端目录 `apple-picking-backend`。stdout/stderr 会写入：

```text
logs/lerobot_record.log
```

日志开头会打印 `sys.executable`、`cwd`、脚本路径和实际命令。

## 停止逻辑

`POST /stop` 会调用 `lerobot_record_service.stop()`。Windows 下会终止 LeRobot 进程树，避免只杀掉 `cmd.exe` 而留下真正的 `python -m lerobot.record` 继续占用机械臂 COM 口。

## 校准确认

当 LeRobot 输出校准确认提示时，后端会设置 `policy_status.pending_interaction`，前端弹窗让用户选择继续或停止。

用户点击继续后，前端调用：

```text
POST /policy/calibration/continue
```

后端向 LeRobot 子进程 stdin 写入 Enter。

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

## policy_status 含义

当前 `policy_status` 代表 LeRobot record 外部进程状态：

- `running`: LeRobot 进程仍存在。
- `loaded`: 随 `running` 表示 LeRobot 进程已启动。
- `model_path`: 当前执行的脚本路径。
- `last_error`: 启动或运行阶段记录的错误。
- `pending_interaction`: 校准确认等需要前端响应的交互。
