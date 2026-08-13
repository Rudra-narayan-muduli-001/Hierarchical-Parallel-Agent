"""Launch the Parallel Mind GUI + backend with a single command.

Usage:
    python run.py

Starts the FastAPI backend (uvicorn, :8000) and the Vite dev server
(gui/, :3000), loads .env, then opens the browser at http://localhost:3000.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GUI_DIR = ROOT / "gui"
SRC_DIR = ROOT / "src"
BACKEND_URL = "http://localhost:3000"
BACKEND_PORT = 8000
GUI_PORT = 3000

LOGS_DIR = ROOT / ".logs"


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env", override=False)
    except ImportError:
        env_path = ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


def _free_port(port: int) -> None:
    if os.name != "nt":
        return
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    f"Get-NetTCPConnection -LocalPort {port} -State Listen "
                    f"-ErrorAction SilentlyContinue | "
                    f"ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force }}"
                ),
            ],
            capture_output=True,
            timeout=15,
        )
    except Exception:
        pass


def _wait_for_port(port: int, timeout: int = 40) -> bool:
    import socket

    candidates = [
        (socket.AF_INET, "127.0.0.1"),
        (socket.AF_INET6, "::1"),
    ]
    deadline = time.time() + timeout
    while time.time() < deadline:
        for family, host in candidates:
            try:
                with socket.socket(family, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    if sock.connect_ex((host, port)) == 0:
                        return True
            except (OSError, OverflowError):
                continue
        time.sleep(0.5)
    return False


def main() -> int:
    _load_dotenv()
    LOGS_DIR.mkdir(exist_ok=True)

    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    _free_port(BACKEND_PORT)
    _free_port(GUI_PORT)

    backend_log = open(LOGS_DIR / "backend.log", "a", encoding="utf-8")
    gui_log = open(LOGS_DIR / "gui.log", "a", encoding="utf-8")

    backend = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "hierarchy.api.server:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(BACKEND_PORT),
        ],
        cwd=str(ROOT),
        env=env,
        stdout=backend_log,
        stderr=subprocess.STDOUT,
    )

    gui = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(GUI_DIR),
        stdout=gui_log,
        stderr=subprocess.STDOUT,
        shell=True,
    )

    processes = [backend, gui]
    try:
        backend_ok = _wait_for_port(BACKEND_PORT)
        gui_ok = _wait_for_port(GUI_PORT)
        if not backend_ok:
            print("[run.py] Backend failed to start on "
                  f":{BACKEND_PORT} — check .logs/backend.log")
        if not gui_ok:
            print("[run.py] GUI failed to start on "
                  f":{GUI_PORT} — check .logs/gui.log")
        if backend_ok and gui_ok:
            print(f"[run.py] Backend on http://localhost:{BACKEND_PORT}")
            print(f"[run.py] GUI on {BACKEND_URL}")
            webbrowser.open(BACKEND_URL)
            print("[run.py] Press Ctrl+C to stop everything.")
        while True:
            time.sleep(1)
            for proc in list(processes):
                if proc.poll() is not None:
                    processes.remove(proc)
                    print(f"[run.py] Process exited early (code "
                          f"{proc.returncode}) — check the .logs/ files.")
    except KeyboardInterrupt:
        print("\n[run.py] Shutting down...")
    finally:
        for proc in processes:
            proc.terminate()
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())