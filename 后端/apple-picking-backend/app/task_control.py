from typing import Optional, Tuple

from app.adapters.robot_client import RawRobotState
from app.models import ExecutionMode
from app.services.lerobot_record_service import lerobot_record_service
from app.status_fusion import build_ui_state
from app.state_manager import task_state
from app.websocket_manager import websocket_manager


def _ui_state_payload(ui_state) -> dict:
    if hasattr(ui_state, "model_dump"):
        return ui_state.model_dump(mode="json")
    return ui_state.dict()


async def push_ui_state(
    mode: Optional[ExecutionMode] = None,
    raw_robot_state: Optional[RawRobotState] = None,
) -> None:
    ui_state = build_ui_state(mode, raw_robot_state)
    await websocket_manager.broadcast(_ui_state_payload(ui_state))


async def execute_task(mode: ExecutionMode) -> Tuple[bool, str]:
    await task_state.set_mode(ExecutionMode.robot_pc)
    can_start, message = await task_state.can_start()
    if not can_start:
        await task_state.add_log(message)
        await push_ui_state(ExecutionMode.robot_pc)
        return False, message

    target_maturity = task_state.get_target_maturity()
    robot_model = task_state.get_robot_model()
    result = await lerobot_record_service.start(
        target_maturity=target_maturity,
        robot_model=robot_model,
    )
    await task_state.set_policy_status(lerobot_record_service.status())

    if not result.success:
        await task_state.mark_error(result.message)
        await push_ui_state(ExecutionMode.robot_pc)
        return False, result.message

    await task_state.start_running("LeRobot script process running")
    await task_state.add_log(result.message)
    await push_ui_state(ExecutionMode.robot_pc)
    return True, result.message


async def stop_robot_task(mode: ExecutionMode = ExecutionMode.robot_pc) -> Tuple[bool, str]:
    await task_state.set_mode(ExecutionMode.robot_pc)
    result = await lerobot_record_service.stop()
    await task_state.set_policy_status(lerobot_record_service.status())
    stopped, local_message = await task_state.stop()
    await push_ui_state(ExecutionMode.robot_pc)

    if result.success:
        return True, result.message
    if stopped:
        return False, f"{local_message} {result.message}"
    return False, result.message
