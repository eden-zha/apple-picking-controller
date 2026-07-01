import os
import subprocess
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException


app = FastAPI(
    title="Robot PC Control Service",
    description="Robot PC side starter for robot_client and policy_server.",
)

_policy_process: Optional[subprocess.Popen] = None
_robot_process: Optional[subprocess.Popen] = None
_policy_runtime_process: Optional[subprocess.Popen] = None


def _start_process(env_name: str) -> subprocess.Popen:
    command = os.getenv(env_name)
    if not command:
        raise RuntimeError(f"{env_name} is not configured.")
    return subprocess.Popen(command, shell=True)


@app.get("/health")
async def health():
    return {
        "ok": True,
        "service": "robot_pc_control",
        "time": datetime.now().isoformat(timespec="seconds"),
    }


@app.post("/robot/start")
async def robot_start():
    global _policy_process, _robot_process
    try:
        if _policy_process is None or _policy_process.poll() is not None:
            _policy_process = _start_process("POLICY_SERVER_START_CMD")
        if _robot_process is None or _robot_process.poll() is not None:
            _robot_process = _start_process("ROBOT_CLIENT_START_CMD")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "success": True,
        "message": "robot_client and policy_server start commands accepted",
        "time": datetime.now().isoformat(timespec="seconds"),
    }


@app.post("/policy/start")
async def policy_start():
    global _policy_runtime_process
    try:
        if _policy_runtime_process is None or _policy_runtime_process.poll() is not None:
            _policy_runtime_process = _start_process("POLICY_RUNTIME_START_CMD")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "success": True,
        "message": "policy_runtime_service start command accepted",
        "time": datetime.now().isoformat(timespec="seconds"),
    }


@app.post("/policy/stop")
async def policy_stop():
    global _policy_runtime_process
    if _policy_runtime_process is not None and _policy_runtime_process.poll() is None:
        _policy_runtime_process.terminate()
    return {
        "success": True,
        "message": "policy_runtime_service stop command sent",
        "time": datetime.now().isoformat(timespec="seconds"),
    }


@app.get("/policy/status")
async def policy_status():
    return {
        "running": _policy_runtime_process is not None and _policy_runtime_process.poll() is None,
        "loaded": _policy_runtime_process is not None and _policy_runtime_process.poll() is None,
        "paused": False,
        "model_path": None,
        "inference_hz": 0,
        "loop_hz": 0,
        "last_error": None,
        "source": "robot_pc_process_launcher",
    }


@app.post("/robot/stop")
async def robot_stop():
    global _policy_process, _robot_process
    for process in (_robot_process, _policy_process):
        if process is not None and process.poll() is None:
            process.terminate()
    return {
        "success": True,
        "message": "robot_client and policy_server stop commands sent",
        "time": datetime.now().isoformat(timespec="seconds"),
    }


@app.get("/robot/status")
async def robot_status():
    return {
        "running": _robot_process is not None and _robot_process.poll() is None,
        "fps": 0,
        "step": 0,
        "time": datetime.now().isoformat(timespec="seconds"),
    }


@app.post("/robot/action")
async def robot_action():
    raise HTTPException(
        status_code=501,
        detail="This launcher does not execute actions. Run app.main on the robot PC or configure a real robot_client action endpoint.",
    )
