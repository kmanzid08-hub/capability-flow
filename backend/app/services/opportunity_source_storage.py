import uuid
from pathlib import Path
from typing import Any

import boto3  # type: ignore[import-untyped]
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.core.opportunity_config import (
    get_opportunity_intelligence_settings,
)
from app.services.document_storage import (
    StorageConfigurationError,
)


class OpportunitySourceStorage:
    def __init__(self) -> None:
        self.settings = get_opportunity_intelligence_settings()
        self.app_settings = get_settings()

        self.client: Any | None = None

        if self.app_settings.storage_backend == "r2":
            if not all(
                (
                    self.app_settings.r2_endpoint_url,
                    self.app_settings.r2_access_key_id,
                    self.app_settings.r2_secret_access_key,
                    self.app_settings.r2_bucket_name,
                )
            ):
                raise StorageConfigurationError(
                    "R2 storage is enabled but one or more R2 settings are missing"
                )

            self.client = boto3.client(
                service_name="s3",
                endpoint_url=(self.app_settings.r2_endpoint_url),
                aws_access_key_id=(self.app_settings.r2_access_key_id),
                aws_secret_access_key=(self.app_settings.r2_secret_access_key),
                region_name="auto",
            )

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

        if self.app_settings.storage_backend == "r2":
            key = f"opportunity-sources/{organization_id}/{opportunity_id}/{stored_filename}"

            assert self.client is not None

            self.client.put_object(
                Bucket=(self.app_settings.r2_bucket_name),
                Key=key,
                Body=content,
            )

            return (
                stored_filename,
                f"r2://{key}",
            )

        directory = (
            self.settings.opportunity_source_storage_root
            / str(organization_id)
            / str(opportunity_id)
        )
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        path = directory / stored_filename
        path.write_bytes(content)

        return (
            stored_filename,
            str(path),
        )

    async def read(
        self,
        storage_path: str,
    ) -> bytes:
        if storage_path.startswith("r2://"):
            if self.client is None:
                raise FileNotFoundError("R2 storage is not configured")

            key = storage_path.removeprefix("r2://")

            try:
                response: Any = await run_in_threadpool(
                    self.client.get_object,
                    Bucket=(self.app_settings.r2_bucket_name),
                    Key=key,
                )
            except Exception as exc:
                raise FileNotFoundError("Stored source snapshot is missing") from exc

            body: Any = response["Body"]
            content: bytes = await run_in_threadpool(body.read)
            return content

        path = self.resolve(storage_path)

        if not path.is_file():
            raise FileNotFoundError("Stored source snapshot is missing")

        return await run_in_threadpool(path.read_bytes)

    def resolve(
        self,
        storage_path: str,
    ) -> Path:
        if storage_path.startswith("r2://"):
            raise ValueError("R2 objects do not have a local filesystem path")

        root = self.settings.opportunity_source_storage_root.resolve()
        path = Path(storage_path).resolve()

        if root != path and root not in path.parents:
            raise ValueError("Invalid opportunity source storage path")

        return path

    def delete(
        self,
        storage_path: str | None,
    ) -> None:
        if not storage_path:
            return

        if storage_path.startswith("r2://"):
            if self.client is None:
                return

            key = storage_path.removeprefix("r2://")

            self.client.delete_object(
                Bucket=(self.app_settings.r2_bucket_name),
                Key=key,
            )
            return

        path = self.resolve(storage_path)

        try:
            path.unlink()
        except FileNotFoundError:
            pass
