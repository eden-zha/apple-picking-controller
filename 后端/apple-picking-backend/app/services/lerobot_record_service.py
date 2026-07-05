import asyncio
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.models import PolicyStatus, TargetMaturity


STOP_TIMEOUT_SECONDS = 8.0
SCRIPT_BY_TARGET = {
    TargetMaturity.yellow: "run_lerobot_yellow.bat",
    TargetMaturity.red: "run_lerobot_red.bat",
}


@dataclass
class LeRobotRecordResult:
    success: bool
    message: str


class LeRobotRecordService:
    def __init__(self) -> None:
        self._process = None  # type: Optional[subprocess.Popen]
        self._script_path = None  # type: Optional[str]
        self._log_file = None
        self._last_error = None  # type: Optional[str]
        self._lock = asyncio.Lock()

    def status(self) -> PolicyStatus:
        running = self._is_running()
        return PolicyStatus(
            running=running,
            loaded=running,
            paused=False,
            model_path=self._script_path,
            inference_hz=0,
            loop_hz=0,
            last_error=self._last_error,
        )

    async def start(self, target_maturity: Optional[TargetMaturity]) -> LeRobotRecordResult:
        async with self._lock:
            if self._is_running():
                return LeRobotRecordResult(True, "lerobot.record is already running")

            self._cleanup_finished_process()
            try:
                script_path = _resolve_start_script(target_maturity)
            except Exception as exc:
                self._last_error = str(exc)
                self._script_path = None
                return LeRobotRecordResult(False, self._last_error)

            self._script_path = str(script_path)
            self._last_error = None

            try:
                command = _popen_command(script_path)
                self._open_log_file()
                self._write_log_header(script_path, command)
                self._process = subprocess.Popen(
                    command,
                    cwd=str(_backend_dir()),
                    stdout=self._log_file,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    shell=False,
                    env=os.environ.copy(),
                    creationflags=_creation_flags(),
                )
                await asyncio.sleep(0.5)
                if self._process.poll() is not None:
                    code = self._process.returncode
                    self._last_error = f"lerobot.record exited immediately with code {code}; see {_log_path()}"
                    self._process = None
                    self._close_log_file()
                    return LeRobotRecordResult(False, self._last_error)
            except Exception as exc:
                self._last_error = f"{type(exc).__name__}: {exc}"
                self._close_log_file()
                return LeRobotRecordResult(False, f"lerobot.record start failed: {self._last_error}")

            return LeRobotRecordResult(True, f"lerobot.record started via script; script={script_path}; log={_log_path()}")

    async def stop(self) -> LeRobotRecordResult:
        async with self._lock:
            if self._process is None:
                self._close_log_file()
                return LeRobotRecordResult(True, "lerobot.record is not running")

            if self._process.poll() is not None:
                code = self._process.returncode
                self._last_error = f"lerobot.record exited with code {code}"
                self._process = None
                self._close_log_file()
                return LeRobotRecordResult(True, self._last_error)

            pid = self._process.pid
            self._process.terminate()
            try:
                self._process.wait(timeout=STOP_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                _kill_process_tree(pid)
                try:
                    self._process.kill()
                    self._process.wait(timeout=3)
                except Exception:
                    pass

            self._process = None
            self._close_log_file()
            return LeRobotRecordResult(True, "lerobot.record stopped")

    def _is_running(self) -> bool:
        if self._process is None:
            return False
        code = self._process.poll()
        if code is None:
            return True
        self._last_error = f"lerobot.record exited with code {code}"
        self._process = None
        self._close_log_file()
        return False

    def _cleanup_finished_process(self) -> None:
        if self._process is not None and self._process.poll() is not None:
            self._last_error = f"lerobot.record exited with code {self._process.returncode}"
            self._process = None
            self._close_log_file()

    def _open_log_file(self) -> None:
        _log_path().parent.mkdir(parents=True, exist_ok=True)
        self._log_file = open(_log_path(), "a", encoding="utf-8", buffering=1)

    def _close_log_file(self) -> None:
        if self._log_file is not None:
            try:
                self._log_file.flush()
                self._log_file.close()
            finally:
                self._log_file = None

    def _write_log_header(self, script_path: Path, command: list[str]) -> None:
        if self._log_file is None:
            return
        self._log_file.write("\n\n===== lerobot.record started =====\n")
        self._log_file.write(f"sys.executable={sys.executable}\n")
        self._log_file.write(f"cwd={_backend_dir()}\n")
        self._log_file.write("source=script\n")
        self._log_file.write(f"script={script_path}\n")
        self._log_file.write(f"command={_display_command(command)}\n")


def _resolve_start_script(target_maturity: Optional[TargetMaturity]) -> Path:
    configured = _env("LEROBOT_RECORD_SCRIPT")
    if configured:
        script_path = _resolve_script_path(configured)
    else:
        if target_maturity is None:
            raise RuntimeError("target_maturity is required to select LeRobot record script")
        script_name = SCRIPT_BY_TARGET.get(target_maturity)
        if script_name is None:
            raise RuntimeError(f"Unsupported target_maturity for LeRobot record script: {target_maturity}")
        script_path = (_backend_dir() / script_name).resolve()

    if not script_path.exists():
        raise RuntimeError(f"LeRobot record script not found: {script_path}")
    return script_path


def _resolve_script_path(script: str) -> Path:
    script_path = Path(script).expanduser()
    if script_path.is_absolute():
        return script_path
    return (_backend_dir() / script_path).resolve()


def _popen_command(script_path: Path) -> list[str]:
    if os.name == "nt":
        return [
            os.environ.get("COMSPEC", "cmd.exe"),
            "/d",
            "/s",
            "/c",
            "call",
            str(script_path),
        ]
    return [str(script_path)]


def _display_command(command: list[str]) -> str:
    return " ".join(command)


def _env(name: str) -> Optional[str]:
    value = os.getenv(name)
    if value and value.strip():
        return value.strip()
    return None


def _backend_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _log_path() -> Path:
    return _project_root() / "logs" / "lerobot_record.log"


def _creation_flags() -> int:
    if os.name == "nt":
        return getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    return 0


def _kill_process_tree(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


lerobot_record_service = LeRobotRecordService()