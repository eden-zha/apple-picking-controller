import asyncio
import glob
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from app.adapters import robot_client
from app.models import PolicyStatus, TargetMaturity
from app.services.vision_service import vision_service


DEFAULT_TARGET_HZ = 20.0
logger = logging.getLogger(__name__)


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
        self._device = None  # type: Optional[str]
        self._target_maturity = None  # type: Optional[TargetMaturity]
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

    async def start(self, target_maturity: Optional[TargetMaturity]) -> PolicyCommandResult:
        if target_maturity is None:
            return PolicyCommandResult(False, "target_maturity is required before starting policy runtime")

        async with self._lock:
            if self._running:
                return PolicyCommandResult(True, "policy runtime already running")

            self._target_maturity = target_maturity
            try:
                await asyncio.to_thread(self._load_policy)
                robot_start = await robot_client.start()
                if not robot_start.success:
                    self._last_error = robot_start.message
                    return PolicyCommandResult(False, robot_start.message)
            except Exception as exc:
                error_message = _format_exception_message(exc)
                logger.exception("Policy runtime start failed.")
                self._last_error = error_message
                return PolicyCommandResult(False, f"policy runtime start failed: {error_message}")

            self._running = True
            self._paused = False
            self._last_error = None
            self._loop_task = asyncio.create_task(self._inference_loop(target_maturity))
            return PolicyCommandResult(True, f"policy runtime started with target_maturity={target_maturity.value}")

    async def stop(self) -> PolicyCommandResult:
        async with self._lock:
            self._running = False
            self._paused = False
            self._target_maturity = None
            if self._loop_task is not None:
                self._loop_task.cancel()
                self._loop_task = None

        robot_stop = await robot_client.stop()
        if robot_stop.success:
            return PolicyCommandResult(True, "policy runtime stopped")
        return PolicyCommandResult(False, robot_stop.message)

    async def run_policy(self, observation: Any, target_maturity: TargetMaturity, target_apple: Optional[dict]) -> Any:
        if self._policy is None:
            await asyncio.to_thread(self._load_policy)
        policy_input = _build_policy_input(observation, target_maturity, target_apple)
        started_at = time.perf_counter()
        action = await asyncio.to_thread(self._infer_action, policy_input)
        elapsed = time.perf_counter() - started_at
        if elapsed > 0:
            self._loop_hz = round(1.0 / elapsed, 2)
        self._last_action = action
        return action

    async def _inference_loop(self, target_maturity: TargetMaturity) -> None:
        target_period = 1.0 / max(self._inference_hz, 1.0)
        while self._running:
            loop_started = time.perf_counter()
            state = await robot_client.get_state()
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

            target_apple = _select_target_apple(target_maturity)
            if target_apple is None:
                self._paused = True
                self._last_error = f"no {target_maturity.value} apple detected; arm command paused"
                await asyncio.sleep(target_period)
                continue

            self._paused = False
            action = await self.run_policy(observation, target_maturity, target_apple)
            action_result = await robot_client.send_action(action)
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
        cuda_available = _torch_cuda_is_available()
        device = _select_torch_device(cuda_available)
        self._device = device

        _print_policy_startup_details(model_path, cuda_available, device)

        try:
            self._policy = _load_lerobot_act_policy(model_path)
        except Exception as exc:
            self._last_error = _format_exception_message(exc)
            logger.exception("Failed to load LeRobot ACT policy from %s.", model_path)
            raise

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
            return path.resolve()
        raise RuntimeError(f"LEROBOT_POLICY_MODEL_PATH does not exist: {configured}")

    candidates = sorted(
        glob.glob("outputs/train/**/pretrained_model", recursive=True),
        key=lambda item: os.path.getmtime(item),
        reverse=True,
    )
    if candidates:
        return Path(candidates[0]).resolve()

    raise RuntimeError("No LeRobot pretrained_model found under outputs/train/**/pretrained_model.")


def _select_torch_device(cuda_available: bool) -> str:
    return "cuda" if cuda_available else "cpu"


def _torch_cuda_is_available() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        logger.exception("Unable to evaluate torch.cuda.is_available().")
        raise


def _load_lerobot_act_policy(model_path: Path) -> Any:
    ACTPolicy = _import_act_policy()
    policy = ACTPolicy.from_pretrained(str(model_path))
    if hasattr(policy, "eval"):
        policy.eval()
    return policy


def _import_act_policy() -> Any:
    attempts = [
        "lerobot.policies.act.modeling_act:ACTPolicy",
        "lerobot.policies.act:ACTPolicy",
        "lerobot.common.policies.act.modeling_act:ACTPolicy",
        "lerobot.common.policies.act:ACTPolicy",
    ]

    errors = []
    for target in attempts:
        module_name, attr_name = target.split(":", 1)
        try:
            module = __import__(module_name, fromlist=[attr_name])
            return getattr(module, attr_name)
        except Exception as exc:
            errors.append(f"{target}: {type(exc).__name__}: {exc}")

    raise ImportError("Could not import ACTPolicy from known LeRobot paths: " + "; ".join(errors))


def _print_policy_startup_details(model_path: Path, cuda_available: bool, device: str) -> None:
    details = [
        ("sys.executable", sys.executable),
        ("model_path", str(model_path)),
        ("torch.cuda.is_available()", cuda_available),
        ("device", device),
    ]
    for key, value in details:
        message = f"Policy runtime {key}: {value}"
        logger.info(message)
        print(message, flush=True)


def _format_exception_message(exc: Exception) -> str:
    return f"{exc.__class__.__name__}: {exc}"


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


def _build_policy_input(observation: Any, target_maturity: TargetMaturity, target_apple: Optional[dict]) -> Any:
    if isinstance(observation, dict):
        return {
            **observation,
            "target_maturity": target_maturity.value,
            "target_apple": target_apple,
        }
    return {
        "observation": observation,
        "target_maturity": target_maturity.value,
        "target_apple": target_apple,
    }


def _select_target_apple(target_maturity: TargetMaturity) -> Optional[dict]:
    snapshot = vision_service.snapshot()
    for apple in snapshot.apple_list:
        if apple.get("color") == target_maturity.value:
            return apple
    return None


policy_runtime_service = PolicyRuntimeService()
