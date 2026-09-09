import asyncio
import uuid
from contextlib import suppress

from app.services.analysis_control import (
    abort_active_analysis,
    register_analysis_task,
    unregister_analysis_task,
)


async def test_abort_active_analysis_cancels_registered_task() -> None:
    organization_id = uuid.uuid4()
    user_id = uuid.uuid4()
    person_id = uuid.uuid4()
    task = asyncio.create_task(asyncio.sleep(60))

    register_analysis_task(organization_id, user_id, person_id, task)
    try:
        assert abort_active_analysis(organization_id, user_id, person_id) == 1
        with suppress(asyncio.CancelledError):
            await task
        assert task.cancelled()
    finally:
        unregister_analysis_task(organization_id, user_id, person_id, task)


def test_abort_active_analysis_is_empty_when_nothing_is_running() -> None:
    assert abort_active_analysis(uuid.uuid4(), uuid.uuid4(), uuid.uuid4()) == 0
