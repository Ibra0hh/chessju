import uuid

from redis import Redis
from rq import Queue

from app.analysis.tasks import run_analysis_job
from app.config import get_settings

ANALYSIS_QUEUE_NAME = "analysis"


def get_analysis_queue() -> Queue:
    settings = get_settings()
    connection = Redis.from_url(settings.valkey_url)
    return Queue(
        ANALYSIS_QUEUE_NAME,
        connection=connection,
        default_timeout=settings.analysis_job_timeout_seconds,
    )


def enqueue_analysis_job(job_id: uuid.UUID) -> None:
    settings = get_settings()
    queue = get_analysis_queue()
    queue.enqueue(
        run_analysis_job,
        str(job_id),
        job_timeout=settings.analysis_job_timeout_seconds,
    )
