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


class StatusResponse(BaseModel):
    state: TaskState
    progress: int = Field(ge=0, le=100)
    message: str
    target_mode: Optional[TargetMode] = None
    current_step: str
    logs: List[str]


class LogsResponse(BaseModel):
    logs: List[str]


class CommandResponse(BaseModel):
    success: bool
    message: str
    status: StatusResponse


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
