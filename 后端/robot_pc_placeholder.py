from datetime import datetime

from fastapi import FastAPI


app = FastAPI(
    title="Robot PC Placeholder Service",
    description="Placeholder robot server for demo integration. Replace with real robot control service.",
)


@app.get("/health")
async def health():
    return {
        "ok": True,
        "service": "robot_pc_placeholder",
        "time": datetime.now().isoformat(timespec="seconds"),
    }


@app.post("/robot/start")
async def robot_start():
    return {
        "success": True,
        "message": "placeholder robot start accepted",
        "time": datetime.now().isoformat(timespec="seconds"),
    }


@app.post("/robot/stop")
async def robot_stop():
    return {
        "success": True,
        "message": "placeholder robot stop accepted",
        "time": datetime.now().isoformat(timespec="seconds"),
    }
