# 苹果采摘系统：团队使用说明

## 项目说明

本项目包含：

- React/Vite 前端 UI：位于 `前端` 目录下，启动器会自动选择包含 `package.json` / `index.html` 且包含 local / remote UI 的当前前端项目
- FastAPI 后端：`后端\apple-picking-backend`
- Windows 一键启动脚本：`start.bat`

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

3. 返回项目根目录，进入当前前端项目目录并安装前端依赖。

   当前前端项目目录应满足：包含 `package.json`，并且是实际包含 local / remote UI 的前端目录。不要进入 `dist`、`src`、`node_modules` 或备份目录。

   ```bat
   cd /d "..\..\前端\<当前前端项目目录>"
   npm.cmd install
   ```

4. 返回项目根目录，双击 `start.bat`。脚本会自动调用 `launcher.py`，启动后端和前端，并自动打开 <http://localhost:5173>。

`launcher.py` 会以自身所在目录作为项目根目录，不依赖 v1.0 / v2.0 等版本号目录，也不依赖固定前端文件夹名。后端固定解析为 `后端\apple-picking-backend`；前端会在 `前端` 目录下自动查找包含 `package.json` 或 `index.html` 的项目，并优先选择包含 local / remote UI 的那个前端。

脚本会自动优先使用后端目录中的 `.venv`。如果没有 `.venv`，则继续尝试后端目录的 `venv`、项目根目录的 `venv`，最后使用当前 Python 环境。现有的本机 `venv` 不是团队运行所必需的内容。

## 日常运行

1. 双击项目根目录的 `start.bat`。
2. 等待启动窗口显示 `[INFO] Startup complete. You can use the web page now.`。
3. 浏览器会自动打开前端页面：<http://localhost:5173>。如果浏览器没有自动打开，可手动访问该地址。
4. 后端接口文档：<http://127.0.0.1:8000/docs>。

启动日志会写入 `logs\backend.log` 和 `logs\frontend.log`。如果 8000 或 5173 端口已被占用，启动器会提示对应服务可能已经在运行。关闭对应的服务进程即可停止服务。

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
- 提示前端依赖未安装：进入 `前端` 目录下实际包含 `package.json` 的当前前端项目，执行一次 `npm.cmd install`。启动脚本不会自动重复安装依赖。
- 找不到 `python`：安装 Python 3.10+，安装时勾选“Add Python to PATH”，或在后端目录创建 `.venv`。
- 找不到 `npm.cmd`：安装 Node.js LTS 后重新打开命令行窗口。
- 前端无法打开：先查看 `logs\frontend.log`。如果 5173 端口已被占用，请关闭占用该端口的旧前端服务后重新双击 `start.bat`。

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
