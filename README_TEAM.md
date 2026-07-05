# 团队使用说明

这份文档描述当前已经实现并仍在使用的项目运行方式。

当前控制链路：

```text
前端
  -> FastAPI 后端
  -> task_control
  -> lerobot_record_service
  -> run_lerobot_*.bat
  -> python -m lerobot.record
```

LeRobot record 进程负责连接机械臂、摄像头和 policy。后端负责启动/停止该外部进程、维护状态并向前端推送信息。

## 项目组成

- 前端：`前端/keyon-apple-ui - 前端`
- 后端：`后端/apple-picking-backend`
- LeRobot 启动服务：`后端/apple-picking-backend/app/services/lerobot_record_service.py`
- yellow 脚本：`后端/apple-picking-backend/run_lerobot_yellow.bat`
- red 脚本：`后端/apple-picking-backend/run_lerobot_red.bat`

## 环境准备

- 前端需要 Node.js 和 npm。
- 后端需要能运行 FastAPI 的 Python 环境。
- 运行 LeRobot 的 Python 环境必须已经安装并验证 LeRobot、torch、摄像头、机械臂串口和 policy 权重。

不要直接复制其他电脑上的虚拟环境。Python/conda/venv 环境包含本机路径和平台相关依赖，应在实际运行电脑上配置并验证。

## 前端运行

```bat
cd /d "前端\keyon-apple-ui - 前端"
npm.cmd install
npm.cmd run dev
```

构建检查：

```bat
npm.cmd run build
```

## 后端运行

```bat
cd /d "后端\apple-picking-backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

如果机器上有多个 Python 环境，应显式使用已配置 LeRobot 的 Python。

接口文档：

```text
http://127.0.0.1:8000/docs
```

## 开始任务

前端点击开始后：

1. 调用 `POST /start_task`。
2. 后端读取当前 `target_maturity`。
3. `yellow` 启动 `run_lerobot_yellow.bat`。
4. `red` 启动 `run_lerobot_red.bat`。
5. LeRobot record 进程开始连接机械臂、摄像头和 policy。

也可以通过 `LEROBOT_RECORD_SCRIPT` 指定要执行的 `.bat` 脚本。

## 停止任务

前端点击停止后：

1. 调用 `POST /stop`。
2. 后端停止 LeRobot record 外部进程。
3. Windows 下会清理子进程树，避免真实 `python -m lerobot.record` 留在后台继续占用 COM 口。

## 校准确认

当 LeRobot 输出校准确认提示时，后端会通过 `policy_status.pending_interaction` 通知前端。前端弹窗提供：

- 继续：调用 `POST /policy/calibration/continue`，后端向 LeRobot stdin 写入 Enter。
- 停止：调用停止任务流程。

## 日志

LeRobot 外部进程 stdout/stderr 写入：

```text
后端/apple-picking-backend/logs/lerobot_record.log
```

前端顶部“运行日志”用于展示后端任务日志，已适配不同窗口大小。

## 状态显示

前端“机器人状态”显示规则：

- `policy_status.running == true`：显示“作业中”。
- 否则如果 `robot_status.running == true`：显示“运行中”。
- 否则显示“未运行”。

右上角时间来自前端运行设备的本地时间，显示到分钟。
