import logging
from config import get_config

config = get_config()

def get_logger():
    logger = logging.getLogger('bincache')
    log_level = getattr(logging, config['log_level'], logging.INFO)
    logger.setLevel(log_level)
    if config['log_file']:
        log_handler = logging.FileHandler(config['log_file'])
        log_formatter = logging.Formatter('%(asctime)s - PID: %(process)d - PWD: %(pathname)s - %(message)s')
        log_handler.setFormatter(log_formatter)
        logger.addHandler(log_handler)
    return logger