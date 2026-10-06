from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time

from app.core.config import get_settings

logger = logging.getLogger("capability_flow.runtime")


def _terminate(process: subprocess.Popen[bytes] | None, *, timeout: float = 10.0) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5.0)


def _start_worker() -> subprocess.Popen[bytes]:
    logger.info("Starting durable AI worker process")
    return subprocess.Popen([sys.executable, "-m", "app.workers.ai_job_worker"])


def main() -> int:
    """Run the HTTP server and durable AI worker as sibling OS processes."""
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    port = os.environ.get("PORT", "10000")

    worker: subprocess.Popen[bytes] | None = None
    if settings.ai_job_worker_enabled:
        worker = _start_worker()

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
    restart_delay = 5.0
    next_worker_restart_at = 0.0
    worker_started_at = time.monotonic()

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
                    logger.error(
                        "AI worker exited unexpectedly with status %s; web API remains online",
                        worker_code,
                    )
                    alive_for = time.monotonic() - worker_started_at
                    if alive_for >= 60.0:
                        restart_delay = 5.0
                    worker = None
                    next_worker_restart_at = time.monotonic() + restart_delay
                    restart_delay = min(restart_delay * 2.0, 60.0)

            if (
                worker is None
                and settings.ai_job_worker_enabled
                and not stopping
                and time.monotonic() >= next_worker_restart_at
            ):
                worker = _start_worker()
                worker_started_at = time.monotonic()

            time.sleep(0.5)
    finally:
        _terminate(web)
        _terminate(worker)


if __name__ == "__main__":
    raise SystemExit(main())
