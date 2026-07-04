import asyncio
import importlib
import os
import time
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class RobotCommandResult:
    success: bool
    message: str


@dataclass
class RawRobotState:
    is_running: bool
    fps: float
    step_count: int
    observation: Optional[Any] = None
    current_action: Optional[Any] = None
    latency: Optional[float] = None


_direct_robot = None
_step_count = 0


def _env(name: str) -> Optional[str]:
    value = os.getenv(name)
    if value and value.strip():
        return value.strip()
    return None


def _load_direct_robot() -> Any:
    global _direct_robot
    if _direct_robot is not None:
        return _direct_robot

    factory_path = _env("SO_ARM101_ROBOT_FACTORY")
    if not factory_path:
        raise RuntimeError("SO_ARM101_ROBOT_FACTORY is not set on this robot PC.")

    module_name, function_name = factory_path.rsplit(":", 1)
    factory = getattr(importlib.import_module(module_name), function_name)
    _direct_robot = factory()
    if hasattr(_direct_robot, "connect"):
        _direct_robot.connect()
    return _direct_robot


def _direct_get_state() -> RawRobotState:
    global _step_count
    robot = _load_direct_robot()
    observation = None
    if hasattr(robot, "get_observation"):
        observation = robot.get_observation()
    elif hasattr(robot, "capture_observation"):
        observation = robot.capture_observation()

    running = True
    if hasattr(robot, "is_running"):
        running = bool(robot.is_running())

    _step_count = min(_step_count + 1, 100)
    return RawRobotState(
        is_running=running,
        fps=0,
        step_count=_step_count,
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
    raise RuntimeError("Configured SO-ARM101 robot object has no send_action/set_action API.")


async def start() -> RobotCommandResult:
    try:
        await asyncio.to_thread(_load_direct_robot)
    except Exception as exc:
        return RobotCommandResult(False, f"SO-ARM101 start failed: {exc}")
    return RobotCommandResult(True, "SO-ARM101 robot connected on robot PC")


async def stop() -> RobotCommandResult:
    global _direct_robot, _step_count
    try:
        robot = _load_direct_robot()
        if hasattr(robot, "disconnect"):
            await asyncio.to_thread(robot.disconnect)
    except Exception as exc:
        return RobotCommandResult(False, f"SO-ARM101 stop failed: {exc}")

    _direct_robot = None
    _step_count = 0
    return RobotCommandResult(True, "SO-ARM101 robot stopped on robot PC")


async def send_action(action: Any) -> RobotCommandResult:
    try:
        await asyncio.to_thread(_direct_send_action, action)
    except Exception as exc:
        return RobotCommandResult(False, f"SO-ARM101 action failed: {exc}")
    return RobotCommandResult(True, "SO-ARM101 action sent locally")


async def get_state() -> Optional[RawRobotState]:
    started_at = time.perf_counter()
    try:
        state = await asyncio.to_thread(_direct_get_state)
    except Exception:
        return None
    state.latency = round((time.perf_counter() - started_at) * 1000, 2)
    return state
