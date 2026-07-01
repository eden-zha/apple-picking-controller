import csv
import io

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from app.stats_service import stats_service


router = APIRouter()


@router.websocket("/ws/stats")
async def websocket_stats(websocket: WebSocket) -> None:
    await websocket.accept()
    queue = await stats_service.subscribe()
    try:
        while True:
            stats = await queue.get()
            await websocket.send_json(stats)
    except WebSocketDisconnect:
        stats_service.unsubscribe(queue)


@router.post("/monitor/start")
async def start_monitor():
    return await stats_service.start_monitor()


@router.post("/monitor/stop")
async def stop_monitor():
    return await stats_service.stop_monitor()


@router.post("/stats/reset")
async def reset_stats():
    return await stats_service.reset_stats()


@router.get("/export/csv")
async def export_csv():
    rows = await stats_service.export_rows()
    output = io.StringIO()
    fieldnames = [
        "initial_total",
        "current_total",
        "picked_total",
        "red_count",
        "green_count",
        "fps",
        "running",
        "camera_status",
        "model_status",
        "message",
        "updated_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=mock_vision_stats.csv"},
    )


@router.post("/snapshot")
async def snapshot():
    return await stats_service.create_snapshot()
