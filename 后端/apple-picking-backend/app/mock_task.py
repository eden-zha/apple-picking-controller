import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class MockFallbackSnapshot:
    running: bool
    fps: float
    step: int
    latency: Optional[float] = None


def get_mock_fallback_snapshot() -> MockFallbackSnapshot:
    cycle_seconds = 20
    elapsed = int(time.monotonic()) % cycle_seconds
    progress = int((elapsed / (cycle_seconds - 1)) * 100)
    return MockFallbackSnapshot(
        running=False,
        fps=12.0,
        step=progress,
        latency=None,
    )
