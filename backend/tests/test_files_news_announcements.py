import asyncio
import uuid
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.models import Role, UserRole
from app.common.time import utc_now
from app.database import AsyncSessionLocal
from app.main import app

client = TestClient(app)


def unique_suffix() -> str:
    return uuid.uuid4().hex[:12]


def unique_user_payload(prefix: str = "content-test") -> dict[str, str]:
    suffix = unique_suffix()
    return {
        "email": f"{prefix}-{suffix}@example.com",
        "password": "correct-horse-123",
        "username": f"{prefix.replace('-', '_')}_{suffix}",
        "full_name": "Content Test User",
    }


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def register_user(prefix: str = "content-test") -> dict:
    response = client.post("/api/v1/auth/register", json=unique_user_payload(prefix))
    assert response.status_code == 201, response.text
    return response.json()


async def _assign_role(user_id: uuid.UUID, role_name: str) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one()
        session.add(UserRole(user_id=user_id, role_id=role.id))
        await session.commit()


def assign_role(user_id: str, role_name: str) -> None:
    asyncio.run(_assign_role(uuid.UUID(user_id), role_name))


def register_admin() -> dict:
    data = register_user("content-admin")
    assign_role(data["user"]["id"], "admin")
    return data


def create_draft_article(admin_data: dict, slug: str | None = None) -> dict:
    suffix = unique_suffix()
    payload = {
        "title": f"ChessJU Update {suffix}",
        "slug": slug,
        "summary": "A short content update.",
        "body_markdown": "Full article body.",
    }
    if slug is None:
        payload.pop("slug")
    response = client.post(
        "/api/v1/admin/news",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_published_article(admin_data: dict, slug: str | None = None) -> dict:
    article = create_draft_article(admin_data, slug=slug)
    response = client.post(
        f"/api/v1/admin/news/{article['id']}/publish",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    assert response.status_code == 200, response.text
    return response.json()


def create_announcement(
    admin_data: dict,
    *,
    status: str = "published",
    expires_at: str | None = None,
) -> dict:
    suffix = unique_suffix()
    payload = {
        "title": f"Announcement {suffix}",
        "message": "Club room is open today.",
        "target": "all",
        "priority": "normal",
        "status": status,
        "expires_at": expires_at,
    }
    response = client.post(
        "/api/v1/admin/announcements",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


def latest_audit_log(action: str, entity_id: str, admin_data: dict) -> dict:
    response = client.get(
        f"/api/v1/admin/audit-logs?action={action}&limit=10",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    assert response.status_code == 200, response.text
    for item in response.json()["items"]:
        if item["entity_id"] == entity_id:
            return item
    raise AssertionError(f"Audit log not found for {action} {entity_id}")


def test_admin_can_upload_allowed_file_type() -> None:
    admin_data = register_admin()

    response = client.post(
        "/api/v1/admin/files",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        data={"file_type": "news_image"},
        files={"file": ("cover.png", b"png image bytes", "image/png")},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["file_type"] == "news_image"
    assert body["mime_type"] == "image/png"
    assert body["size_bytes"] == len(b"png image bytes")


def test_member_cannot_use_admin_file_upload() -> None:
    member_data = register_user()

    response = client.post(
        "/api/v1/admin/files",
        headers=auth_headers(member_data["tokens"]["access_token"]),
        data={"file_type": "news_image"},
        files={"file": ("cover.png", b"png image bytes", "image/png")},
    )

    assert response.status_code == 403


def test_file_metadata_does_not_expose_unsafe_absolute_paths() -> None:
    admin_data = register_admin()

    response = client.post(
        "/api/v1/admin/files",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        data={"file_type": "news_image"},
        files={"file": ("folder/cover.png", b"png image bytes", "image/png")},
    )

    assert response.status_code == 201, response.text
    body_text = response.text.lower()
    assert "storage_path" not in body_text
    assert "c:\\" not in body_text
    assert "/data/storage" not in body_text


def test_invalid_extension_or_mime_type_is_rejected() -> None:
    admin_data = register_admin()

    response = client.post(
        "/api/v1/admin/files",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        data={"file_type": "news_image"},
        files={"file": ("cover.exe", b"not an image", "image/png")},
    )

    assert response.status_code == 400


def test_admin_can_create_draft_article() -> None:
    admin_data = register_admin()
    article = create_draft_article(admin_data)

    assert article["status"] == "draft"
    assert article["published_at"] is None
    assert article["title"].startswith("ChessJU Update")


def test_member_cannot_create_article() -> None:
    member_data = register_user()

    response = client.post(
        "/api/v1/admin/news",
        headers=auth_headers(member_data["tokens"]["access_token"]),
        json={
            "title": "Unauthorized Draft",
            "body_markdown": "Should fail.",
        },
    )

    assert response.status_code == 403


def test_public_news_list_only_returns_published_articles() -> None:
    admin_data = register_admin()
    draft = create_draft_article(admin_data, slug=f"draft-{unique_suffix()}")
    published = create_published_article(admin_data, slug=f"published-{unique_suffix()}")

    response = client.get("/api/v1/news?limit=100")

    assert response.status_code == 200
    slugs = {item["slug"] for item in response.json()["items"]}
    assert published["slug"] in slugs
    assert draft["slug"] not in slugs


def test_public_news_detail_returns_published_article_by_slug() -> None:
    admin_data = register_admin()
    article = create_published_article(admin_data, slug=f"detail-{unique_suffix()}")

    response = client.get(f"/api/v1/news/{article['slug']}")

    assert response.status_code == 200
    assert response.json()["id"] == article["id"]


def test_draft_article_is_hidden_from_public_endpoint() -> None:
    admin_data = register_admin()
    article = create_draft_article(admin_data, slug=f"hidden-draft-{unique_suffix()}")

    response = client.get(f"/api/v1/news/{article['slug']}")

    assert response.status_code == 404


def test_archived_article_is_hidden_from_public_endpoint() -> None:
    admin_data = register_admin()
    article = create_published_article(admin_data, slug=f"archived-{unique_suffix()}")

    archive_response = client.post(
        f"/api/v1/admin/news/{article['id']}/archive",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    response = client.get(f"/api/v1/news/{article['slug']}")

    assert archive_response.status_code == 200
    assert response.status_code == 404


def test_soft_deleted_article_is_hidden_from_public_endpoint() -> None:
    admin_data = register_admin()
    article = create_published_article(admin_data, slug=f"deleted-{unique_suffix()}")

    delete_response = client.delete(
        f"/api/v1/admin/news/{article['id']}",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    response = client.get(f"/api/v1/news/{article['slug']}")

    assert delete_response.status_code == 200
    assert delete_response.json() == {"deleted": True}
    assert response.status_code == 404


def test_publish_endpoint_changes_status_and_published_at() -> None:
    admin_data = register_admin()
    article = create_draft_article(admin_data)

    response = client.post(
        f"/api/v1/admin/news/{article['id']}/publish",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "published"
    assert response.json()["published_at"] is not None


def test_admin_article_mutation_creates_audit_log() -> None:
    admin_data = register_admin()
    article = create_draft_article(admin_data)

    response = client.patch(
        f"/api/v1/admin/news/{article['id']}",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={"summary": "Updated summary."},
    )
    log = latest_audit_log("article.updated", article["id"], admin_data)

    assert response.status_code == 200
    assert log["before"]["summary"] == "A short content update."
    assert log["after"]["summary"] == "Updated summary."


def test_duplicate_slug_is_rejected() -> None:
    admin_data = register_admin()
    slug = f"duplicate-{unique_suffix()}"
    create_draft_article(admin_data, slug=slug)

    response = client.post(
        "/api/v1/admin/news",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={
            "title": "Duplicate Slug",
            "slug": slug,
            "body_markdown": "Should conflict.",
        },
    )

    assert response.status_code == 409


def test_admin_can_create_announcement() -> None:
    admin_data = register_admin()
    announcement = create_announcement(admin_data)

    assert announcement["status"] == "published"
    assert announcement["published_at"] is not None


def test_member_cannot_create_announcement() -> None:
    member_data = register_user()

    response = client.post(
        "/api/v1/admin/announcements",
        headers=auth_headers(member_data["tokens"]["access_token"]),
        json={"title": "Unauthorized", "message": "Should fail."},
    )

    assert response.status_code == 403


def test_public_announcements_only_show_published_active_announcements() -> None:
    admin_data = register_admin()
    draft = create_announcement(admin_data, status="draft")
    published = create_announcement(admin_data)

    response = client.get("/api/v1/announcements?limit=100")

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert published["id"] in ids
    assert draft["id"] not in ids


def test_expired_announcement_is_hidden() -> None:
    admin_data = register_admin()
    expires_at = (utc_now() - timedelta(days=1)).isoformat()
    announcement = create_announcement(admin_data, expires_at=expires_at)

    response = client.get("/api/v1/announcements?limit=100")

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert announcement["id"] not in ids


def test_archived_announcement_is_hidden() -> None:
    admin_data = register_admin()
    announcement = create_announcement(admin_data)

    archive_response = client.post(
        f"/api/v1/admin/announcements/{announcement['id']}/archive",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    response = client.get("/api/v1/announcements?limit=100")

    assert archive_response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert announcement["id"] not in ids


def test_soft_deleted_announcement_is_hidden() -> None:
    admin_data = register_admin()
    announcement = create_announcement(admin_data)

    delete_response = client.delete(
        f"/api/v1/admin/announcements/{announcement['id']}",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    response = client.get("/api/v1/announcements?limit=100")

    assert delete_response.status_code == 200
    assert delete_response.json() == {"deleted": True}
    ids = {item["id"] for item in response.json()["items"]}
    assert announcement["id"] not in ids


def test_admin_announcement_mutation_creates_audit_log() -> None:
    admin_data = register_admin()
    announcement = create_announcement(admin_data)

    response = client.patch(
        f"/api/v1/admin/announcements/{announcement['id']}",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={"message": "Updated announcement."},
    )
    log = latest_audit_log("announcement.updated", announcement["id"], admin_data)

    assert response.status_code == 200
    assert log["before"]["message"] == "Club room is open today."
    assert log["after"]["message"] == "Updated announcement."


def test_home_returns_stable_response_shape() -> None:
    response = client.get("/api/v1/home")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "announcements",
        "latest_news",
        "upcoming_tournaments",
        "leaderboard_preview",
    }
    assert isinstance(body["announcements"], list)
    assert isinstance(body["latest_news"], list)
    assert isinstance(body["upcoming_tournaments"], list)
    assert body["leaderboard_preview"] == []


def test_home_includes_latest_published_news() -> None:
    admin_data = register_admin()
    article = create_published_article(admin_data, slug=f"home-news-{unique_suffix()}")

    response = client.get("/api/v1/home")

    assert response.status_code == 200
    slugs = {item["slug"] for item in response.json()["latest_news"]}
    assert article["slug"] in slugs


def test_home_includes_active_announcements() -> None:
    admin_data = register_admin()
    announcement = create_announcement(admin_data)

    response = client.get("/api/v1/home")

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["announcements"]}
    assert announcement["id"] in ids
