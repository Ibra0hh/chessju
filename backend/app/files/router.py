from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.database import get_db_session
from app.files.schemas import FileMetadataResponse, FileType
from app.files.services import create_admin_file_upload
from app.users.models import User

router = APIRouter(tags=["Files"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post(
    "/admin/files",
    response_model=FileMetadataResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_admin_file(
    request: Request,
    file_type: FileType = Form(...),
    file: UploadFile = File(...),
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> FileMetadataResponse:
    record = await create_admin_file_upload(
        session=session,
        admin_id=current_admin.id,
        file_type=file_type,
        upload=file,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return FileMetadataResponse.model_validate(record)
