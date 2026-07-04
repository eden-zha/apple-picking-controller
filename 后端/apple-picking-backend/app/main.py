import asyncio
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.adapters import robot_client
from app.models import CommandResponse, LogsResponse, PolicyStatus, TargetAppleRequest, TaskCommandRequest, UIStateResponse, VisionStatus
from app.status_fusion import build_ui_state
from app.services.policy_runtime_service import policy_runtime_service
from app.services.vision_service import vision_service
from app.state_manager import task_state
from app.task_control import execute_task, push_ui_state, stop_robot_task
from app.websocket_manager import websocket_manager


app = FastAPI(
    title="Apple Picking Robot Backend",
    description="Real robot control path with fused UI status display.",
    version="0.3.0",
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


def ui_state_payload(ui_state: UIStateResponse) -> dict:
    if hasattr(ui_state, "model_dump"):
        return ui_state.model_dump(mode="json")
    return ui_state.dict()


async def refresh_policy_status() -> None:
    await task_state.set_policy_status(policy_runtime_service.status())


async def refresh_robot_status() -> None:
    raw_state = await robot_client.get_state()
    if raw_state is None:
        await task_state.mark_robot_status_unavailable()
        return
    await task_state.set_robot_status_from_raw(raw_state)


@app.get("/status", response_model=UIStateResponse)
async def get_status() -> UIStateResponse:
    await refresh_policy_status()
    await refresh_robot_status()
    return build_ui_state()


@app.websocket("/ws/status")
async def status_websocket(websocket: WebSocket) -> None:
    await websocket_manager.connect(websocket)
    try:
        await websocket.send_json(ui_state_payload(build_ui_state()))
        while True:
            await asyncio.sleep(30)
            await refresh_policy_status()
            await refresh_robot_status()
            await websocket.send_json(ui_state_payload(build_ui_state()))
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception:
        websocket_manager.disconnect(websocket)


@app.websocket("/ws/vision")
async def vision_websocket(websocket: WebSocket) -> None:
    await vision_service.websocket_manager.connect(websocket)
    try:
        await websocket.send_json(ui_state_payload(vision_service.snapshot()))
        while True:
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        vision_service.websocket_manager.disconnect(websocket)
    except Exception:
        vision_service.websocket_manager.disconnect(websocket)


@app.post("/set_target_apple", response_model=CommandResponse)
async def set_target_apple(request: TargetAppleRequest) -> CommandResponse:
    await task_state.set_target_maturity(request.target_maturity)
    await push_ui_state(task_state.get_mode())
    return CommandResponse(
        success=True,
        message=f"target_maturity set to {request.target_maturity.value}.",
        status=build_ui_state(),
    )


@app.post("/start_task", response_model=CommandResponse)
async def start_task(request: Optional[TaskCommandRequest] = None) -> CommandResponse:
    started, message = await execute_task(TaskCommandRequest().mode)
    return CommandResponse(success=started, message=message, status=build_ui_state())


@app.post("/stop", response_model=CommandResponse)
async def stop_task(request: Optional[TaskCommandRequest] = None) -> CommandResponse:
    stopped, message = await stop_robot_task(TaskCommandRequest().mode)
    return CommandResponse(success=stopped, message=message, status=build_ui_state())


@app.post("/policy/start")
async def start_local_policy_runtime(request: Optional[TargetAppleRequest] = None) -> dict:
    target_maturity = request.target_maturity if request is not None else task_state.get_target_maturity()
    if request is not None:
        await task_state.set_target_maturity(request.target_maturity)
    await vision_service.start()
    result = await policy_runtime_service.start(target_maturity=target_maturity)
    await task_state.set_policy_status(policy_runtime_service.status())
    return {
        "success": result.success,
        "message": result.message,
        "policy_status": ui_state_payload(build_ui_state()).get("policy_status"),
    }


@app.post("/policy/stop")
async def stop_local_policy_runtime() -> dict:
    result = await policy_runtime_service.stop()
    await vision_service.stop()
    await task_state.set_policy_status(policy_runtime_service.status())
    return {
        "success": result.success,
        "message": result.message,
        "policy_status": ui_state_payload(build_ui_state()).get("policy_status"),
    }


@app.get("/policy/status", response_model=PolicyStatus)
async def get_policy_runtime_status() -> PolicyStatus:
    await task_state.set_policy_status(policy_runtime_service.status())
    return policy_runtime_service.status()


@app.get("/vision/status", response_model=VisionStatus)
async def get_vision_status() -> VisionStatus:
    return vision_service.snapshot()


@app.post("/reset", response_model=CommandResponse)
async def reset_system() -> CommandResponse:
    await policy_runtime_service.stop()
    await vision_service.stop()
    await task_state.reset()
    await push_ui_state(task_state.get_mode())
    return CommandResponse(success=True, message="System reset.", status=build_ui_state())


@app.get("/logs", response_model=LogsResponse)
async def get_logs() -> LogsResponse:
    return LogsResponse(logs=task_state.get_logs())
