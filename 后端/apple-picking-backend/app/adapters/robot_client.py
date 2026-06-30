import asyncio
import os
from dataclasses import dataclass
from typing import Optional

import requests


DEFAULT_TIMEOUT_SECONDS = 2


@dataclass
class RobotCommandResult:
    success: bool
    message: str
    url: Optional[str] = None


def _get_robot_base_url() -> Optional[str]:
    robot_pc_ip = os.getenv("ROBOT_PC_IP")
    if robot_pc_ip:
        return f"http://{robot_pc_ip}:8000"

    base_url = os.getenv("ROBOT_BASE_URL")
    if base_url:
        return base_url.rstrip("/")

    return "http://127.0.0.1:8000"


def _post_json(url: str) -> None:
    response = requests.post(url, json={}, timeout=DEFAULT_TIMEOUT_SECONDS)
    response.raise_for_status()


async def send_robot_command(command: str) -> RobotCommandResult:
    base_url = _get_robot_base_url()
    url = f"{base_url}/robot/{command}"
    try:
        await asyncio.to_thread(_post_json, url)
    except Exception as exc:
        return RobotCommandResult(
            success=False,
            message=f"remote failed -> fallback triggered: {exc}",
            url=url,
        )

    return RobotCommandResult(
        success=True,
        message=f"remote success: robot command '{command}' sent successfully.",
        url=url,
    )
