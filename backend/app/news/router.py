import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.database import get_db_session
from app.news.schemas import (
    AdminArticleListResponse,
    AnnouncementCreateRequest,
    AnnouncementListResponse,
    AnnouncementResponse,
    AnnouncementUpdateRequest,
    ArticleCreateRequest,
    ArticleListResponse,
    ArticleResponse,
    ArticleUpdateRequest,
    DeleteResponse,
    HomeResponse,
)
from app.news.services import (
    archive_announcement,
    archive_article,
    create_announcement,
    create_article,
    get_admin_article,
    get_home_content,
    get_public_article_by_slug,
    list_admin_announcements,
    list_admin_articles,
    list_public_announcements,
    list_public_articles,
    publish_announcement,
    publish_article,
    soft_delete_announcement,
    soft_delete_article,
    update_announcement,
    update_article,
)
from app.users.models import User

router = APIRouter(tags=["content"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/news", response_model=ArticleListResponse)
async def public_news(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ArticleListResponse:
    return await list_public_articles(session, limit=limit, offset=offset)


@router.get("/news/{slug}", response_model=ArticleResponse)
async def public_news_detail(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
) -> ArticleResponse:
    return await get_public_article_by_slug(session, slug)


@router.get("/announcements", response_model=AnnouncementListResponse)
async def public_announcements(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AnnouncementListResponse:
    return await list_public_announcements(session, limit=limit, offset=offset)


@router.get("/home", response_model=HomeResponse)
async def home(session: AsyncSession = Depends(get_db_session)) -> HomeResponse:
    return await get_home_content(session)


@router.post(
    "/admin/news",
    response_model=ArticleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_article(
    payload: ArticleCreateRequest,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> ArticleResponse:
    return await create_article(
        session=session,
        admin_id=current_admin.id,
        payload=payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/admin/news", response_model=AdminArticleListResponse)
async def admin_list_articles(
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AdminArticleListResponse:
    _ = current_admin
    return await list_admin_articles(session, limit=limit, offset=offset)


@router.get("/admin/news/{article_id}", response_model=ArticleResponse)
async def admin_get_article(
    article_id: uuid.UUID,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> ArticleResponse:
    _ = current_admin
    article = await get_admin_article(session, article_id)
    return ArticleResponse.model_validate(article)


@router.patch("/admin/news/{article_id}", response_model=ArticleResponse)
async def admin_update_article(
    article_id: uuid.UUID,
    payload: ArticleUpdateRequest,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> ArticleResponse:
    return await update_article(
        session=session,
        admin_id=current_admin.id,
        article_id=article_id,
        payload=payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/admin/news/{article_id}/publish", response_model=ArticleResponse)
async def admin_publish_article(
    article_id: uuid.UUID,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> ArticleResponse:
    return await publish_article(
        session=session,
        admin_id=current_admin.id,
        article_id=article_id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/admin/news/{article_id}/archive", response_model=ArticleResponse)
async def admin_archive_article(
    article_id: uuid.UUID,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> ArticleResponse:
    return await archive_article(
        session=session,
        admin_id=current_admin.id,
        article_id=article_id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.delete("/admin/news/{article_id}", response_model=DeleteResponse)
async def admin_delete_article(
    article_id: uuid.UUID,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> DeleteResponse:
    deleted = await soft_delete_article(
        session=session,
        admin_id=current_admin.id,
        article_id=article_id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return DeleteResponse(deleted=deleted)


@router.post(
    "/admin/announcements",
    response_model=AnnouncementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_announcement(
    payload: AnnouncementCreateRequest,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> AnnouncementResponse:
    return await create_announcement(
        session=session,
        admin_id=current_admin.id,
        payload=payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/admin/announcements", response_model=AnnouncementListResponse)
async def admin_list_announcements(
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AnnouncementListResponse:
    _ = current_admin
    return await list_admin_announcements(session, limit=limit, offset=offset)


@router.patch("/admin/announcements/{announcement_id}", response_model=AnnouncementResponse)
async def admin_update_announcement(
    announcement_id: uuid.UUID,
    payload: AnnouncementUpdateRequest,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> AnnouncementResponse:
    return await update_announcement(
        session=session,
        admin_id=current_admin.id,
        announcement_id=announcement_id,
        payload=payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/admin/announcements/{announcement_id}/publish", response_model=AnnouncementResponse)
async def admin_publish_announcement(
    announcement_id: uuid.UUID,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> AnnouncementResponse:
    return await publish_announcement(
        session=session,
        admin_id=current_admin.id,
        announcement_id=announcement_id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/admin/announcements/{announcement_id}/archive", response_model=AnnouncementResponse)
async def admin_archive_announcement(
    announcement_id: uuid.UUID,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> AnnouncementResponse:
    return await archive_announcement(
        session=session,
        admin_id=current_admin.id,
        announcement_id=announcement_id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.delete("/admin/announcements/{announcement_id}", response_model=DeleteResponse)
async def admin_delete_announcement(
    announcement_id: uuid.UUID,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> DeleteResponse:
    deleted = await soft_delete_announcement(
        session=session,
        admin_id=current_admin.id,
        announcement_id=announcement_id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return DeleteResponse(deleted=deleted)
