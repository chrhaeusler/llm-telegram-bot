# src/utils/logger.py

import logging
import os

logger = logging.getLogger(__name__)


def setup_logger() -> None:
    log_directory = "logs"
    os.makedirs(log_directory, exist_ok=True)

    log_filename = os.path.join(log_directory, "bot_log.log")

    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)


# ✅ Always configure on import
setup_logger()
