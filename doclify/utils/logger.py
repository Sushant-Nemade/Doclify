import logging


def get_logger(name: str = __name__) -> logging.Logger:
    project_logger = logging.getLogger("doclify")
    if not project_logger.handlers:
        project_logger.addHandler(logging.NullHandler())
    project_logger.propagate = False
    return logging.getLogger(name)
