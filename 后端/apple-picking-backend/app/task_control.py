from typing import Optional, Tuple

from app.adapters.robot_client import RawRobotState
from app.models import ExecutionMode, PolicyStatus
from app.services.policy_runtime_service import policy_runtime_service
from app.status_fusion import build_ui_state
from app.state_manager import task_state
from app.websocket_manager import websocket_manager


def _ui_state_payload(ui_state) -> dict:
    if hasattr(ui_state, "model_dump"):
        return ui_state.model_dump(mode="json")
    return ui_state.dict()


def _is_local(mode: ExecutionMode) -> bool:
    return mode == ExecutionMode.local


async def push_ui_state(
    mode: Optional[ExecutionMode] = None,
    raw_robot_state: Optional[RawRobotState] = None,
) -> None:
    ui_state = build_ui_state(mode, raw_robot_state)
    await websocket_manager.broadcast(_ui_state_payload(ui_state))


async def execute_task(mode: ExecutionMode) -> Tuple[bool, str]:
    await task_state.set_mode(mode)
    can_start, message = await task_state.can_start()
    if not can_start:
        await task_state.add_log(message)
        await push_ui_state(mode)
        return False, message

    result = await policy_runtime_service.start(local=_is_local(mode))
    if _is_local(mode):
        await task_state.set_policy_status(policy_runtime_service.status())
    else:
        await task_state.set_policy_status(
            PolicyStatus(
                running=result.success,
                loaded=result.success,
                paused=False,
                source="remote_policy_runtime_service",
                last_error=None if result.success else result.message,
            )
        )

    if not result.success:
        await task_state.mark_error(result.message)
        await push_ui_state(mode)
        return False, result.message

    await task_state.start_running("policy_runtime_service inference loop running")
    await task_state.add_log(result.message)
    await push_ui_state(mode)
    return True, result.message


async def stop_robot_task(mode: ExecutionMode = ExecutionMode.remote) -> Tuple[bool, str]:
    await task_state.set_mode(mode)
    result = await policy_runtime_service.stop(local=_is_local(mode))
    if _is_local(mode):
        await task_state.set_policy_status(policy_runtime_service.status())
    else:
        await task_state.set_policy_status(
            PolicyStatus(
                running=False,
                loaded=False,
                paused=False,
                source="remote_policy_runtime_service",
                last_error=None if result.success else result.message,
            )
        )
    stopped, local_message = await task_state.stop()
    await push_ui_state(mode)

    if result.success:
        return True, result.message
    if stopped:
        return False, f"{local_message} {result.message}"
    return False, result.message
