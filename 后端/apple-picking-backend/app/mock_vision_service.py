import random
from typing import Dict


def generate_next_stats(current_stats: Dict) -> Dict:
    # TODO: replace with YOLO + ByteTrack + USB camera pipeline
    initial_total = int(current_stats["initial_total"])
    current_total = int(current_stats["current_total"])

    decrement = random.choice([0, 0, 1, 1, 2])
    next_current_total = max(0, min(initial_total, current_total - decrement))
    picked_total = initial_total - next_current_total

    red_count = int(round(next_current_total * 0.68))
    green_count = next_current_total - red_count

    return {
        **current_stats,
        "current_total": next_current_total,
        "picked_total": picked_total,
        "red_count": red_count,
        "green_count": green_count,
        "fps": round(random.uniform(24.0, 31.5), 1),
        "message": "YOLO mock monitor is running.",
    }
