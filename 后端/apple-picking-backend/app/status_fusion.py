from typing import Optional

from app.adapters.robot_client import RawRobotState
from app.mock_task import get_mock_fallback_snapshot
from app.models import ExecutionMode, RobotStatus, TaskState, UIStateResponse
from app.services.vision_service import vision_service
from app.state_manager import task_state


def robot_step_to_progress(step_count: int) -> int:
    return max(0, min(100, int(step_count)))


def robot_state_to_task_state(raw_robot_state: RawRobotState) -> TaskState:
    if raw_robot_state.is_running:
        return TaskState.RUNNING
    if raw_robot_state.step_count >= 100:
        return TaskState.DONE
    return TaskState.STOPPED


def _robot_status_from_raw(raw_robot_state: RawRobotState) -> RobotStatus:
    return RobotStatus(
        running=raw_robot_state.is_running,
        fps=raw_robot_state.fps,
        step=raw_robot_state.step_count,
        latency=raw_robot_state.latency,
        source="robot_client",
    )


def _robot_status_for_ui(raw_robot_state: Optional[RawRobotState]) -> RobotStatus:
    if raw_robot_state is not None:
        return _robot_status_from_raw(raw_robot_state)

    robot_status = task_state.get_robot_status()
    if robot_status.source == "robot_client":
        return robot_status

    fallback = get_mock_fallback_snapshot()
    return RobotStatus(
        running=fallback.running,
        fps=fallback.fps,
        step=fallback.step,
        latency=fallback.latency,
        source="mock_fallback",
    )


def build_ui_state(
    mode: Optional[ExecutionMode] = None,
    raw_robot_state: Optional[RawRobotState] = None,
) -> UIStateResponse:
    backend_status = task_state.get_status()
    current_mode = mode or task_state.get_mode()
    robot_status = _robot_status_for_ui(raw_robot_state)

    task_state_value = backend_status.state
    progress = backend_status.progress

    if raw_robot_state is not None:
        task_state_value = robot_state_to_task_state(raw_robot_state)
        progress = robot_step_to_progress(raw_robot_state.step_count)

    return UIStateResponse(
        task_state=task_state_value,
        progress=progress,
        mode=current_mode,
        target_maturity=backend_status.target_maturity,
        logs=backend_status.logs,
        robot_status=robot_status,
        policy_status=backend_status.policy_status,
        vision_status=vision_service.snapshot(),
    )
