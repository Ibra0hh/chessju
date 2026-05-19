from typing import Any
from urllib.parse import quote

import httpx
from fastapi import HTTPException, status

from app.config import get_settings

CHESSCOM_API_BASE_URL = "https://api.chess.com/pub"


class ChessComApiClient:
    def __init__(self, timeout_seconds: int | None = None, user_agent: str | None = None) -> None:
        settings = get_settings()
        self.timeout_seconds = timeout_seconds or settings.chesscom_sync_timeout_seconds
        self.user_agent = user_agent or settings.chesscom_user_agent

    async def _get_json(self, url: str) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=headers) as client:
            response = await client.get(url)
        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chess.com resource not found",
            )
        if response.status_code == 429:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Chess.com rate limit reached; try again later",
            )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Chess.com public API request failed",
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Chess.com public API returned invalid JSON",
            ) from exc
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Chess.com public API returned unexpected data",
            )
        return data

    async def fetch_profile(self, username: str) -> dict[str, Any]:
        encoded_username = quote(username, safe="")
        return await self._get_json(f"{CHESSCOM_API_BASE_URL}/player/{encoded_username}")

    async def fetch_archives(self, username: str) -> list[str]:
        encoded_username = quote(username, safe="")
        data = await self._get_json(
            f"{CHESSCOM_API_BASE_URL}/player/{encoded_username}/games/archives"
        )
        archives = data.get("archives")
        if not isinstance(archives, list):
            return []
        return [str(item) for item in archives if isinstance(item, str)]

    async def fetch_archive_games(self, archive_url: str) -> list[dict[str, Any]]:
        data = await self._get_json(archive_url)
        games = data.get("games")
        if not isinstance(games, list):
            return []
        return [item for item in games if isinstance(item, dict)]
