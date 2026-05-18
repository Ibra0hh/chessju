import logging
import time


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    logger = logging.getLogger("chessju.worker")
    logger.info("ChessJU worker started in idle foundation mode")

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
