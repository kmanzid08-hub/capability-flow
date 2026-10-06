import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings

if TYPE_CHECKING:
    from app.workers.ai_job_worker import AIJobWorker

settings = get_settings()


def _embedded_worker_enabled() -> bool:
    value = os.getenv("AI_JOB_WORKER_EMBEDDED", "true").strip().lower()
    return settings.ai_job_worker_enabled and value in {"1", "true", "yes", "on"}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    worker: AIJobWorker | None = None
    if _embedded_worker_enabled():
        # Keep worker-only imports out of the web process when Render runs the
        # durable worker as a sibling process. This reduces duplicate memory use.
        from app.workers.ai_job_worker import AIJobWorker as RuntimeAIJobWorker

        worker = RuntimeAIJobWorker(settings)
        await worker.start()
    app.state.ai_job_worker = worker
    try:
        yield
    finally:
        if worker is not None:
            await worker.stop()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)
