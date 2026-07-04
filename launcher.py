import argparse
import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "后端" / "apple-picking-backend"
FRONTEND_ROOT = ROOT_DIR / "前端"
LOG_DIR = ROOT_DIR / "logs"

BACKEND_PORT = 8000
FRONTEND_PORT = 5173
SKIP_DIR_NAMES = {"node_modules", "dist", "build", ".git", ".vite", ".vite-temp", "__pycache__"}
SOURCE_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".html", ".css"}


def log(message):
    print(message, flush=True)


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def choose_backend_python():
    candidates = [
        BACKEND_DIR / ".venv" / "Scripts" / "python.exe",
        BACKEND_DIR / "venv" / "Scripts" / "python.exe",
        ROOT_DIR / "venv" / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable or "python"


def iter_frontend_project_candidates():
    if not FRONTEND_ROOT.exists():
        return

    for path in FRONTEND_ROOT.rglob("*"):
        if not path.is_dir():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.relative_to(FRONTEND_ROOT).parts):
            continue
        if (path / "package.json").exists() or (path / "index.html").exists():
            yield path


def read_text_safely(path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return ""


def frontend_signal_score(candidate):
    score = 0
    package_json = candidate / "package.json"
    index_html = candidate / "index.html"

    if package_json.exists():
        score += 100
        package_text = read_text_safely(package_json)
        if '"dev"' in package_text:
            score += 40
        if "vite" in package_text:
            score += 20

    if index_html.exists():
        score += 50

    signal_text = []
    for source_file in candidate.rglob("*"):
        if not source_file.is_file():
            continue
        relative_parts = source_file.relative_to(candidate).parts
        if any(part in SKIP_DIR_NAMES for part in relative_parts):
            continue
        if source_file.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        signal_text.append(read_text_safely(source_file))

    combined = "\n".join(signal_text)
    if "ws/vision" in combined:
        score += 500
    if "/start_task" in combined:
        score += 120
    if "/stop" in combined:
        score += 120
    if "target_maturity" in combined:
        score += 60

    return score


def find_frontend_dir():
    candidates = list(iter_frontend_project_candidates() or [])
    if not candidates:
        return None

    ranked = sorted(
        candidates,
        key=lambda candidate: (
            frontend_signal_score(candidate),
            (candidate / "package.json").stat().st_mtime if (candidate / "package.json").exists() else 0,
            candidate.stat().st_mtime,
        ),
        reverse=True,
    )
    return ranked[0]


def open_log_file(name):
    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / name
    return open(log_path, "a", encoding="utf-8", buffering=1)


def start_process(name, command, cwd, log_name, env=None):
    try:
        log_file = open_log_file(log_name)
        log_file.write(f"\n\n===== {name} started at {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n")
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            shell=False,
            env=env,
        )
        log(f"[INFO] {name} process started. PID={process.pid}. Log: {LOG_DIR / log_name}")
        return process
    except Exception as exc:
        log(f"[ERROR] Failed to start {name}: {exc}")
        return None


def start_backend():
    log("[INFO] Starting backend...")
    if not BACKEND_DIR.exists():
        log(f"[ERROR] Backend directory not found: {BACKEND_DIR}")
        return None
    if is_port_in_use(BACKEND_PORT):
        log(f"[WARN] Port {BACKEND_PORT} is already in use. Backend may already be running.")
        return None

    python_exe = choose_backend_python()
    command = [
        python_exe,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(BACKEND_PORT),
    ]
    return start_process("backend", command, BACKEND_DIR, "backend.log")


def start_frontend(robot_backend_url):
    log("[INFO] Starting frontend...")
    frontend_dir = find_frontend_dir()
    if frontend_dir is None:
        log(f"[ERROR] Frontend project not found under: {FRONTEND_ROOT}")
        return None
    log(f"[INFO] Frontend project selected: {frontend_dir}")
    if is_port_in_use(FRONTEND_PORT):
        log(f"[WARN] Port {FRONTEND_PORT} is already in use. Frontend may already be running.")
        return None

    env = os.environ.copy()
    if robot_backend_url:
        env["VITE_ROBOT_BACKEND_URL"] = robot_backend_url.rstrip("/")
        log(f"[INFO] Frontend will connect to backend: {env['VITE_ROBOT_BACKEND_URL']}")

    command = ["npm.cmd", "run", "dev", "--", "--host", "0.0.0.0"]
    return start_process("frontend", command, frontend_dir, "frontend.log", env=env)


def report_status(name, port, process):
    if is_port_in_use(port):
        log(f"[INFO] {name} is available on port {port}.")
        return
    if process is not None and process.poll() is not None:
        log(f"[ERROR] {name} exited early with code {process.returncode}. Please check logs.")
        return
    log(f"[INFO] {name} is starting. Please wait a moment and check logs if it does not become ready.")


def parse_args():
    parser = argparse.ArgumentParser(description="Apple picking robot launcher")
    parser.add_argument(
        "--role",
        choices=["all", "backend", "frontend"],
        default="all",
        help="all: robot PC single-machine demo; backend: robot PC only; frontend: PC1 only",
    )
    parser.add_argument(
        "--robot-backend-url",
        default=os.getenv("VITE_ROBOT_BACKEND_URL") or os.getenv("ROBOT_BACKEND_URL"),
        help="Robot PC backend URL for frontend mode, for example http://192.168.1.20:8000",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the frontend page automatically.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    log(f"[INFO] Launcher started. role={args.role}")

    backend_process = None
    frontend_process = None

    if args.role in {"all", "backend"}:
        backend_process = start_backend()

    if args.role in {"all", "frontend"}:
        robot_backend_url = args.robot_backend_url
        if args.role == "all" and not robot_backend_url:
            robot_backend_url = f"http://127.0.0.1:{BACKEND_PORT}"
        if args.role == "frontend" and not robot_backend_url:
            log("[ERROR] Frontend-only mode requires --robot-backend-url or VITE_ROBOT_BACKEND_URL.")
            return
        frontend_process = start_frontend(robot_backend_url)

    log("[INFO] Checking service status...")
    time.sleep(3)
    if args.role in {"all", "backend"}:
        report_status("backend", BACKEND_PORT, backend_process)
    if args.role in {"all", "frontend"}:
        report_status("frontend", FRONTEND_PORT, frontend_process)

    if args.role in {"all", "frontend"} and not args.no_browser:
        frontend_url = f"http://localhost:{FRONTEND_PORT}"
        log(f"[INFO] Opening browser: {frontend_url}")
        time.sleep(1)
        try:
            webbrowser.open(frontend_url)
        except Exception as exc:
            log(f"[WARN] Could not open browser automatically: {exc}")

    log("[INFO] Startup complete.")
    if args.role == "backend":
        log(f"[INFO] Robot PC backend is http://<robot_pc_ip>:{BACKEND_PORT}")
    if args.role in {"all", "frontend"}:
        log(f"[INFO] Frontend is http://localhost:{FRONTEND_PORT}")
    log("[INFO] Close started processes manually when you are finished.")


if __name__ == "__main__":
    main()
