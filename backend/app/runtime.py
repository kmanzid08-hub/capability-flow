from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

from app.core.config import get_settings


def _terminate(process: subprocess.Popen[bytes] | None, *, timeout: float = 10.0) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5.0)


def main() -> int:
    """Run the HTTP server and durable AI worker as separate OS processes."""
    settings = get_settings()
    port = os.environ.get("PORT", "10000")

    worker: subprocess.Popen[bytes] | None = None
    if settings.ai_job_worker_enabled:
        worker = subprocess.Popen([sys.executable, "-m", "app.workers.ai_job_worker"])

    web = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            port,
        ]
    )

    stopping = False

    def handle_signal(signum: int, _frame: object) -> None:
        nonlocal stopping
        if stopping:
            return
        stopping = True
        if web.poll() is None:
            web.send_signal(signum)
        if worker is not None and worker.poll() is None:
            worker.send_signal(signum)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        while True:
            web_code = web.poll()
            if web_code is not None:
                return int(web_code)

            if worker is not None:
                worker_code = worker.poll()
                if worker_code is not None:
                    if stopping:
                        return 0
                    _terminate(web)
                    return int(worker_code) if worker_code else 1

            time.sleep(0.5)
    finally:
        _terminate(web)
        _terminate(worker)


if __name__ == "__main__":
    raise SystemExit(main())
