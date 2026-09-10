import os
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Protocol

import boto3  # type: ignore[import-untyped]
from boto3.s3.transfer import TransferConfig  # type: ignore[import-untyped]
from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings

ALLOWED_MIME_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ".xls": "application/vnd.ms-excel",
    ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ".csv": "text/csv",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation"),
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".txt": "text/plain",
    ".rtf": "application/rtf",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".odp": "application/vnd.oasis.opendocument.presentation",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".text": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".tsv": "text/tab-separated-values",
    ".json": "application/json",
    ".jsonl": "application/x-ndjson",
    ".xml": "application/xml",
    ".html": "text/html",
    ".htm": "text/html",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12",
}


class InvalidDocumentFile(ValueError):
    pass


class DocumentTooLarge(ValueError):
    pass


class StorageConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredDocument:
    storage_key: str
    original_filename: str
    file_extension: str
    mime_type: str
    file_size: int


class DocumentStorage(Protocol):
    async def save(
        self,
        upload: UploadFile,
        organization_id: uuid.UUID,
        person_id: uuid.UUID,
    ) -> StoredDocument: ...

    async def read(
        self,
        storage_key: str,
    ) -> bytes: ...

    async def download_to_path(
        self,
        storage_key: str,
        destination: Path,
    ) -> None: ...

    async def delete(
        self,
        storage_key: str,
    ) -> None: ...


def is_temporary_document_filename(filename: str) -> bool:
    cleaned = filename.replace("\\", "/").split("/")[-1].strip()
    lowered = cleaned.lower()
    return cleaned.startswith("~$") or lowered.startswith(".~lock.")


def sanitize_filename(
    filename: str | None,
) -> str:
    if filename is None:
        raise InvalidDocumentFile("The uploaded file must have a filename")

    cleaned = filename.replace("\\", "/").split("/")[-1]
    cleaned = cleaned.replace("\x00", "").strip()

    if not cleaned:
        raise InvalidDocumentFile("The uploaded file must have a filename")

    if is_temporary_document_filename(cleaned):
        raise InvalidDocumentFile(
            "This appears to be a Microsoft Office or LibreOffice temporary file. "
            "Please upload the original document instead."
        )

    if len(cleaned) > 500:
        raise InvalidDocumentFile("The filename is too long")

    return cleaned


def _metadata_for_upload(
    upload: UploadFile,
) -> tuple[str, str, str]:
    original_filename = sanitize_filename(upload.filename)
    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_MIME_TYPES:
        raise InvalidDocumentFile(f"Files with extension '{extension or 'none'}' are not allowed")

    return (
        original_filename,
        extension,
        ALLOWED_MIME_TYPES[extension],
    )


class LocalDocumentStorage:
    def __init__(
        self,
        root: Path,
        max_file_size_bytes: int,
    ) -> None:
        self.root = root.resolve()
        self.max_file_size_bytes = max_file_size_bytes

    async def save(
        self,
        upload: UploadFile,
        organization_id: uuid.UUID,
        person_id: uuid.UUID,
    ) -> StoredDocument:
        (
            original_filename,
            extension,
            mime_type,
        ) = _metadata_for_upload(upload)

        storage_key = f"{organization_id}/{person_id}/{uuid.uuid4().hex}{extension}"

        destination = self._resolve_key(storage_key)

        await run_in_threadpool(
            destination.parent.mkdir,
            0o755,
            True,
            True,
        )

        await upload.seek(0)

        try:
            file_size = await run_in_threadpool(
                self._write_stream,
                upload.file,
                destination,
            )
        except Exception:
            await run_in_threadpool(
                destination.unlink,
                True,
            )
            raise

        return StoredDocument(
            storage_key=storage_key,
            original_filename=original_filename,
            file_extension=extension,
            mime_type=mime_type,
            file_size=file_size,
        )

    async def read(
        self,
        storage_key: str,
    ) -> bytes:
        path = self._resolve_key(storage_key)

        if not path.is_file():
            raise FileNotFoundError("Document file not found")

        return await run_in_threadpool(path.read_bytes)

    async def download_to_path(
        self,
        storage_key: str,
        destination: Path,
    ) -> None:
        path = self._resolve_key(storage_key)
        if not path.is_file():
            raise FileNotFoundError("Document file not found")
        await run_in_threadpool(destination.parent.mkdir, 0o755, True, True)
        await run_in_threadpool(shutil.copyfile, path, destination)

    async def delete(
        self,
        storage_key: str,
    ) -> None:
        path = self._resolve_key(storage_key)

        await run_in_threadpool(
            path.unlink,
            True,
        )

    def _resolve_key(
        self,
        storage_key: str,
    ) -> Path:
        path = (self.root / storage_key).resolve()

        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise InvalidDocumentFile("Invalid storage key") from exc

        return path

    def _write_stream(
        self,
        source: BinaryIO,
        destination: Path,
    ) -> int:
        temporary = destination.with_name(f"{destination.name}.part")

        total = 0

        try:
            with temporary.open("xb") as output:
                while True:
                    chunk = source.read(1024 * 1024)

                    if not chunk:
                        break

                    total += len(chunk)

                    if total > self.max_file_size_bytes:
                        raise DocumentTooLarge(
                            "The uploaded file exceeds the configured size limit"
                        )

                    output.write(chunk)

            if total == 0:
                raise InvalidDocumentFile("Empty files are not allowed")

            os.replace(
                temporary,
                destination,
            )

            return total

        finally:
            temporary.unlink(missing_ok=True)


class R2DocumentStorage:
    def __init__(
        self,
        *,
        endpoint_url: str,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str,
        max_file_size_bytes: int,
    ) -> None:
        self.bucket_name = bucket_name
        self.max_file_size_bytes = max_file_size_bytes
        self.client: Any = boto3.client(
            service_name="s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=(secret_access_key),
            region_name="auto",
        )
        self.transfer_config = TransferConfig(
            multipart_threshold=8 * 1024 * 1024,
            multipart_chunksize=8 * 1024 * 1024,
            max_concurrency=4,
            use_threads=True,
        )

    async def save(
        self,
        upload: UploadFile,
        organization_id: uuid.UUID,
        person_id: uuid.UUID,
    ) -> StoredDocument:
        (
            original_filename,
            extension,
            mime_type,
        ) = _metadata_for_upload(upload)

        storage_key = f"documents/{organization_id}/{person_id}/{uuid.uuid4().hex}{extension}"

        await upload.seek(0)
        file_size = await run_in_threadpool(self._stream_size, upload.file)
        if file_size == 0:
            raise InvalidDocumentFile("Empty files are not allowed")
        if file_size > self.max_file_size_bytes:
            raise DocumentTooLarge("The uploaded file exceeds the configured size limit")

        await upload.seek(0)
        await run_in_threadpool(
            self.client.upload_fileobj,
            upload.file,
            self.bucket_name,
            storage_key,
            ExtraArgs={"ContentType": mime_type},
            Config=self.transfer_config,
        )

        return StoredDocument(
            storage_key=storage_key,
            original_filename=original_filename,
            file_extension=extension,
            mime_type=mime_type,
            file_size=file_size,
        )

    async def read(
        self,
        storage_key: str,
    ) -> bytes:
        response: Any = await run_in_threadpool(
            self.client.get_object,
            Bucket=self.bucket_name,
            Key=storage_key,
        )
        body: Any = response["Body"]
        content: bytes = await run_in_threadpool(body.read)
        return content

    async def download_to_path(
        self,
        storage_key: str,
        destination: Path,
    ) -> None:
        await run_in_threadpool(destination.parent.mkdir, 0o755, True, True)
        await run_in_threadpool(
            self.client.download_file,
            self.bucket_name,
            storage_key,
            str(destination),
        )

    async def delete(
        self,
        storage_key: str,
    ) -> None:
        await run_in_threadpool(
            self.client.delete_object,
            Bucket=self.bucket_name,
            Key=storage_key,
        )

    @staticmethod
    def _stream_size(source: BinaryIO) -> int:
        original = source.tell()
        source.seek(0, 2)
        size = source.tell()
        source.seek(original)
        return int(size)


def create_document_storage(
    settings: Settings,
) -> DocumentStorage:
    max_bytes = settings.document_max_file_size_mb * 1024 * 1024

    if settings.storage_backend == "local":
        return LocalDocumentStorage(
            root=settings.document_storage_path,
            max_file_size_bytes=max_bytes,
        )

    endpoint_url = settings.r2_endpoint_url
    access_key_id = settings.r2_access_key_id
    secret_access_key = settings.r2_secret_access_key
    bucket_name = settings.r2_bucket_name

    if (
        endpoint_url is None
        or access_key_id is None
        or secret_access_key is None
        or bucket_name is None
    ):
        raise StorageConfigurationError(
            "R2 storage is enabled but one or more R2 settings are missing"
        )

    return R2DocumentStorage(
        endpoint_url=endpoint_url,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        bucket_name=bucket_name,
        max_file_size_bytes=max_bytes,
    )
