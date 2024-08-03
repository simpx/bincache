import logging
from config import get_config

config = get_config()

_logger

def get_logger():
    global _logger
    if _logger is None:
        _logger = logging.getLogger('bincache')
        log_level = getattr(logging, config['log_level'], logging.INFO)
        _logger.setLevel(log_level)
        if config['log_file']:
            log_handler = logging.FileHandler(config['log_file'])
            log_formatter = logging.Formatter('%(asctime)s - PID: %(process)d - PWD: %(pathname)s - %(message)s')
            log_handler.setFormatter(log_formatter)
            _logger.addHandler(log_handler)
    return _logger