import asyncio
import os
import time
from pathlib import Path
from typing import Any, Optional

from app.models import VisionStatus
from app.websocket_manager import WebSocketManager


DEFAULT_CAMERA_INDEX = 1
DEFAULT_PUSH_INTERVAL_SECONDS = 3.0
YOLO_CONFIDENCE_THRESHOLD = 0.25


class VisionService:
    def __init__(self) -> None:
        self.websocket_manager = WebSocketManager()
        self._model = None
        self._camera = None
        self._loop_task = None  # type: Optional[asyncio.Task]
        self._running = False
        self._suspended = False
        self._last_error = None  # type: Optional[str]
        self._last_frame_at = None  # type: Optional[float]
        self._backend_dir = Path(__file__).resolve().parents[2]
        self._debug_image_path = self._backend_dir / "logs" / "yolo_debug.jpg"
        self._printed_model_names = False
        self._snapshot = VisionStatus()
        self._lock = asyncio.Lock()

    def snapshot(self) -> VisionStatus:
        return self._snapshot

    def is_suspended(self) -> bool:
        return self._suspended

    async def start(self) -> None:
        async with self._lock:
            if self._suspended:
                return
            if self._loop_task is not None and not self._loop_task.done():
                self._running = True
                self._snapshot.status = "running"
                return

            self._running = True
            self._last_error = None
            self._last_frame_at = None
            self._snapshot = VisionStatus(status="running")
            self._loop_task = asyncio.create_task(self._run_loop())

    async def resume(self) -> None:
        async with self._lock:
            self._suspended = False
        await self.start()

    async def suspend(self) -> None:
        async with self._lock:
            self._suspended = True
        await self.stop()

    async def stop(self) -> None:
        async with self._lock:
            self._running = False
            self._snapshot = VisionStatus(status="stopped")
            task = self._loop_task
            self._loop_task = None
            await asyncio.to_thread(self._release_camera)

        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        await self.websocket_manager.broadcast(_payload(self._snapshot))

    async def _run_loop(self) -> None:
        try:
            await asyncio.to_thread(self._initialize_real_pipeline)
        except Exception as exc:
            self._mark_unavailable(f"vision unavailable: {exc}")
            self._running = False
            await self.websocket_manager.broadcast(_payload(self._snapshot))
            return

        while self._running:
            started_at = time.perf_counter()
            try:
                snapshot = await asyncio.to_thread(self._infer_once)
            except Exception as exc:
                self._mark_unavailable(f"vision inference failed: {exc}")
                self._running = False
                snapshot = self._snapshot

            self._snapshot = snapshot
            await self.websocket_manager.broadcast(_payload(snapshot))
            if not self._running:
                break
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
        if not self._printed_model_names:
            print(f"[vision] YOLO model_path={model_path}", flush=True)
            print(f"[vision] YOLO model.names={getattr(self._model, 'names', None)}", flush=True)
            self._printed_model_names = True

    def _open_camera(self) -> None:
        if self._camera is not None:
            return

        try:
            import cv2
        except Exception as exc:
            raise RuntimeError("opencv-python is not installed") from exc

        camera_index = int(os.getenv("CAMERA_INDEX", DEFAULT_CAMERA_INDEX))
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
        _print_raw_detections(results)
        self._save_debug_frame(frame, results)
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

    def _mark_unavailable(self, error: str) -> None:
        self._last_error = error
        self._release_camera()
        self._snapshot = VisionStatus(status="unavailable")

    def _save_debug_frame(self, frame: Any, results: Any) -> None:
        try:
            import cv2

            self._debug_image_path.parent.mkdir(parents=True, exist_ok=True)
            annotated = frame.copy()
            if results:
                first = results[0]
                boxes = getattr(first, "boxes", None)
                names = getattr(first, "names", {}) or {}
                if boxes is not None:
                    for box in boxes:
                        confidence = float(box.conf[0]) if getattr(box, "conf", None) is not None else 0.0
                        class_id = int(box.cls[0]) if getattr(box, "cls", None) is not None else -1
                        class_name = str(names.get(class_id, class_id))
                        xyxy = box.xyxy[0].tolist() if getattr(box, "xyxy", None) is not None else []
                        if len(xyxy) != 4:
                            continue
                        x1, y1, x2, y2 = [int(round(float(value))) for value in xyxy]
                        color = _debug_box_color(class_name)
                        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                        label = f"{class_name} {confidence:.2f}"
                        (text_w, text_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
                        label_y1 = max(0, y1 - text_h - baseline - 4)
                        cv2.rectangle(annotated, (x1, label_y1), (x1 + text_w + 6, label_y1 + text_h + baseline + 4), color, -1)
                        cv2.putText(
                            annotated,
                            label,
                            (x1 + 3, label_y1 + text_h + 1),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.55,
                            (255, 255, 255),
                            2,
                            cv2.LINE_AA,
                        )
            cv2.imwrite(str(self._debug_image_path), annotated)
            print(f"[vision] saved annotated debug frame: {self._debug_image_path}", flush=True)
        except Exception as exc:
            print(f"[vision] failed to save debug frame: {type(exc).__name__}: {exc}", flush=True)

    def _release_camera(self) -> None:
        if self._camera is not None:
            self._camera.release()
            self._camera = None


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


def _debug_box_color(class_name: str) -> tuple[int, int, int]:
    color = _class_to_color(class_name.lower())
    if color == "red":
        return (0, 0, 255)
    if color == "yellow":
        return (0, 220, 255)
    if color == "green":
        return (0, 180, 0)
    return (255, 255, 255)


def _print_raw_detections(results: Any) -> None:
    if not results:
        print("[vision] raw detections=[]", flush=True)
        return

    first = results[0]
    boxes = getattr(first, "boxes", None)
    names = getattr(first, "names", {}) or {}
    if boxes is None:
        print("[vision] raw detections boxes=None", flush=True)
        return

    count = 0
    for box in boxes:
        confidence = float(box.conf[0]) if getattr(box, "conf", None) is not None else 0.0
        class_id = int(box.cls[0]) if getattr(box, "cls", None) is not None else -1
        class_name = str(names.get(class_id, class_id))
        xyxy = box.xyxy[0].tolist() if getattr(box, "xyxy", None) is not None else []
        bbox = [round(float(value), 2) for value in xyxy]
        print(
            f"[vision] raw detection class_id={class_id} class_name={class_name} "
            f"conf={confidence:.3f} bbox={bbox}",
            flush=True,
        )
        count += 1

    if count == 0:
        print("[vision] raw detections=[]", flush=True)


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
    if "green" in class_name:
        return "green"
    if "yellow" in class_name or "half" in class_name or "unripe" in class_name or class_name == "1":
        return "yellow"
    if "red" in class_name or "ripe" in class_name or class_name in {"0", "apple"}:
        return "red"
    return None


def _payload(snapshot: VisionStatus) -> dict:
    if hasattr(snapshot, "model_dump"):
        return snapshot.model_dump(mode="json")
    return snapshot.dict()


vision_service = VisionService()
