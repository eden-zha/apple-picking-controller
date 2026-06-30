# 苹果采摘系统：团队使用说明

## 项目说明

本项目包含：

- React/Vite 前端 UI：`前端\keyon-apple-ui - 前端`
- FastAPI 后端：`后端\apple-picking-backend`
- Windows 一键启动脚本：`start_project.bat`

当前版本是“前后端通信与任务状态机联调用原型”，用于验证页面、接口和模拟任务状态流转，不代表已经完成真实硬件闭环。

## 首次使用前的准备

请先安装：

- Python 3.12，或其他 Python 3.10+ 版本
- Node.js LTS（自带 npm）
- 建议安装 VS Code，方便查看和调试项目

不要复制或依赖其他成员电脑上的 `venv`。Python 虚拟环境包含本机路径和平台相关文件，应由每位组员在自己的电脑上创建。

## 首次运行

以下命令均在项目根目录打开终端后执行。

1. 进入后端目录，创建并激活自己的虚拟环境：

   ```bat
   cd /d "后端\apple-picking-backend"
   python -m venv .venv
   .venv\Scripts\activate.bat
   ```

   如果已有可用的 Python 环境，也可以跳过创建虚拟环境。

2. 安装后端依赖：

   ```bat
   python -m pip install -r requirements.txt
   ```

3. 返回项目根目录，进入前端目录并安装前端依赖：

   ```bat
   cd /d "..\..\前端\keyon-apple-ui - 前端"
   npm.cmd install
   ```

4. 返回项目根目录，双击 `start_project.bat`。脚本会分别打开后端和前端两个命令行窗口。

脚本会自动优先使用后端目录中的 `.venv`。如果没有 `.venv`，则使用系统环境中的 `python`。现有的本机 `venv` 不是团队运行所必需的内容。

## 日常运行

1. 双击项目根目录的 `start_project.bat`。
2. 等待前端和后端窗口显示启动完成。
3. 打开前端页面：通常为 <http://localhost:5173>。如果 5173 端口被占用，以前端窗口输出的 `Local` 地址为准。
4. 后端接口文档：<http://127.0.0.1:8000/docs>。

关闭对应的命令行窗口即可停止服务。

## 当前真实可用功能

- “只摘精品果”对应后端 `target_mode = red_only`，即只采红苹果
- “尽量多摘”对应后端 `target_mode = red_green`，即红苹果和绿苹果都采
- 开始采摘
- 紧急停止
- 查询任务状态和日志

## 当前暂未接入真实硬件的功能

- A/B/C 区域选择
- 路线模式
- 真实小车导航
- 真实机械臂控制
- 真实电量、天气、果筐容量、剩余时间等传感器数据

这些页面元素或展示数据不应理解为真实硬件已经接入。

## 如何验证前后端已经联通

1. 确认后端窗口显示 Uvicorn 正在 `http://127.0.0.1:8000` 运行，并能打开 <http://127.0.0.1:8000/docs>。
2. 打开前端页面，选择“只摘精品果”或“尽量多摘”，再点击开始采摘。
3. 页面能够显示后端返回的任务状态、进度或日志，且没有“接口请求失败，请检查后端是否运行在 8000 端口”的提示，即说明前后端通信正常。
4. 可在页面中执行紧急停止，并观察状态和日志是否随之更新。

也可以直接访问 <http://127.0.0.1:8000/status>，确认后端返回 JSON 状态数据。

## 常见问题

- 提示后端依赖未安装：进入后端目录并在脚本将使用的 Python 环境中执行 `python -m pip install -r requirements.txt`。
- 提示前端依赖未安装：进入前端目录执行一次 `npm.cmd install`。启动脚本不会自动重复安装依赖。
- 找不到 `python`：安装 Python 3.10+，安装时勾选“Add Python to PATH”，或在后端目录创建 `.venv`。
- 找不到 `npm.cmd`：安装 Node.js LTS 后重新打开命令行窗口。
- 前端不是 5173 端口：Vite 会在端口被占用时选择其他端口，请使用前端窗口输出的 `Local` 地址。
## 运行模式说明

### local模式

- 不连接机械臂
- 使用本地mock执行
- 用于开发与调试

### remote模式

- 连接机械臂电脑
- 通过HTTP调用 robot server
- 默认模式

## 环境变量

机器人电脑地址可通过以下环境变量配置：

- `ROBOT_PC_IP`：机器人电脑 IP，后端会请求 `http://<ROBOT_PC_IP>:8000/robot/start` 和 `http://<ROBOT_PC_IP>:8000/robot/stop`
- `ROBOT_BASE_URL`：完整 robot server 地址，例如 `http://192.168.1.20:8000`

优先级：`ROBOT_PC_IP` -> `ROBOT_BASE_URL` -> `http://127.0.0.1:8000`。

## UI说明

前端页面顶部可切换 local / remote 模式。点击开始采摘或紧急停止时，前端会在请求体中携带当前模式：

```json
{
  "mode": "local"
}
```

或：

```json
{
  "mode": "remote"
}
```

如果缺少 `mode`，后端默认按 `remote` 处理；remote 请求失败时会自动 fallback 到本地 mock / 本地 stop。
