import re
import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.services import create_admin_action_log
from app.common.time import utc_now
from app.files.models import FileRecord
from app.news.models import Announcement, Article
from app.news.schemas import (
    AdminArticleListResponse,
    AnnouncementCreateRequest,
    AnnouncementListResponse,
    AnnouncementResponse,
    AnnouncementUpdateRequest,
    ArticleCreateRequest,
    ArticleListResponse,
    ArticleResponse,
    ArticleSummaryResponse,
    ArticleUpdateRequest,
    HomeResponse,
)

SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_slug(value: str) -> str:
    slug = SLUG_NON_ALNUM.sub("-", value.lower()).strip("-")
    return slug or "article"


def _dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def article_audit_snapshot(article: Article) -> dict[str, Any]:
    return {
        "id": str(article.id),
        "author_id": str(article.author_id),
        "title": article.title,
        "slug": article.slug,
        "summary": article.summary,
        "body_markdown": article.body_markdown,
        "cover_file_id": str(article.cover_file_id) if article.cover_file_id else None,
        "status": article.status,
        "published_at": _dt(article.published_at),
        "created_at": _dt(article.created_at),
        "updated_at": _dt(article.updated_at),
        "deleted_at": _dt(article.deleted_at),
    }


def announcement_audit_snapshot(announcement: Announcement) -> dict[str, Any]:
    return {
        "id": str(announcement.id),
        "created_by": str(announcement.created_by),
        "title": announcement.title,
        "message": announcement.message,
        "target": announcement.target,
        "priority": announcement.priority,
        "status": announcement.status,
        "published_at": _dt(announcement.published_at),
        "expires_at": _dt(announcement.expires_at),
        "tournament_id": str(announcement.tournament_id) if announcement.tournament_id else None,
        "created_at": _dt(announcement.created_at),
        "updated_at": _dt(announcement.updated_at),
        "deleted_at": _dt(announcement.deleted_at),
    }


async def _validate_news_cover(session: AsyncSession, cover_file_id: uuid.UUID | None) -> None:
    if cover_file_id is None:
        return
    record = await session.get(FileRecord, cover_file_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover file not found")
    if record.file_type != "news_image":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cover file must be a news image",
        )


async def _slug_exists(
    session: AsyncSession,
    slug: str,
    exclude_article_id: uuid.UUID | None = None,
) -> bool:
    statement = select(Article.id).where(Article.slug == slug)
    if exclude_article_id is not None:
        statement = statement.where(Article.id != exclude_article_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none() is not None


async def _resolve_article_slug(
    session: AsyncSession,
    title: str,
    requested_slug: str | None = None,
    exclude_article_id: uuid.UUID | None = None,
) -> str:
    if requested_slug:
        slug = normalize_slug(requested_slug)
        if await _slug_exists(session, slug, exclude_article_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already exists")
        return slug

    base_slug = normalize_slug(title)
    candidate = base_slug
    suffix = 2
    while await _slug_exists(session, candidate, exclude_article_id):
        candidate = f"{base_slug}-{suffix}"
        suffix += 1
    return candidate


def _public_article_statement() -> Select[tuple[Article]]:
    return select(Article).where(
        Article.status == "published",
        Article.published_at.is_not(None),
        Article.deleted_at.is_(None),
    )


def _public_announcement_statement(now: datetime) -> Select[tuple[Announcement]]:
    return select(Announcement).where(
        Announcement.status == "published",
        Announcement.target == "all",
        Announcement.published_at.is_not(None),
        Announcement.deleted_at.is_(None),
        or_(Announcement.expires_at.is_(None), Announcement.expires_at > now),
    )


async def list_public_articles(
    session: AsyncSession, limit: int = 20, offset: int = 0
) -> ArticleListResponse:
    statement = _public_article_statement()
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    result = await session.execute(
        statement.order_by(Article.published_at.desc(), Article.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return ArticleListResponse(
        items=[ArticleSummaryResponse.model_validate(article) for article in result.scalars()],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def get_public_article_by_slug(session: AsyncSession, slug: str) -> ArticleResponse:
    result = await session.execute(_public_article_statement().where(Article.slug == slug))
    article = result.scalar_one_or_none()
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return ArticleResponse.model_validate(article)


async def list_admin_articles(
    session: AsyncSession, limit: int = 50, offset: int = 0
) -> AdminArticleListResponse:
    total = await session.scalar(select(func.count()).select_from(Article))
    result = await session.execute(
        select(Article)
        .order_by(Article.created_at.desc(), Article.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return AdminArticleListResponse(
        items=[ArticleResponse.model_validate(article) for article in result.scalars()],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def get_admin_article(session: AsyncSession, article_id: uuid.UUID) -> Article:
    article = await session.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return article


async def create_article(
    session: AsyncSession,
    admin_id: uuid.UUID,
    payload: ArticleCreateRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ArticleResponse:
    await _validate_news_cover(session, payload.cover_file_id)
    slug = await _resolve_article_slug(session, payload.title, payload.slug)
    article = Article(
        author_id=admin_id,
        title=payload.title,
        slug=slug,
        summary=payload.summary,
        body_markdown=payload.body_markdown,
        cover_file_id=payload.cover_file_id,
        status="draft",
    )
    session.add(article)
    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="article.created",
        entity_type="article",
        entity_id=article.id,
        after=article_audit_snapshot(article),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(article)
    return ArticleResponse.model_validate(article)


async def update_article(
    session: AsyncSession,
    admin_id: uuid.UUID,
    article_id: uuid.UUID,
    payload: ArticleUpdateRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ArticleResponse:
    article = await get_admin_article(session, article_id)
    before = article_audit_snapshot(article)
    update_data = payload.model_dump(exclude_unset=True)

    if "cover_file_id" in update_data:
        await _validate_news_cover(session, update_data["cover_file_id"])
    if "slug" in update_data and update_data["slug"] is not None:
        update_data["slug"] = await _resolve_article_slug(
            session,
            title=article.title,
            requested_slug=update_data["slug"],
            exclude_article_id=article.id,
        )

    for field_name, value in update_data.items():
        setattr(article, field_name, value)

    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="article.updated",
        entity_type="article",
        entity_id=article.id,
        before=before,
        after=article_audit_snapshot(article),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(article)
    return ArticleResponse.model_validate(article)


async def publish_article(
    session: AsyncSession,
    admin_id: uuid.UUID,
    article_id: uuid.UUID,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ArticleResponse:
    article = await get_admin_article(session, article_id)
    before = article_audit_snapshot(article)
    article.status = "published"
    if article.published_at is None:
        article.published_at = utc_now()
    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="article.published",
        entity_type="article",
        entity_id=article.id,
        before=before,
        after=article_audit_snapshot(article),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(article)
    return ArticleResponse.model_validate(article)


async def archive_article(
    session: AsyncSession,
    admin_id: uuid.UUID,
    article_id: uuid.UUID,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ArticleResponse:
    article = await get_admin_article(session, article_id)
    before = article_audit_snapshot(article)
    article.status = "archived"
    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="article.archived",
        entity_type="article",
        entity_id=article.id,
        before=before,
        after=article_audit_snapshot(article),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(article)
    return ArticleResponse.model_validate(article)


async def soft_delete_article(
    session: AsyncSession,
    admin_id: uuid.UUID,
    article_id: uuid.UUID,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> bool:
    article = await get_admin_article(session, article_id)
    before = article_audit_snapshot(article)
    if article.deleted_at is None:
        article.deleted_at = utc_now()
    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="article.deleted",
        entity_type="article",
        entity_id=article.id,
        before=before,
        after=article_audit_snapshot(article),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    return True


async def list_public_announcements(
    session: AsyncSession, limit: int = 20, offset: int = 0
) -> AnnouncementListResponse:
    statement = _public_announcement_statement(utc_now())
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    result = await session.execute(
        statement.order_by(Announcement.published_at.desc(), Announcement.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return AnnouncementListResponse(
        items=[AnnouncementResponse.model_validate(item) for item in result.scalars()],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def list_admin_announcements(
    session: AsyncSession, limit: int = 50, offset: int = 0
) -> AnnouncementListResponse:
    total = await session.scalar(select(func.count()).select_from(Announcement))
    result = await session.execute(
        select(Announcement)
        .order_by(Announcement.created_at.desc(), Announcement.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return AnnouncementListResponse(
        items=[AnnouncementResponse.model_validate(item) for item in result.scalars()],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def get_admin_announcement(
    session: AsyncSession, announcement_id: uuid.UUID
) -> Announcement:
    announcement = await session.get(Announcement, announcement_id)
    if announcement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    return announcement


async def create_announcement(
    session: AsyncSession,
    admin_id: uuid.UUID,
    payload: AnnouncementCreateRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AnnouncementResponse:
    announcement = Announcement(
        created_by=admin_id,
        title=payload.title,
        message=payload.message,
        target=payload.target,
        priority=payload.priority,
        status=payload.status,
        published_at=utc_now() if payload.status == "published" else None,
        expires_at=payload.expires_at,
        tournament_id=payload.tournament_id,
    )
    session.add(announcement)
    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="announcement.created",
        entity_type="announcement",
        entity_id=announcement.id,
        after=announcement_audit_snapshot(announcement),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(announcement)
    return AnnouncementResponse.model_validate(announcement)


async def update_announcement(
    session: AsyncSession,
    admin_id: uuid.UUID,
    announcement_id: uuid.UUID,
    payload: AnnouncementUpdateRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AnnouncementResponse:
    announcement = await get_admin_announcement(session, announcement_id)
    before = announcement_audit_snapshot(announcement)
    update_data = payload.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(announcement, field_name, value)
    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="announcement.updated",
        entity_type="announcement",
        entity_id=announcement.id,
        before=before,
        after=announcement_audit_snapshot(announcement),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(announcement)
    return AnnouncementResponse.model_validate(announcement)


async def publish_announcement(
    session: AsyncSession,
    admin_id: uuid.UUID,
    announcement_id: uuid.UUID,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AnnouncementResponse:
    announcement = await get_admin_announcement(session, announcement_id)
    before = announcement_audit_snapshot(announcement)
    announcement.status = "published"
    if announcement.published_at is None:
        announcement.published_at = utc_now()
    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="announcement.published",
        entity_type="announcement",
        entity_id=announcement.id,
        before=before,
        after=announcement_audit_snapshot(announcement),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(announcement)
    return AnnouncementResponse.model_validate(announcement)


async def archive_announcement(
    session: AsyncSession,
    admin_id: uuid.UUID,
    announcement_id: uuid.UUID,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AnnouncementResponse:
    announcement = await get_admin_announcement(session, announcement_id)
    before = announcement_audit_snapshot(announcement)
    announcement.status = "archived"
    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="announcement.archived",
        entity_type="announcement",
        entity_id=announcement.id,
        before=before,
        after=announcement_audit_snapshot(announcement),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(announcement)
    return AnnouncementResponse.model_validate(announcement)


async def soft_delete_announcement(
    session: AsyncSession,
    admin_id: uuid.UUID,
    announcement_id: uuid.UUID,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> bool:
    announcement = await get_admin_announcement(session, announcement_id)
    before = announcement_audit_snapshot(announcement)
    if announcement.deleted_at is None:
        announcement.deleted_at = utc_now()
    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="announcement.deleted",
        entity_type="announcement",
        entity_id=announcement.id,
        before=before,
        after=announcement_audit_snapshot(announcement),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    return True


async def get_home_content(session: AsyncSession) -> HomeResponse:
    from app.tournaments.services import list_home_upcoming_tournaments

    announcements = await list_public_announcements(session, limit=5, offset=0)
    latest_news = await list_public_articles(session, limit=5, offset=0)
    return HomeResponse(
        announcements=announcements.items,
        latest_news=latest_news.items,
        upcoming_tournaments=await list_home_upcoming_tournaments(session, limit=5),
        leaderboard_preview=[],
    )
