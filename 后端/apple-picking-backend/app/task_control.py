from typing import Optional, Tuple

from app.adapters.robot_client import RawRobotState
from app.models import ExecutionMode
from app.services.policy_runtime_service import policy_runtime_service
from app.services.vision_service import vision_service
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

    await vision_service.start()
    target_maturity = task_state.get_target_maturity()
    result = await policy_runtime_service.start(target_maturity=target_maturity)
    await task_state.set_policy_status(policy_runtime_service.status())

    if not result.success:
        await task_state.mark_error(result.message)
        await push_ui_state(ExecutionMode.robot_pc)
        return False, result.message

    await task_state.start_running("YOLO vision and robot PC arm control running")
    await task_state.add_log(result.message)
    await push_ui_state(ExecutionMode.robot_pc)
    return True, result.message


async def stop_robot_task(mode: ExecutionMode = ExecutionMode.robot_pc) -> Tuple[bool, str]:
    await task_state.set_mode(ExecutionMode.robot_pc)
    result = await policy_runtime_service.stop()
    await vision_service.stop()
    await task_state.set_policy_status(policy_runtime_service.status())
    stopped, local_message = await task_state.stop()
    await push_ui_state(ExecutionMode.robot_pc)

    if result.success:
        return True, result.message
    if stopped:
        return False, f"{local_message} {result.message}"
    return False, result.message
