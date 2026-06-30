import asyncio
from typing import Tuple

from app.state_manager import task_state


MOCK_STEPS = [
    (0, "初始化模拟采摘任务"),
    (20, "模拟识别目标苹果颜色"),
    (40, "模拟定位目标苹果"),
    (60, "模拟执行采摘动作"),
    (80, "模拟放置苹果"),
    (100, "模拟任务收尾"),
]


async def _run_mock_task() -> None:
    current_task = asyncio.current_task()
    try:
        for progress, current_step in MOCK_STEPS:
            should_continue = await task_state.update_progress(progress, current_step)
            if not should_continue:
                return
            if progress < 100:
                await asyncio.sleep(1)
        await task_state.complete()
    except asyncio.CancelledError:
        await task_state.add_log("模拟任务已取消，进度不再继续更新。")
    except Exception as exc:
        await task_state.add_log(f"模拟任务异常：{exc}")
    finally:
        await task_state.clear_running_task(current_task)


async def start_mock_task() -> Tuple[bool, str]:
    can_start, message = await task_state.can_start()
    if not can_start:
        await task_state.add_log(message)
        return False, message

    await task_state.start_running()
    task = asyncio.create_task(_run_mock_task())
    await task_state.set_running_task(task)
    return True, "任务已启动，后台正在模拟执行。"
