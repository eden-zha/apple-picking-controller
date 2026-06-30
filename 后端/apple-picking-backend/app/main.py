from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from app.models import CommandResponse, LogsResponse, StatusResponse, TargetAppleRequest, TaskCommandRequest
from app.state_manager import task_state
from app.task_control import start_robot_task, stop_robot_task

app = FastAPI(
    title="Apple Picking Backend Prototype",
    description="A FastAPI prototype for UI-backend communication. No real hardware is connected.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    return task_state.get_status()


@app.post("/set_target_apple", response_model=CommandResponse)
async def set_target_apple(request: TargetAppleRequest) -> CommandResponse:
    target_mode = request.resolve_target_mode()
    if target_mode is None:
        raise HTTPException(
            status_code=400,
            detail="请使用 target_mode=red_only 或 target_mode=red_green；旧版仅兼容 target_color=red。",
        )

    await task_state.set_target_mode(target_mode)
    return CommandResponse(
        success=True,
        message=f"目标采摘模式已设置为：{target_mode.value}。",
        status=task_state.get_status(),
    )


@app.post("/start_task", response_model=CommandResponse)
async def start_task(request: Optional[TaskCommandRequest] = None) -> CommandResponse:
    mode = request.mode if request is not None else TaskCommandRequest().mode
    started, message = await start_robot_task(mode)
    return CommandResponse(success=started, message=message, status=task_state.get_status())


@app.post("/stop", response_model=CommandResponse)
async def stop_task(request: Optional[TaskCommandRequest] = None) -> CommandResponse:
    mode = request.mode if request is not None else TaskCommandRequest().mode
    stopped, message = await stop_robot_task(mode)
    return CommandResponse(success=stopped, message=message, status=task_state.get_status())


@app.post("/reset", response_model=CommandResponse)
async def reset_system() -> CommandResponse:
    await task_state.reset()
    return CommandResponse(success=True, message="系统已复位，等待新任务。", status=task_state.get_status())


@app.get("/logs", response_model=LogsResponse)
async def get_logs() -> LogsResponse:
    return LogsResponse(logs=task_state.get_logs())
