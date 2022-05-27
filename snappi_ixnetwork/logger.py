import sys
import time
import logging

APP_LOGGER_NAME = 'snappi_ixnetwork'


def setup_applevel_logger(log_level, file_name=None, module_name=None):
    logger = logging.getLogger(APP_LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(fmt="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
                                  datefmt="%Y-%m-%d %H:%M:%S")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    logger.handlers.clear()
    logger.addHandler(sh)
    if file_name:
        fh = logging.FileHandler(file_name)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    if module_name is not None:
        logger = get_logger(module_name)
    return logger


def get_logger(module_name):
    module_name = ".".join(str(module_name).split(".")[1:])
    return logging.getLogger(APP_LOGGER_NAME).getChild(module_name)