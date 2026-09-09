import asyncio
import uuid
from collections import defaultdict
from typing import Any

AnalysisKey = tuple[uuid.UUID, uuid.UUID, uuid.UUID]

_active_analysis_tasks: dict[AnalysisKey, set[asyncio.Task[Any]]] = defaultdict(set)


def _key(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    person_id: uuid.UUID,
) -> AnalysisKey:
    return organization_id, user_id, person_id


def register_analysis_task(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    person_id: uuid.UUID,
    task: asyncio.Task[Any],
) -> None:
    _active_analysis_tasks[_key(organization_id, user_id, person_id)].add(task)


def unregister_analysis_task(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    person_id: uuid.UUID,
    task: asyncio.Task[Any],
) -> None:
    key = _key(organization_id, user_id, person_id)
    tasks = _active_analysis_tasks.get(key)
    if tasks is None:
        return
    tasks.discard(task)
    if not tasks:
        _active_analysis_tasks.pop(key, None)


def abort_active_analysis(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    person_id: uuid.UUID,
) -> int:
    tasks = list(_active_analysis_tasks.get(_key(organization_id, user_id, person_id), ()))
    cancelled = 0
    for task in tasks:
        if task.done():
            continue
        task.cancel()
        cancelled += 1
    return cancelled
