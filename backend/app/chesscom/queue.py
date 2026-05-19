import uuid

from redis import Redis
from rq import Queue

from app.config import get_settings

CHESSCOM_QUEUE_NAME = "chesscom"


def get_chesscom_queue() -> Queue:
    settings = get_settings()
    connection = Redis.from_url(settings.valkey_url)
    return Queue(
        CHESSCOM_QUEUE_NAME,
        connection=connection,
        default_timeout=settings.chesscom_sync_timeout_seconds,
    )


def enqueue_chesscom_sync_job(sync_job_id: uuid.UUID) -> None:
    from app.chesscom.tasks import sync_chesscom_games

    settings = get_settings()
    queue = get_chesscom_queue()
    queue.enqueue(
        sync_chesscom_games,
        str(sync_job_id),
        job_timeout=settings.chesscom_sync_timeout_seconds,
    )
