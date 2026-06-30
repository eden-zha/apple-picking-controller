from typing import Tuple

from app.adapters.robot_client import send_robot_command
from app.mock_task import start_mock_task
from app.models import ExecutionMode, TaskState
from app.state_manager import task_state


async def start_robot_task(mode: ExecutionMode = ExecutionMode.remote) -> Tuple[bool, str]:
    can_start, message = await task_state.can_start()
    if not can_start:
        await task_state.add_log(message)
        return False, message

    if mode == ExecutionMode.local:
        await task_state.add_log("Start mode=local, using local mock task.")
        return await start_mock_task()

    result = await send_robot_command("start")
    if result.success:
        await task_state.start_running()
        await task_state.add_log(f"remote success: robot start request sent: {result.url}")
        return True, "Robot start request sent. Task is running on robot PC."

    await task_state.add_log(
        f"remote failed -> fallback triggered: {result.message}"
    )
    return await start_mock_task()


async def stop_robot_task(mode: ExecutionMode = ExecutionMode.remote) -> Tuple[bool, str]:
    status = task_state.get_status()
    if status.state != TaskState.RUNNING:
        return await task_state.stop()

    if mode == ExecutionMode.local:
        await task_state.add_log("Stop mode=local, using local stop.")
        return await task_state.stop()

    result = await send_robot_command("stop")
    stopped, local_message = await task_state.stop()

    if result.success:
        await task_state.add_log(f"remote success: robot stop request sent: {result.url}")
        return stopped, "Robot stop request sent. Task has been stopped locally."

    await task_state.add_log(
        f"remote failed -> fallback triggered, local stop applied: {result.message}"
    )
    return stopped, f"{local_message} Robot stop request failed; local fallback applied."
