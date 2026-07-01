import asyncio
import glob
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import requests

from app.adapters import robot_client
from app.models import PolicyStatus


DEFAULT_TARGET_HZ = 20.0
REMOTE_TIMEOUT_SECONDS = 5


@dataclass
class PolicyCommandResult:
    success: bool
    message: str


class PolicyRuntimeService:
    def __init__(self) -> None:
        self._policy = None
        self._model_path = None  # type: Optional[str]
        self._loop_task = None  # type: Optional[asyncio.Task]
        self._running = False
        self._paused = False
        self._last_error = None  # type: Optional[str]
        self._loop_hz = 0.0
        self._inference_hz = _float_env("POLICY_INFERENCE_HZ", DEFAULT_TARGET_HZ)
        self._last_action = None
        self._lock = asyncio.Lock()

    def status(self) -> PolicyStatus:
        return PolicyStatus(
            running=self._running,
            loaded=self._policy is not None,
            paused=self._paused,
            model_path=self._model_path,
            inference_hz=self._inference_hz,
            loop_hz=self._loop_hz,
            last_error=self._last_error,
        )

    async def start(self, local: bool) -> PolicyCommandResult:
        if not local:
            return await _remote_policy_command("start")

        async with self._lock:
            if self._running:
                return PolicyCommandResult(True, "policy runtime already running")

            try:
                await asyncio.to_thread(self._load_policy)
                robot_start = await robot_client.start(local=True)
                if not robot_start.success:
                    self._last_error = robot_start.message
                    return PolicyCommandResult(False, robot_start.message)
            except Exception as exc:
                self._last_error = str(exc)
                return PolicyCommandResult(False, f"policy runtime start failed: {exc}")

            self._running = True
            self._paused = False
            self._last_error = None
            self._loop_task = asyncio.create_task(self._inference_loop())
            return PolicyCommandResult(True, "policy runtime started")

    async def stop(self, local: bool) -> PolicyCommandResult:
        if not local:
            return await _remote_policy_command("stop")

        async with self._lock:
            self._running = False
            self._paused = False
            if self._loop_task is not None:
                self._loop_task.cancel()
                self._loop_task = None

        robot_stop = await robot_client.stop(local=True)
        if robot_stop.success:
            return PolicyCommandResult(True, "policy runtime stopped")
        return PolicyCommandResult(False, robot_stop.message)

    async def refresh_remote_status(self) -> PolicyStatus:
        remote_status = await _remote_policy_status()
        return remote_status or self.status()

    async def run_policy(self, observation: Any) -> Any:
        if self._policy is None:
            await asyncio.to_thread(self._load_policy)
        started_at = time.perf_counter()
        action = await asyncio.to_thread(self._infer_action, observation)
        elapsed = time.perf_counter() - started_at
        if elapsed > 0:
            self._loop_hz = round(1.0 / elapsed, 2)
        self._last_action = action
        return action

    async def _inference_loop(self) -> None:
        target_period = 1.0 / max(self._inference_hz, 1.0)
        while self._running:
            loop_started = time.perf_counter()
            state = await robot_client.get_state(local=True)
            if state is None:
                self._paused = True
                self._last_error = "robot disconnected; policy loop paused"
                await asyncio.sleep(target_period)
                continue

            observation = state.observation
            if observation is None:
                self._paused = True
                self._last_error = "robot observation unavailable; policy loop paused"
                await asyncio.sleep(target_period)
                continue

            self._paused = False
            action = await self.run_policy(observation)
            action_result = await robot_client.send_action(action, local=True)
            if not action_result.success:
                self._paused = True
                self._last_error = action_result.message
                await asyncio.sleep(target_period)
                continue

            elapsed = time.perf_counter() - loop_started
            if elapsed > 0:
                self._loop_hz = round(1.0 / elapsed, 2)
            await asyncio.sleep(max(0.0, target_period - elapsed))

    def _load_policy(self) -> None:
        if self._policy is not None:
            return

        model_path = _find_policy_model_path()
        self._model_path = str(model_path)

        try:
            self._policy = _load_lerobot_act_policy(model_path)
        except Exception as exc:
            raise RuntimeError(
                "Unable to load LeRobot ACT policy. Install lerobot/torch and set "
                "LEROBOT_POLICY_MODEL_PATH to outputs/train/**/pretrained_model."
            ) from exc

    def _infer_action(self, observation: Any) -> Any:
        if self._policy is None:
            raise RuntimeError("policy is not loaded")

        if hasattr(self._policy, "select_action"):
            action = self._policy.select_action(observation)
        elif hasattr(self._policy, "predict_action"):
            action = self._policy.predict_action(observation)
        elif callable(self._policy):
            action = self._policy(observation)
        else:
            raise RuntimeError("loaded policy has no supported inference method")

        return _to_jsonable(action)


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _find_policy_model_path() -> Path:
    configured = os.getenv("LEROBOT_POLICY_MODEL_PATH")
    if configured:
        path = Path(configured)
        if path.exists():
            return path
        raise RuntimeError(f"LEROBOT_POLICY_MODEL_PATH does not exist: {configured}")

    candidates = sorted(
        glob.glob("outputs/train/**/pretrained_model", recursive=True),
        key=lambda item: os.path.getmtime(item),
        reverse=True,
    )
    if candidates:
        return Path(candidates[0])

    raise RuntimeError("No LeRobot pretrained_model found under outputs/train/**/pretrained_model.")


def _load_lerobot_act_policy(model_path: Path) -> Any:
    try:
        from lerobot.common.policies.act.modeling_act import ACTPolicy
    except Exception:
        from lerobot.common.policies.act import ACTPolicy

    policy = ACTPolicy.from_pretrained(str(model_path))
    if hasattr(policy, "eval"):
        policy.eval()
    return policy


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    return value


def _remote_base_url() -> Optional[str]:
    base_url = os.getenv("POLICY_RUNTIME_REMOTE_URL") or os.getenv("ROBOT_PC_BASE_URL")
    if base_url:
        return base_url.rstrip("/")

    robot_pc_ip = os.getenv("ROBOT_PC_IP")
    if robot_pc_ip:
        return f"http://{robot_pc_ip}:8000"
    return None


async def _remote_policy_command(command: str) -> PolicyCommandResult:
    base_url = _remote_base_url()
    if not base_url:
        return PolicyCommandResult(False, "remote policy runtime endpoint is not configured")

    url = f"{base_url}/policy/{command}"
    try:
        response = await asyncio.to_thread(
            requests.post,
            url,
            json={},
            timeout=REMOTE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json() if response.content else {}
    except Exception as exc:
        return PolicyCommandResult(False, f"remote policy runtime {command} failed: {exc}")

    return PolicyCommandResult(
        success=bool(payload.get("success", True)),
        message=payload.get("message") or f"remote policy runtime {command} accepted",
    )


async def _remote_policy_status() -> Optional[PolicyStatus]:
    base_url = _remote_base_url()
    if not base_url:
        return None

    try:
        response = await asyncio.to_thread(
            requests.get,
            f"{base_url}/policy/status",
            timeout=REMOTE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return None

    return PolicyStatus(**payload)


policy_runtime_service = PolicyRuntimeService()

