import asyncio
import math
import os
import time
from pathlib import Path
from typing import Any, Optional

from app.models import VisionStatus
from app.websocket_manager import WebSocketManager


DEFAULT_YOLO_CAMERA_INDEX = 1
DEFAULT_PUSH_INTERVAL_SECONDS = 0.5
YOLO_CONFIDENCE_THRESHOLD = 0.25


class VisionService:
    def __init__(self) -> None:
        self.websocket_manager = WebSocketManager()
        self._model = None
        self._camera = None
        self._loop_task = None  # type: Optional[asyncio.Task]
        self._running = False
        self._fallback = False
        self._last_error = None  # type: Optional[str]
        self._last_frame_at = None  # type: Optional[float]
        self._snapshot = VisionStatus()
        self._lock = asyncio.Lock()

    def snapshot(self) -> VisionStatus:
        return self._snapshot

    async def start(self) -> None:
        async with self._lock:
            if self._loop_task is not None and not self._loop_task.done():
                self._running = True
                self._snapshot.status = "running"
                return

            self._running = True
            self._fallback = False
            self._last_error = None
            self._snapshot = VisionStatus(status="running")
            self._loop_task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        async with self._lock:
            self._running = False
            self._snapshot.status = "stopped"
            if self._loop_task is not None:
                self._loop_task.cancel()
                self._loop_task = None
            await asyncio.to_thread(self._release_camera)
        await self.websocket_manager.broadcast(_payload(self._snapshot))

    async def _run_loop(self) -> None:
        try:
            await asyncio.to_thread(self._initialize_real_pipeline)
        except Exception as exc:
            self._enter_fallback(f"vision fallback enabled: {exc}")

        while self._running:
            started_at = time.perf_counter()
            if self._fallback:
                snapshot = self._mock_snapshot()
            else:
                try:
                    snapshot = await asyncio.to_thread(self._infer_once)
                except Exception as exc:
                    self._enter_fallback(f"vision inference failed: {exc}")
                    snapshot = self._mock_snapshot()

            self._snapshot = snapshot
            await self.websocket_manager.broadcast(_payload(snapshot))
            elapsed = time.perf_counter() - started_at
            await asyncio.sleep(max(0.0, DEFAULT_PUSH_INTERVAL_SECONDS - elapsed))

    def _initialize_real_pipeline(self) -> None:
        self._load_yolo()
        self._open_camera()

    def _load_yolo(self) -> None:
        if self._model is not None:
            return

        model_path = _find_yolo_model_path()
        try:
            from ultralytics import YOLO
        except Exception as exc:
            raise RuntimeError("ultralytics is not installed") from exc

        self._model = YOLO(str(model_path))

    def _open_camera(self) -> None:
        if self._camera is not None:
            return

        try:
            import cv2
        except Exception as exc:
            raise RuntimeError("opencv-python is not installed") from exc

        camera_index = int(os.getenv("YOLO_CAMERA_INDEX") or os.getenv("CAMERA_INDEX") or DEFAULT_YOLO_CAMERA_INDEX)
        camera = cv2.VideoCapture(camera_index)
        if not camera.isOpened():
            raise RuntimeError(f"USB camera open failed: index={camera_index}")
        self._camera = camera

    def _infer_once(self) -> VisionStatus:
        if self._camera is None or self._model is None:
            raise RuntimeError("vision pipeline is not initialized")

        ok, frame = self._camera.read()
        if not ok or frame is None:
            raise RuntimeError("camera frame read failed")

        now = time.perf_counter()
        fps = 0.0
        if self._last_frame_at is not None:
            elapsed = now - self._last_frame_at
            if elapsed > 0:
                fps = round(1.0 / elapsed, 2)
        self._last_frame_at = now

        results = self._model(frame, verbose=False)
        apple_list = _extract_apples(results)
        red = sum(1 for apple in apple_list if apple.get("color") == "red")
        yellow = sum(1 for apple in apple_list if apple.get("color") == "yellow")
        green = sum(1 for apple in apple_list if apple.get("color") == "green")

        return VisionStatus(
            total=len(apple_list),
            red=red,
            yellow=yellow,
            green=green,
            fps=fps,
            status="running",
            apple_list=apple_list,
        )

    def _enter_fallback(self, error: str) -> None:
        self._fallback = True
        self._last_error = error
        self._release_camera()

    def _release_camera(self) -> None:
        if self._camera is not None:
            self._camera.release()
            self._camera = None

    def _mock_snapshot(self) -> VisionStatus:
        tick = time.monotonic()
        red = 2 + int((math.sin(tick / 2.0) + 1) * 2)
        yellow = 1 + int((math.cos(tick / 2.8) + 1) * 1.5)
        green = 1 + int((math.sin(tick / 3.4) + 1) * 1.5)
        apple_list = [
            {
                "id": f"fallback-{index + 1}",
                "color": _mock_apple_color(index, red, yellow),
                "confidence": 0.82,
                "bbox": [20 + index * 18, 40, 80 + index * 18, 110],
                "source": "mock_fallback",
            }
            for index in range(red + yellow + green)
        ]
        return VisionStatus(
            total=red + yellow + green,
            red=red,
            yellow=yellow,
            green=green,
            fps=12.0,
            status="fallback",
            apple_list=apple_list,
        )


def _find_yolo_model_path() -> Path:
    configured = os.getenv("YOLO_MODEL_PATH")
    if configured:
        path = Path(configured)
        if path.exists():
            return path
        raise RuntimeError(f"YOLO_MODEL_PATH does not exist: {configured}")

    candidates = [
        Path("best.pt"),
        Path("models/best.pt"),
        Path("weights/best.pt"),
        Path("runs/detect/train/weights/best.pt"),
    ]
    for path in candidates:
        if path.exists():
            return path

    raise RuntimeError("YOLO model not found. Set YOLO_MODEL_PATH or place best.pt in the backend working directory.")


def _extract_apples(results: Any) -> list[dict]:
    if not results:
        return []

    first = results[0]
    boxes = getattr(first, "boxes", None)
    if boxes is None:
        return []

    names = getattr(first, "names", {}) or {}
    apples = []
    for index, box in enumerate(boxes):
        confidence = float(box.conf[0]) if getattr(box, "conf", None) is not None else 0.0
        if confidence < YOLO_CONFIDENCE_THRESHOLD:
            continue

        class_id = int(box.cls[0]) if getattr(box, "cls", None) is not None else -1
        class_name = str(names.get(class_id, class_id)).lower()
        color = _class_to_color(class_name)
        if color is None:
            continue

        xyxy = box.xyxy[0].tolist() if getattr(box, "xyxy", None) is not None else []
        apples.append(
            {
                "id": f"apple-{index + 1}",
                "color": color,
                "confidence": round(confidence, 3),
                "bbox": [round(float(value), 2) for value in xyxy],
                "class_name": class_name,
            }
        )
    return apples


def _class_to_color(class_name: str) -> Optional[str]:
    if "green" in class_name or "unripe" in class_name or class_name == "2":
        return "green"
    if "yellow" in class_name or "half" in class_name or class_name == "1":
        return "yellow"
    if "red" in class_name or "ripe" in class_name or class_name in {"0", "apple"}:
        return "red"
    return None


def _mock_apple_color(index: int, red_count: int, yellow_count: int) -> str:
    if index < red_count:
        return "red"
    if index < red_count + yellow_count:
        return "yellow"
    return "green"


def _payload(snapshot: VisionStatus) -> dict:
    if hasattr(snapshot, "model_dump"):
        return snapshot.model_dump(mode="json")
    return snapshot.dict()


vision_service = VisionService()
