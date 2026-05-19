import asyncio
import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.services import create_admin_action_log
from app.config import get_settings
from app.files.models import FileRecord
from app.files.schemas import FileType

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
BLOCKED_EXTENSIONS = {
    ".bat",
    ".cmd",
    ".com",
    ".dll",
    ".exe",
    ".js",
    ".msi",
    ".ps1",
    ".scr",
    ".sh",
    ".vbs",
}
ALLOWED_UPLOADS: dict[str, dict[str, set[str]]] = {
    "avatar": {
        "image/jpeg": {".jpg", ".jpeg"},
        "image/png": {".png"},
        "image/webp": {".webp"},
    },
    "news_image": {
        "image/jpeg": {".jpg", ".jpeg"},
        "image/png": {".png"},
        "image/webp": {".webp"},
    },
    "tournament_image": {
        "image/jpeg": {".jpg", ".jpeg"},
        "image/png": {".png"},
        "image/webp": {".webp"},
    },
    "pgn": {
        "application/octet-stream": {".pgn", ".txt"},
        "application/x-chess-pgn": {".pgn", ".txt"},
        "text/plain": {".pgn", ".txt"},
    },
    "export": {
        "application/pdf": {".pdf"},
        "text/csv": {".csv"},
        "text/plain": {".txt"},
    },
    "other": {
        "application/pdf": {".pdf"},
        "text/plain": {".txt"},
    },
}


@dataclass(frozen=True)
class ValidatedUpload:
    original_filename: str
    mime_type: str
    extension: str
    data: bytes


def safe_original_filename(filename: str | None) -> str:
    if not filename:
        return "upload"
    normalized = filename.replace("\\", "/").split("/")[-1].strip()
    return normalized[:255] or "upload"


def _validate_file_type(file_type: str) -> None:
    if file_type not in ALLOWED_UPLOADS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported file type",
        )


def _validate_extension_and_mime(
    original_filename: str, mime_type: str, file_type: str
) -> str:
    extension = Path(original_filename).suffix.lower()
    if extension in BLOCKED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Executable uploads are not allowed",
        )

    allowed_mimes = ALLOWED_UPLOADS[file_type]
    if mime_type not in allowed_mimes or extension not in allowed_mimes[mime_type]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File extension or MIME type is not allowed",
        )

    return extension


async def _read_limited_upload(upload: UploadFile, max_bytes: int = MAX_UPLOAD_BYTES) -> bytes:
    data = await upload.read(max_bytes + 1)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload is empty")
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File too large",
        )
    return data


def _write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


async def _remove_file(path: Path) -> None:
    def remove() -> None:
        if path.is_file():
            path.unlink()

    await asyncio.to_thread(remove)


async def remove_stored_file(record: FileRecord) -> None:
    storage_root = Path(get_settings().local_storage_root)
    await _remove_file(storage_root / record.storage_path)


async def read_validated_upload(
    file_type: FileType,
    upload: UploadFile,
    max_bytes: int = MAX_UPLOAD_BYTES,
) -> ValidatedUpload:
    _validate_file_type(file_type)
    original_filename = safe_original_filename(upload.filename)
    mime_type = upload.content_type or ""
    extension = _validate_extension_and_mime(original_filename, mime_type, file_type)
    data = await _read_limited_upload(upload, max_bytes=max_bytes)
    return ValidatedUpload(
        original_filename=original_filename,
        mime_type=mime_type,
        extension=extension,
        data=data,
    )


async def create_file_record_from_validated_upload(
    session: AsyncSession,
    owner_id: uuid.UUID | None,
    file_type: FileType,
    upload: ValidatedUpload,
) -> FileRecord:
    settings = get_settings()
    storage_root = Path(settings.local_storage_root)
    storage_name = f"{uuid.uuid4()}{upload.extension}"
    relative_path = Path(file_type) / storage_name
    absolute_path = storage_root / relative_path
    checksum = hashlib.sha256(upload.data).hexdigest()
    try:
        await asyncio.to_thread(_write_bytes, absolute_path, upload.data)
        record = FileRecord(
            owner_id=owner_id,
            file_type=file_type,
            storage_provider="local",
            storage_path=relative_path.as_posix(),
            original_filename=upload.original_filename,
            mime_type=upload.mime_type,
            size_bytes=len(upload.data),
            checksum=checksum,
        )
        session.add(record)
        await session.flush()
        return record
    except Exception:
        await _remove_file(absolute_path)
        raise


def file_record_audit_snapshot(record: FileRecord) -> dict[str, object]:
    return {
        "id": str(record.id),
        "owner_id": str(record.owner_id) if record.owner_id else None,
        "file_type": record.file_type,
        "storage_provider": record.storage_provider,
        "original_filename": record.original_filename,
        "mime_type": record.mime_type,
        "size_bytes": record.size_bytes,
        "checksum": record.checksum,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


async def create_admin_file_upload(
    session: AsyncSession,
    admin_id: uuid.UUID,
    file_type: FileType,
    upload: UploadFile,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> FileRecord:
    record: FileRecord | None = None

    try:
        validated_upload = await read_validated_upload(file_type, upload)
        record = await create_file_record_from_validated_upload(
            session=session,
            owner_id=admin_id,
            file_type=file_type,
            upload=validated_upload,
        )
        await create_admin_action_log(
            db=session,
            admin_id=admin_id,
            action="file.uploaded",
            entity_type="file",
            entity_id=record.id,
            after=file_record_audit_snapshot(record),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await session.commit()
        await session.refresh(record)
        return record
    except Exception:
        await session.rollback()
        if record is not None:
            await remove_stored_file(record)
        raise
