from redis.asyncio import Redis

from app.config import get_settings


async def check_valkey_connection() -> bool:
    client = Redis.from_url(get_settings().valkey_url, decode_responses=True)
    try:
        return bool(await client.ping())
    except Exception:
        return False
    finally:
        await client.aclose()
