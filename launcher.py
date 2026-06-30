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
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"
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
    if "local" in combined and "remote" in combined:
        score += 500
    if "/start_task" in combined:
        score += 120
    if "/stop" in combined:
        score += 120
    if "target_mode" in combined:
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


def start_process(name, command, cwd, log_name):
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
        "127.0.0.1",
        "--port",
        str(BACKEND_PORT),
    ]
    return start_process("backend", command, BACKEND_DIR, "backend.log")


def start_frontend():
    log("[INFO] Starting frontend...")
    frontend_dir = find_frontend_dir()
    if frontend_dir is None:
        log(f"[ERROR] Frontend project not found under: {FRONTEND_ROOT}")
        return None
    log(f"[INFO] Frontend project selected: {frontend_dir}")
    if is_port_in_use(FRONTEND_PORT):
        log(f"[WARN] Port {FRONTEND_PORT} is already in use. Frontend may already be running.")
        return None

    command = ["npm.cmd", "run", "dev"]
    return start_process("frontend", command, frontend_dir, "frontend.log")


def report_status(name, port, process):
    if is_port_in_use(port):
        log(f"[INFO] {name} is available on port {port}.")
        return
    if process is not None and process.poll() is not None:
        log(f"[ERROR] {name} exited early with code {process.returncode}. Please check logs.")
        return
    log(f"[INFO] {name} is starting. Please wait a moment and check logs if it does not become ready.")


def main():
    log("[INFO] One-click launcher started.")

    backend_process = start_backend()
    frontend_process = start_frontend()

    log("[INFO] Checking service status...")
    time.sleep(3)
    report_status("backend", BACKEND_PORT, backend_process)
    report_status("frontend", FRONTEND_PORT, frontend_process)

    log(f"[INFO] Opening browser: {FRONTEND_URL}")
    time.sleep(1)
    try:
        webbrowser.open(FRONTEND_URL)
    except Exception as exc:
        log(f"[WARN] Could not open browser automatically: {exc}")

    log("[INFO] Startup complete. You can use the web page now.")
    log("[INFO] Close backend/frontend processes manually when you are finished.")


if __name__ == "__main__":
    main()
