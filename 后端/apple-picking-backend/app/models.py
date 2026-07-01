from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class TaskState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    DONE = "DONE"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class TargetMode(str, Enum):
    red_only = "red_only"
    red_green = "red_green"


class LegacyTargetColor(str, Enum):
    red = "red"


class ExecutionMode(str, Enum):
    local = "local"
    remote = "remote"


class RobotStatus(BaseModel):
    running: bool = False
    fps: float = 0
    step: int = 0
    latency: Optional[float] = None
    source: str = "unavailable"


class PolicyStatus(BaseModel):
    running: bool = False
    loaded: bool = False
    paused: bool = False
    model_path: Optional[str] = None
    inference_hz: float = 0
    loop_hz: float = 0
    last_error: Optional[str] = None
    source: str = "policy_runtime_service"


class StatusResponse(BaseModel):
    state: TaskState
    progress: int = Field(ge=0, le=100)
    message: str
    target_mode: Optional[TargetMode] = None
    current_step: str
    logs: List[str]
    robot_status: RobotStatus = Field(default_factory=RobotStatus)
    policy_status: PolicyStatus = Field(default_factory=PolicyStatus)


class UIStateResponse(BaseModel):
    task_state: TaskState
    progress: int = Field(ge=0, le=100)
    mode: ExecutionMode
    target_mode: Optional[TargetMode] = None
    logs: List[str]
    robot_status: RobotStatus
    policy_status: PolicyStatus


class LogsResponse(BaseModel):
    logs: List[str]


class CommandResponse(BaseModel):
    success: bool
    message: str
    status: UIStateResponse


class TaskCommandRequest(BaseModel):
    mode: ExecutionMode = ExecutionMode.remote


class TargetAppleRequest(BaseModel):
    target_mode: Optional[TargetMode] = None
    target_color: Optional[LegacyTargetColor] = None

    def resolve_target_mode(self) -> Optional[TargetMode]:
        if self.target_mode is not None:
            return self.target_mode
        if self.target_color == LegacyTargetColor.red:
            return TargetMode.red_only
        return None
