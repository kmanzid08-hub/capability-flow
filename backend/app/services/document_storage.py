import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

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
}


class InvalidDocumentFile(ValueError):
    pass


class DocumentTooLarge(ValueError):
    pass


@dataclass(frozen=True)
class StoredDocument:
    storage_key: str
    original_filename: str
    file_extension: str
    mime_type: str
    file_size: int


def sanitize_filename(
    filename: str | None,
) -> str:
    if filename is None:
        raise InvalidDocumentFile("The uploaded file must have a filename")

    cleaned = filename.replace("\\", "/").split("/")[-1]
    cleaned = cleaned.replace("\x00", "").strip()

    if not cleaned:
        raise InvalidDocumentFile("The uploaded file must have a filename")

    if len(cleaned) > 500:
        raise InvalidDocumentFile("The filename is too long")

    return cleaned


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
        original_filename = sanitize_filename(
            upload.filename,
        )

        extension = Path(original_filename).suffix.lower()

        if extension not in ALLOWED_MIME_TYPES:
            raise InvalidDocumentFile(
                f"Files with extension '{extension or 'none'}' are not allowed"
            )

        storage_key = f"{organization_id}/{person_id}/{uuid.uuid4().hex}{extension}"

        destination = self._resolve_key(
            storage_key,
        )

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
            mime_type=ALLOWED_MIME_TYPES[extension],
            file_size=file_size,
        )

    async def delete(
        self,
        storage_key: str,
    ) -> None:
        path = self._resolve_key(
            storage_key,
        )

        await run_in_threadpool(
            path.unlink,
            True,
        )

    def path_for(
        self,
        storage_key: str,
    ) -> Path:
        return self._resolve_key(
            storage_key,
        )

    def _resolve_key(
        self,
        storage_key: str,
    ) -> Path:
        path = (self.root / storage_key).resolve()

        try:
            path.relative_to(
                self.root,
            )
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
            with temporary.open(
                "xb",
            ) as output:
                while True:
                    chunk = source.read(
                        1024 * 1024,
                    )

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
            temporary.unlink(
                missing_ok=True,
            )
