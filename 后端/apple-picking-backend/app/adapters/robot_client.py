import asyncio
import importlib
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

import requests


DEFAULT_TIMEOUT_SECONDS = 5


@dataclass
class RobotCommandResult:
    success: bool
    message: str
    url: Optional[str] = None


@dataclass
class RawRobotState:
    is_running: bool
    fps: float
    step_count: int
    observation: Optional[Any] = None
    current_action: Optional[Any] = None
    latency: Optional[float] = None


_direct_robot = None


def _env(name: str) -> Optional[str]:
    value = os.getenv(name)
    if value and value.strip():
        return value.strip()
    return None


def _base_url(local: bool) -> Optional[str]:
    if local:
        return _env("LOCAL_ROBOT_CLIENT_URL") or _env("ROBOT_CLIENT_URL")

    if _env("ROBOT_PC_BASE_URL"):
        return _env("ROBOT_PC_BASE_URL").rstrip("/")

    robot_pc_ip = _env("ROBOT_PC_IP")
    if robot_pc_ip:
        return f"http://{robot_pc_ip}:8000"

    return _env("ROBOT_CLIENT_URL")


def _require_base_url(local: bool) -> str:
    base_url = _base_url(local)
    if not base_url:
        mode = "local" if local else "remote"
        raise RuntimeError(
            f"{mode} robot endpoint is not configured. "
            "Set LOCAL_ROBOT_CLIENT_URL, ROBOT_CLIENT_URL, ROBOT_PC_BASE_URL, or ROBOT_PC_IP."
        )
    return base_url.rstrip("/")


def _post_json(url: str, payload: Optional[dict] = None) -> dict:
    response = requests.post(url, json=payload or {}, timeout=DEFAULT_TIMEOUT_SECONDS)
    response.raise_for_status()
    if response.content:
        return response.json()
    return {}


def _get_json(url: str) -> dict:
    response = requests.get(url, timeout=DEFAULT_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


def _command_endpoint(base_url: str, command: str) -> str:
    return f"{base_url}/robot/{command}"


def _status_endpoint(base_url: str) -> str:
    return f"{base_url}/robot/status"


def _action_endpoint(base_url: str) -> str:
    return f"{base_url}/robot/action"


def _coerce_robot_state(payload: dict, latency: float) -> RawRobotState:
    return RawRobotState(
        is_running=bool(payload.get("is_running", payload.get("running", False))),
        fps=float(payload.get("fps", 0) or 0),
        step_count=int(payload.get("step_count", payload.get("step", 0)) or 0),
        observation=payload.get("observation"),
        current_action=payload.get("current_action"),
        latency=latency,
    )


def _load_direct_robot() -> Any:
    global _direct_robot
    if _direct_robot is not None:
        return _direct_robot

    factory_path = _env("SO_ARM101_ROBOT_FACTORY")
    if not factory_path:
        raise RuntimeError(
            "No robot HTTP endpoint configured and SO_ARM101_ROBOT_FACTORY is not set."
        )

    module_name, function_name = factory_path.rsplit(":", 1)
    factory = getattr(importlib.import_module(module_name), function_name)
    _direct_robot = factory()
    if hasattr(_direct_robot, "connect"):
        _direct_robot.connect()
    return _direct_robot


def _direct_get_state() -> RawRobotState:
    robot = _load_direct_robot()
    observation = None
    if hasattr(robot, "get_observation"):
        observation = robot.get_observation()
    elif hasattr(robot, "capture_observation"):
        observation = robot.capture_observation()

    return RawRobotState(
        is_running=True,
        fps=0,
        step_count=0,
        observation=observation,
        current_action=None,
        latency=None,
    )


def _direct_send_action(action: Any) -> None:
    robot = _load_direct_robot()
    if hasattr(robot, "send_action"):
        robot.send_action(action)
        return
    if hasattr(robot, "set_action"):
        robot.set_action(action)
        return
    raise RuntimeError("Configured SO-ARM101 robot object has no send_action/action API.")


async def start(local: bool = True) -> RobotCommandResult:
    if local and _base_url(local) is None:
        try:
            await asyncio.to_thread(_load_direct_robot)
        except Exception as exc:
            return RobotCommandResult(False, f"local SO-ARM101 start failed: {exc}")
        return RobotCommandResult(True, "local SO-ARM101 robot connected")
    return await _send_robot_command("start", local=local)


async def stop(local: bool = True) -> RobotCommandResult:
    if local and _base_url(local) is None:
        try:
            robot = _load_direct_robot()
            if hasattr(robot, "disconnect"):
                await asyncio.to_thread(robot.disconnect)
        except Exception as exc:
            return RobotCommandResult(False, f"local SO-ARM101 stop failed: {exc}")
        return RobotCommandResult(True, "local SO-ARM101 robot stopped")
    return await _send_robot_command("stop", local=local)


async def _send_robot_command(command: str, local: bool) -> RobotCommandResult:
    try:
        base_url = _require_base_url(local)
        url = _command_endpoint(base_url, command)
        payload = await asyncio.to_thread(_post_json, url)
    except Exception as exc:
        mode = "local" if local else "remote"
        return RobotCommandResult(
            success=False,
            message=f"{mode} robot_client {command} failed: {exc}",
        )

    message = payload.get("message") or f"robot_client {command} accepted"
    return RobotCommandResult(success=True, message=message, url=url)


async def send_action(action: Any, local: bool = True) -> RobotCommandResult:
    if local and _base_url(local) is None:
        try:
            await asyncio.to_thread(_direct_send_action, action)
        except Exception as exc:
            return RobotCommandResult(False, f"local SO-ARM101 action failed: {exc}")
        return RobotCommandResult(True, "local SO-ARM101 action sent")

    try:
        base_url = _require_base_url(local)
        url = _action_endpoint(base_url)
        payload = await asyncio.to_thread(_post_json, url, {"action": action})
    except Exception as exc:
        mode = "local" if local else "remote"
        return RobotCommandResult(False, f"{mode} robot action failed: {exc}")

    message = payload.get("message") or "robot action accepted"
    return RobotCommandResult(True, message, url)


async def get_state(local: bool = True) -> Optional[RawRobotState]:
    if local and _base_url(local) is None:
        started_at = time.perf_counter()
        try:
            state = await asyncio.to_thread(_direct_get_state)
        except Exception:
            return None
        state.latency = round((time.perf_counter() - started_at) * 1000, 2)
        return state

    try:
        base_url = _require_base_url(local)
        url = _status_endpoint(base_url)
    except Exception:
        return None

    started_at = time.perf_counter()
    try:
        payload = await asyncio.to_thread(_get_json, url)
    except Exception:
        return None

    latency = round((time.perf_counter() - started_at) * 1000, 2)
    return _coerce_robot_state(payload, latency)

