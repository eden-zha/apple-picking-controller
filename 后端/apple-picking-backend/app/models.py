from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class TaskState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    DONE = "DONE"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class TargetMaturity(str, Enum):
    red = "red"
    yellow = "yellow"


class RobotModel(str, Enum):
    model_a = "model_a"
    model_b = "model_b"


class ExecutionMode(str, Enum):
    robot_pc = "robot_pc"


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
    pending_interaction: Optional[dict[str, Any]] = None
    source: str = "policy_runtime_service"


class VisionStatus(BaseModel):
    total: int = 0
    red: int = 0
    yellow: int = 0
    green: int = 0
    fps: float = 0
    status: str = "stopped"
    apple_list: List[dict] = Field(default_factory=list)


class StatusResponse(BaseModel):
    state: TaskState
    progress: int = Field(ge=0, le=100)
    message: str
    target_maturity: Optional[TargetMaturity] = None
    robot_model: RobotModel = RobotModel.model_a
    current_step: str
    logs: List[str]
    robot_status: RobotStatus = Field(default_factory=RobotStatus)
    policy_status: PolicyStatus = Field(default_factory=PolicyStatus)


class UIStateResponse(BaseModel):
    task_state: TaskState
    progress: int = Field(ge=0, le=100)
    mode: ExecutionMode
    target_maturity: Optional[TargetMaturity] = None
    robot_model: RobotModel = RobotModel.model_a
    logs: List[str]
    robot_status: RobotStatus
    policy_status: PolicyStatus
    vision_status: VisionStatus = Field(default_factory=VisionStatus)


class LogsResponse(BaseModel):
    logs: List[str]


class CommandResponse(BaseModel):
    success: bool
    message: str
    status: UIStateResponse


class TaskCommandRequest(BaseModel):
    mode: ExecutionMode = ExecutionMode.robot_pc


class TargetAppleRequest(BaseModel):
    target_maturity: TargetMaturity


class RobotModelRequest(BaseModel):
    robot_model: RobotModel
