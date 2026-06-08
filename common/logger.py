import logging
import os


def setup_logger(name):
    log_dir = "logs"

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(
        os.path.join(log_dir, f"{name}.log")
    )

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger