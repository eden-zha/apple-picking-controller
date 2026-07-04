import asyncio
from collections import deque
from datetime import datetime
from typing import List, Optional, Tuple

from app.adapters.robot_client import RawRobotState
from app.models import ExecutionMode, PolicyStatus, RobotStatus, StatusResponse, TargetMaturity, TaskState


class StateManager:
    def __init__(self) -> None:
        self._state = TaskState.IDLE
        self._progress = 0
        self._message = "Waiting for task start."
        self._mode = ExecutionMode.robot_pc
        self._target_maturity = None  # type: Optional[TargetMaturity]
        self._current_step = "Waiting"
        self._robot_status = RobotStatus(source="unavailable")
        self._policy_status = PolicyStatus()
        self._logs = deque(maxlen=50)
        self._active_task = None  # type: Optional[asyncio.Task]
        self._lock = asyncio.Lock()
        self.add_log_sync("System initialized.")

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
            target_maturity=self._target_maturity,
            current_step=self._current_step,
            logs=list(self._logs),
            robot_status=self._robot_status,
            policy_status=self._policy_status,
        )

    def get_robot_status(self) -> RobotStatus:
        return self._robot_status

    def get_policy_status(self) -> PolicyStatus:
        return self._policy_status

    def get_logs(self) -> List[str]:
        return list(self._logs)

    def get_mode(self) -> ExecutionMode:
        return self._mode

    async def set_running_task(self, task: asyncio.Task) -> None:
        async with self._lock:
            self._active_task = task

    async def clear_running_task(self, task: Optional[asyncio.Task] = None) -> None:
        async with self._lock:
            if task is None or self._active_task is task:
                self._active_task = None

    async def can_start(self) -> Tuple[bool, str]:
        async with self._lock:
            if self._target_maturity is None:
                return False, "Select target_maturity before starting a task."
            if self._state == TaskState.IDLE:
                return True, "Task can start."
            if self._state == TaskState.RUNNING:
                return False, "Task is already running."
            if self._state in {TaskState.DONE, TaskState.STOPPED, TaskState.ERROR}:
                return False, "Reset is required before starting another task."
            return False, "Current state does not allow task start."

    async def start_running(self, current_step: str = "robot PC vision and arm control running") -> None:
        async with self._lock:
            self._state = TaskState.RUNNING
            self._progress = 0
            self._current_step = current_step
            target = self._target_maturity.value if self._target_maturity else "unset"
            self._message = f"Task running with target_maturity={target}."
            self.add_log_sync(f"Task entered RUNNING on robot PC, target_maturity={target}.")

    async def set_mode(self, mode: ExecutionMode) -> None:
        async with self._lock:
            self._mode = mode

    async def set_robot_status_from_raw(self, raw_robot_state: RawRobotState) -> None:
        async with self._lock:
            self._robot_status = RobotStatus(
                running=raw_robot_state.is_running,
                fps=raw_robot_state.fps,
                step=raw_robot_state.step_count,
                latency=raw_robot_state.latency,
                source="robot_client",
            )

    async def mark_robot_status_unavailable(self) -> None:
        async with self._lock:
            self._robot_status = RobotStatus(source="unavailable")

    async def set_policy_status(self, policy_status: PolicyStatus) -> None:
        async with self._lock:
            self._policy_status = policy_status

    async def apply_fused_task_state(
        self,
        state: TaskState,
        progress: int,
        current_step: str,
    ) -> None:
        async with self._lock:
            self._state = state
            self._progress = max(0, min(100, progress))
            self._current_step = current_step
            self._message = f"Task state={state.value}, progress={self._progress}%."
            self.add_log_sync(f"Fused state updated: {state.value} / {self._progress}% / {current_step}.")

    async def update_progress(self, progress: int, current_step: str) -> bool:
        async with self._lock:
            if self._state != TaskState.RUNNING:
                return False
            self._progress = max(0, min(100, progress))
            self._current_step = current_step
            self._message = f"Task running, progress={self._progress}%."
            self.add_log_sync(f"Progress updated: {self._progress}% / {current_step}.")
            return True

    async def complete(self) -> None:
        async with self._lock:
            if self._state != TaskState.RUNNING:
                return
            self._state = TaskState.DONE
            self._progress = 100
            self._current_step = "Task complete"
            self._message = "Task complete."
            self.add_log_sync("Task entered DONE.")

    async def mark_error(self, message: str) -> None:
        async with self._lock:
            if self._active_task is not None:
                self._active_task.cancel()
                self._active_task = None
            self._state = TaskState.ERROR
            self._message = message
            self._current_step = "Error"
            self.add_log_sync(message)

    async def stop(self) -> Tuple[bool, str]:
        async with self._lock:
            if self._state != TaskState.RUNNING:
                message = "No task is currently running."
                self.add_log_sync(message)
                return False, message

            self._state = TaskState.STOPPED
            self._message = "Task stopped."
            self._current_step = "Stopped"
            if self._active_task is not None:
                self._active_task.cancel()
                self._active_task = None
            self.add_log_sync("Task entered STOPPED.")
            return True, "Task stopped."

    async def reset(self) -> None:
        async with self._lock:
            if self._active_task is not None:
                self._active_task.cancel()
                self._active_task = None
            self._state = TaskState.IDLE
            self._progress = 0
            self._mode = ExecutionMode.robot_pc
            self._message = "Waiting for task start."
            self._current_step = "Waiting"
            self._robot_status = RobotStatus(source="unavailable")
            self._policy_status = PolicyStatus()
            self.add_log_sync("System reset to IDLE.")

    def get_target_maturity(self) -> Optional[TargetMaturity]:
        return self._target_maturity

    async def set_target_maturity(self, target_maturity: TargetMaturity) -> None:
        async with self._lock:
            self._target_maturity = target_maturity
            self.add_log_sync(f"target_maturity set to {target_maturity.value}.")


task_state = StateManager()
