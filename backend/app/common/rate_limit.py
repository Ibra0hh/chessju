import time
from dataclasses import dataclass
from functools import lru_cache

from fastapi import HTTPException, Request, status
from redis.asyncio import Redis

from app.config import get_settings
from app.users.models import User


@dataclass(frozen=True)
class RateLimitResult:
    limit: int
    remaining: int
    reset_seconds: int


class RateLimitBackendUnavailable(Exception):
    pass


class RedisRateLimiter:
    def __init__(self, valkey_url: str, namespace: str = "chessju:rate_limit") -> None:
        self.client = Redis.from_url(valkey_url, decode_responses=True)
        self.namespace = namespace
        self._disabled_until = 0.0

    async def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        if time.monotonic() < self._disabled_until:
            return RateLimitResult(limit=limit, remaining=limit, reset_seconds=window_seconds)

        redis_key = f"{self.namespace}:{key}"
        try:
            count = await self.client.incr(redis_key)
            if count == 1:
                await self.client.expire(redis_key, window_seconds)
            ttl = await self.client.ttl(redis_key)
        except Exception as exc:
            self._disabled_until = time.monotonic() + 30
            raise RateLimitBackendUnavailable from exc

        reset_seconds = ttl if isinstance(ttl, int) and ttl > 0 else window_seconds
        remaining = max(limit - int(count), 0)
        if int(count) > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": "Rate limit exceeded",
                    "limit": limit,
                    "window_seconds": window_seconds,
                    "reset_seconds": reset_seconds,
                },
            )
        return RateLimitResult(limit=limit, remaining=remaining, reset_seconds=reset_seconds)


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, tuple[int, float]] = {}

    async def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        now = time.monotonic()
        count, reset_at = self._buckets.get(key, (0, now + window_seconds))
        if now >= reset_at:
            count = 0
            reset_at = now + window_seconds
        count += 1
        self._buckets[key] = (count, reset_at)
        reset_seconds = max(int(reset_at - now), 1)
        remaining = max(limit - count, 0)
        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": "Rate limit exceeded",
                    "limit": limit,
                    "window_seconds": window_seconds,
                    "reset_seconds": reset_seconds,
                },
            )
        return RateLimitResult(limit=limit, remaining=remaining, reset_seconds=reset_seconds)


@lru_cache
def get_rate_limiter() -> RedisRateLimiter:
    return RedisRateLimiter(get_settings().valkey_url)


def client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()[:64] or "unknown"
    return request.client.host[:64] if request.client else "unknown"


async def enforce_rate_limit(
    request: Request,
    *,
    key: str,
    limit: int,
    window_seconds: int,
) -> None:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return
    try:
        await get_rate_limiter().check(key=key, limit=limit, window_seconds=window_seconds)
    except RateLimitBackendUnavailable:
        return


async def enforce_ip_rate_limit(
    request: Request,
    *,
    scope: str,
    limit: int,
    window_seconds: int,
) -> None:
    await enforce_rate_limit(
        request,
        key=f"ip:{scope}:{client_ip(request)}",
        limit=limit,
        window_seconds=window_seconds,
    )


async def enforce_user_rate_limit(
    request: Request,
    *,
    user: User,
    scope: str,
    limit: int,
    window_seconds: int,
) -> None:
    await enforce_rate_limit(
        request,
        key=f"user:{scope}:{user.id}",
        limit=limit,
        window_seconds=window_seconds,
    )
