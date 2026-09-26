import uuid
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.services.profile_ai import ProfileAIService


@pytest.mark.asyncio
async def test_overlong_ai_skill_is_rejected_before_database_write() -> None:
    service = ProfileAIService.__new__(ProfileAIService)
    service.organization_id = uuid.uuid4()
    service.session = object()

    suggestion = SimpleNamespace(
        category="skill",
        payload={
            "name": "x" * 151,
            "proficiency": None,
            "years_experience": None,
            "last_used_year": None,
        },
    )

    with pytest.raises(ValidationError) as captured:
        await service._apply(uuid.uuid4(), suggestion)  # type: ignore[arg-type]

    message = service._format_validation_error(captured.value)
    assert "at most 150 characters" in message
    assert "Edit this suggestion before accepting" in message
