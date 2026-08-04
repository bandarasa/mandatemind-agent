import logging
import json
from pythonjsonlogger import jsonlogger

def setup_logging():
    logger = logging.getLogger("mandatemind-agent")
    logger.setLevel(logging.INFO)

    log_handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    log_handler.setFormatter(formatter)

    logger.addHandler(log_handler)
    return logger
