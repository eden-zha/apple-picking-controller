import asyncio
from datetime import datetime
from typing import Dict, List

from app.mock_vision_service import generate_next_stats


class StatsService:
    def __init__(self) -> None:
        self._initial_total = 42
        self._stats = self._create_initial_stats()
        self._running = False
        self._lock = asyncio.Lock()
        self._subscribers = set()
        self._background_task = None

    def _create_initial_stats(self) -> Dict:
        initial_total = self._initial_total
        red_count = int(round(initial_total * 0.68))
        green_count = initial_total - red_count
        return {
            "initial_total": initial_total,
            "current_total": initial_total,
            "picked_total": 0,
            "red_count": red_count,
            "green_count": green_count,
            "fps": 0.0,
            "running": False,
            "camera_status": "mock",
            "model_status": "mock_running",
            "message": "Vision mock monitor is idle.",
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }

    def _normalize_stats(self, stats: Dict) -> Dict:
        initial_total = max(0, int(stats["initial_total"]))
        current_total = max(0, min(initial_total, int(stats["current_total"])))
        picked_total = initial_total - current_total
        red_count = max(0, min(current_total, int(stats.get("red_count", 0))))
        green_count = max(0, current_total - red_count)

        return {
            **stats,
            "initial_total": initial_total,
            "current_total": current_total,
            "picked_total": picked_total,
            "red_count": red_count,
            "green_count": green_count,
            "running": self._running,
            "camera_status": "mock",
            "model_status": "mock_running",
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }

    async def ensure_background_task(self) -> None:
        if self._background_task is None or self._background_task.done():
            self._background_task = asyncio.create_task(self._run_background_loop())

    async def _run_background_loop(self) -> None:
        while True:
            async with self._lock:
                if self._running:
                    self._stats = self._normalize_stats(generate_next_stats(self._stats))
                else:
                    self._stats = self._normalize_stats(self._stats)
                snapshot = dict(self._stats)

            await self._broadcast(snapshot)
            await asyncio.sleep(1)

    async def _broadcast(self, snapshot: Dict) -> None:
        stale_subscribers = []
        for queue in list(self._subscribers):
            try:
                if queue.full():
                    queue.get_nowait()
                queue.put_nowait(snapshot)
            except asyncio.QueueFull:
                stale_subscribers.append(queue)

        for queue in stale_subscribers:
            self._subscribers.discard(queue)

    async def subscribe(self) -> asyncio.Queue:
        await self.ensure_background_task()
        queue = asyncio.Queue(maxsize=1)
        async with self._lock:
            queue.put_nowait(dict(self._stats))
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    async def start_monitor(self) -> Dict:
        await self.ensure_background_task()
        async with self._lock:
            self._running = True
            self._stats = self._normalize_stats(
                {
                    **self._stats,
                    "running": True,
                    "message": "YOLO mock monitor is running.",
                }
            )
            return dict(self._stats)

    async def stop_monitor(self) -> Dict:
        await self.ensure_background_task()
        async with self._lock:
            self._running = False
            self._stats = self._normalize_stats(
                {
                    **self._stats,
                    "running": False,
                    "fps": 0.0,
                    "message": "YOLO mock monitor is stopped.",
                }
            )
            return dict(self._stats)

    async def reset_stats(self) -> Dict:
        await self.ensure_background_task()
        async with self._lock:
            self._running = False
            self._stats = self._create_initial_stats()
            return dict(self._stats)

    async def get_stats(self) -> Dict:
        await self.ensure_background_task()
        async with self._lock:
            return dict(self._stats)

    async def create_snapshot(self) -> Dict:
        stats = await self.get_stats()
        return {
            "success": True,
            "snapshot_id": f"mock-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "camera_status": "mock",
            "model_status": "mock_running",
            "message": "Mock snapshot captured. No image file was generated.",
            "stats": stats,
        }

    async def export_rows(self) -> List[Dict]:
        stats = await self.get_stats()
        return [stats]


stats_service = StatsService()
