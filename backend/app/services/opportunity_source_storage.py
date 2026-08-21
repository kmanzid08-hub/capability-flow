import os
import uuid
from pathlib import Path

from app.core.opportunity_config import get_opportunity_intelligence_settings


class OpportunitySourceStorage:
    def __init__(self) -> None:
        self.settings = get_opportunity_intelligence_settings()

    def store(
        self,
        *,
        organization_id: uuid.UUID,
        opportunity_id: uuid.UUID,
        content: bytes,
        filename: str,
    ) -> tuple[str, str]:
        suffix = Path(filename).suffix.lower()[:20]
        stored_filename = f"{uuid.uuid4().hex}{suffix}"
        directory = (
            self.settings.opportunity_source_storage_root
            / str(organization_id)
            / str(opportunity_id)
        )
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / stored_filename
        path.write_bytes(content)
        return stored_filename, str(path)

    def resolve(self, storage_path: str) -> Path:
        root = self.settings.opportunity_source_storage_root.resolve()
        path = Path(storage_path).resolve()
        if root != path and root not in path.parents:
            raise ValueError("Invalid opportunity source storage path")
        return path

    def delete(self, storage_path: str | None) -> None:
        if not storage_path:
            return
        path = self.resolve(storage_path)
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
