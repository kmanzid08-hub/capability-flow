import uuid
from pathlib import Path
from typing import Any, BinaryIO

import boto3  # type: ignore[import-untyped]
from boto3.s3.transfer import TransferConfig  # type: ignore[import-untyped]
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
        self.transfer_config = TransferConfig(
            multipart_threshold=8 * 1024 * 1024,
            multipart_chunksize=8 * 1024 * 1024,
            max_concurrency=4,
            use_threads=True,
        )

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

    async def store_fileobj(
        self,
        *,
        organization_id: uuid.UUID,
        opportunity_id: uuid.UUID,
        source: BinaryIO,
        filename: str,
        file_size: int,
        mime_type: str | None = None,
    ) -> tuple[str, str]:
        if file_size <= 0:
            raise ValueError("Empty opportunity files are not allowed")
        if file_size > self.settings.opportunity_max_source_bytes:
            raise ValueError("Opportunity document exceeds the configured size limit")

        suffix = Path(filename).suffix.lower()[:20]
        stored_filename = f"{uuid.uuid4().hex}{suffix}"
        source.seek(0)

        if self.app_settings.storage_backend == "r2":
            key = f"opportunity-sources/{organization_id}/{opportunity_id}/{stored_filename}"
            assert self.client is not None
            kwargs: dict[str, object] = {"Config": self.transfer_config}
            if mime_type:
                kwargs["ExtraArgs"] = {"ContentType": mime_type}
            await run_in_threadpool(
                self.client.upload_fileobj,
                source,
                self.app_settings.r2_bucket_name,
                key,
                **kwargs,
            )
            source.seek(0)
            return stored_filename, f"r2://{key}"

        directory = (
            self.settings.opportunity_source_storage_root
            / str(organization_id)
            / str(opportunity_id)
        )
        await run_in_threadpool(directory.mkdir, 0o755, True, True)
        path = directory / stored_filename
        await run_in_threadpool(self._copy_stream, source, path)
        source.seek(0)
        return stored_filename, str(path)

    @staticmethod
    def _copy_stream(source: BinaryIO, path: Path) -> None:
        source.seek(0)
        with path.open("wb") as output:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)

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
