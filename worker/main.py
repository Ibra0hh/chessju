import logging

from redis import Redis
from rq import Queue, Worker

from app.analysis.queue import ANALYSIS_QUEUE_NAME
from app.chesscom.queue import CHESSCOM_QUEUE_NAME
from app.config import get_settings


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    logger = logging.getLogger("chessju.worker")
    settings = get_settings()
    connection = Redis.from_url(settings.valkey_url)
    queues = [
        Queue(ANALYSIS_QUEUE_NAME, connection=connection),
        Queue(CHESSCOM_QUEUE_NAME, connection=connection),
    ]
    logger.info(
        "ChessJU worker started for queues %s",
        ", ".join(queue.name for queue in queues),
    )
    Worker(queues, connection=connection).work()


if __name__ == "__main__":
    main()
