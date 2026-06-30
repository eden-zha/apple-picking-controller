import asyncio
from collections import deque
from datetime import datetime
from typing import List, Optional, Tuple

from app.models import StatusResponse, TargetMode, TaskState


class StateManager:
    def __init__(self) -> None:
        self._state = TaskState.IDLE
        self._progress = 0
        self._message = "等待任务开始。"
        self._target_mode = None  # type: Optional[TargetMode]
        self._current_step = "等待开始"
        self._logs = deque(maxlen=50)  # type: deque
        self._active_task = None  # type: Optional[asyncio.Task]
        self._lock = asyncio.Lock()
        self.add_log_sync("系统初始化完成。")

    def _format_log(self, message: str) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] {message}"

    def add_log_sync(self, message: str) -> None:
        self._logs.append(self._format_log(message))

    async def add_log(self, message: str) -> None:
        async with self._lock:
            self.add_log_sync(message)

    def get_status(self) -> StatusResponse:
        return StatusResponse(
            state=self._state,
            progress=self._progress,
            message=self._message,
            target_mode=self._target_mode,
            current_step=self._current_step,
            logs=list(self._logs),
        )

    def get_logs(self) -> List[str]:
        return list(self._logs)

    async def set_running_task(self, task: asyncio.Task) -> None:
        async with self._lock:
            self._active_task = task

    async def clear_running_task(self, task: Optional[asyncio.Task] = None) -> None:
        async with self._lock:
            if task is None or self._active_task is task:
                self._active_task = None

    async def can_start(self) -> Tuple[bool, str]:
        async with self._lock:
            if self._target_mode is None:
                return False, "请先通过 /set_target_apple 选择本轮任务模式。"
            if self._state == TaskState.IDLE:
                return True, "可以启动任务。"
            if self._state == TaskState.RUNNING:
                return False, "任务已经在运行。"
            if self._state in {TaskState.DONE, TaskState.STOPPED}:
                return False, "当前任务已结束或已停止，需要先 reset 后才能重新开始。"
            return False, "当前状态不允许启动任务。"

    async def start_running(self) -> None:
        async with self._lock:
            self._state = TaskState.RUNNING
            self._progress = 0
            self._current_step = "启动模拟识别流程"
            self._message = f"任务运行中，目标模式为 {self._target_mode.value}。"
            self.add_log_sync(f"任务启动，目标模式：{self._target_mode.value}，进入 RUNNING 状态。")

    async def update_progress(self, progress: int, current_step: str) -> bool:
        async with self._lock:
            if self._state != TaskState.RUNNING:
                return False
            self._progress = progress
            self._current_step = current_step
            self._message = f"任务运行中，当前进度 {progress}%。"
            self.add_log_sync(f"任务进度更新为 {progress}%，当前步骤：{current_step}。")
            return True

    async def complete(self) -> None:
        async with self._lock:
            if self._state != TaskState.RUNNING:
                return
            self._state = TaskState.DONE
            self._progress = 100
            self._current_step = "模拟任务完成"
            self._message = "任务完成。"
            self.add_log_sync("任务完成，进入 DONE 状态。")

    async def stop(self) -> Tuple[bool, str]:
        async with self._lock:
            if self._state != TaskState.RUNNING:
                message = "当前没有正在运行的任务。"
                self.add_log_sync(message)
                return False, message

            self._state = TaskState.STOPPED
            self._message = "任务已停止。"
            self._current_step = "任务已停止"
            if self._active_task is not None:
                self._active_task.cancel()
                self._active_task = None
            self.add_log_sync("任务被停止，进入 STOPPED 状态。")
            return True, "任务已停止。"

    async def reset(self) -> None:
        async with self._lock:
            if self._active_task is not None:
                self._active_task.cancel()
                self._active_task = None
            self._state = TaskState.IDLE
            self._progress = 0
            self._message = "等待任务开始。"
            self._current_step = "等待开始"
            self.add_log_sync("系统复位，进入 IDLE 状态。")

    async def set_target_mode(self, target_mode: TargetMode) -> None:
        async with self._lock:
            self._target_mode = target_mode
            self.add_log_sync(f"目标采摘模式已设置为：{target_mode.value}。")


task_state = StateManager()
