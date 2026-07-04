import os
import subprocess
from datetime import datetime
from typing import Dict, Optional

from fastapi import FastAPI


app = FastAPI(
    title="Robot PC Control Service",
    description=(
        "HTTP entrypoint on the robot PC. It starts/stops the local trained "
        "vision-policy-arm grasping program; it does not read cameras or run "
        "inference inside this FastAPI process."
    ),
)

_grasp_process: Optional[subprocess.Popen] = None
_policy_process: Optional[subprocess.Popen] = None
_robot_process: Optional[subprocess.Popen] = None
_policy_runtime_process: Optional[subprocess.Popen] = None
_placeholder_running = False
_active_mode = "idle"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _env(name: str) -> Optional[str]:
    value = os.getenv(name)
    if value and value.strip():
        return value.strip()
    return None


def _is_running(process: Optional[subprocess.Popen]) -> bool:
    return process is not None and process.poll() is None


def _process_info(process: Optional[subprocess.Popen]) -> Dict[str, object]:
    return {
        "running": _is_running(process),
        "pid": process.pid if process is not None else None,
    }


def _start_command(command: str, cwd: Optional[str] = None) -> subprocess.Popen:
    return subprocess.Popen(
        command,
        cwd=cwd,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )


def _terminate_process(process: Optional[subprocess.Popen]) -> bool:
    if not _is_running(process):
        return False

    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)
    return True


def _start_grasp_program() -> Optional[subprocess.Popen]:
    command = _env("ROBOT_GRASP_START_CMD") or _env("APPLE_PICKING_GRASP_CMD")
    if command is None:
        return None
    return _start_command(command, cwd=_env("ROBOT_GRASP_WORKDIR"))


def _start_legacy_placeholder() -> str:
    global _policy_process, _robot_process, _placeholder_running

    policy_command = _env("POLICY_SERVER_START_CMD")
    robot_command = _env("ROBOT_CLIENT_START_CMD")

    if policy_command and not _is_running(_policy_process):
        _policy_process = _start_command(policy_command, cwd=_env("POLICY_SERVER_WORKDIR"))
    if robot_command and not _is_running(_robot_process):
        _robot_process = _start_command(robot_command, cwd=_env("ROBOT_CLIENT_WORKDIR"))

    if policy_command or robot_command:
        _placeholder_running = False
        return "legacy placeholder commands accepted"

    _placeholder_running = True
    return "placeholder fallback active: no ROBOT_GRASP_START_CMD configured"


def _stop_grasp_program() -> bool:
    stop_command = _env("ROBOT_GRASP_STOP_CMD") or _env("APPLE_PICKING_STOP_CMD")
    if stop_command:
        subprocess.run(stop_command, shell=True, timeout=10, check=False)
    return _terminate_process(_grasp_process)


@app.get("/health")
async def health():
    return {
        "ok": True,
        "service": "robot_pc_control",
        "mode": _active_mode,
        "time": _now(),
    }


@app.post("/robot/start")
async def robot_start():
    global _active_mode, _grasp_process

    if _is_running(_grasp_process):
        return {
            "success": True,
            "message": "robot grasp program is already running",
            "mode": _active_mode,
            "time": _now(),
        }

    _grasp_process = _start_grasp_program()
    if _grasp_process is not None:
        _active_mode = "grasp_program"
        return {
            "success": True,
            "message": "robot grasp program started on robot PC",
            "mode": _active_mode,
            "pid": _grasp_process.pid,
            "time": _now(),
        }

    fallback_message = _start_legacy_placeholder()
    _active_mode = "placeholder_fallback"
    return {
        "success": True,
        "message": fallback_message,
        "mode": _active_mode,
        "time": _now(),
    }


@app.post("/robot/stop")
async def robot_stop():
    global _active_mode, _placeholder_running

    stopped = {
        "grasp_program": _stop_grasp_program(),
        "policy_runtime": _terminate_process(_policy_runtime_process),
        "robot_client": _terminate_process(_robot_process),
        "policy_server": _terminate_process(_policy_process),
        "placeholder": _placeholder_running,
    }
    _placeholder_running = False
    _active_mode = "idle"

    return {
        "success": True,
        "message": "robot PC grasp program stopped; local camera and arm resources should be released by the child process",
        "stopped": stopped,
        "mode": _active_mode,
        "time": _now(),
    }


@app.get("/robot/status")
async def robot_status():
    return {
        "running": _is_running(_grasp_process)
        or _is_running(_policy_runtime_process)
        or _is_running(_robot_process)
        or _placeholder_running,
        "mode": _active_mode,
        "grasp_program": _process_info(_grasp_process),
        "policy_runtime": _process_info(_policy_runtime_process),
        "robot_client": _process_info(_robot_process),
        "policy_server": _process_info(_policy_process),
        "placeholder": _placeholder_running,
        "time": _now(),
    }


@app.post("/policy/start")
async def policy_start():
    global _active_mode, _policy_runtime_process

    command = _env("POLICY_RUNTIME_START_CMD")
    if command and not _is_running(_policy_runtime_process):
        _policy_runtime_process = _start_command(command, cwd=_env("POLICY_RUNTIME_WORKDIR"))
        _active_mode = "policy_runtime"
        return {
            "success": True,
            "message": "policy_runtime_service start command accepted",
            "mode": _active_mode,
            "pid": _policy_runtime_process.pid,
            "time": _now(),
        }

    return await robot_start()


@app.post("/policy/stop")
async def policy_stop():
    stopped = _terminate_process(_policy_runtime_process)
    return {
        "success": True,
        "message": "policy_runtime_service stop command sent",
        "stopped": stopped,
        "time": _now(),
    }


@app.get("/policy/status")
async def policy_status():
    running = _is_running(_policy_runtime_process) or _is_running(_grasp_process)
    return {
        "running": running,
        "loaded": running,
        "paused": False,
        "model_path": _env("LEROBOT_POLICY_MODEL_PATH") or _env("YOLO_MODEL_PATH"),
        "inference_hz": 0,
        "loop_hz": 0,
        "last_error": None,
        "source": "robot_pc_control_service",
    }


@app.post("/robot/action")
async def robot_action():
    return {
        "success": False,
        "message": (
            "This robot PC entrypoint is start/stop only. The grasp program "
            "started by /robot/start owns camera, model inference, and arm control."
        ),
        "time": _now(),
    }

