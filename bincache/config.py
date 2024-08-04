import os
from configparser import ConfigParser

DEFAULT_CACHE_DIR = os.path.join(os.path.expanduser("~"), '.cache', 'bincache')
DEFAULT_MAX_SIZE = 5 * 1024 * 1024 * 1024  # 5G
DEFAULT_LOG_FILE = ""
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_STATS = False
CONFIG_FILE = 'bincache.conf'

_config = None

def parse_size(size_str):
    size_str = size_str.upper()
    units = {"B": 1, "K": 1024, "M": 1024**2, "G": 1024**3}
    for unit in units:
        if size_str.endswith(unit):
            return int(size_str[:-1]) * units[unit]
    return int(size_str)

def get_config():
    global _config
    if not _config:
        cache_dir = os.getenv('BINCACHE_DIR', DEFAULT_CACHE_DIR)
        config_file = os.path.join(cache_dir, CONFIG_FILE)
        config_params = {
            'max_size': DEFAULT_MAX_SIZE,
            'log_file': DEFAULT_LOG_FILE,
            'log_level': DEFAULT_LOG_LEVEL,
            'stats': DEFAULT_STATS,
            'temporary_dir': os.path.join(cache_dir, 'tmp'),
            'cache_dir': cache_dir
        }
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config_string = f"[DEFAULT]\n" + f.read()
            config = ConfigParser(allow_no_value=True)
            config.read_string(config_string)
            if config.has_option('DEFAULT', 'max_size') and config.get('DEFAULT', 'max_size') is not None:
                config_params['max_size'] = parse_size(config.get('DEFAULT', 'max_size'))
            if config.has_option('DEFAULT', 'log_file') and config.get('DEFAULT', 'log_file') is not None:
                log_file = config.get('DEFAULT', 'log_file')
                if not os.path.isabs(log_file) and not log_file.startswith('.' + os.sep):
                    log_file = os.path.join(cache_dir, log_file)
                config_params['log_file'] = log_file
            if config.has_option('DEFAULT', 'log_level') and config.get('DEFAULT', 'log_level') is not None:
                config_params['log_level'] = config.get('DEFAULT', 'log_level').upper()
            if config.has_option('DEFAULT', 'stats') and config.get('DEFAULT', 'stats') is not None:
                config_params['stats'] = config.getboolean('DEFAULT', 'stats')
            if config.has_option('DEFAULT', 'temporary_dir') and config.get('DEFAULT', 'temporary_dir') is not None:
                config_params['temporary_dir'] = config.get('DEFAULT', 'temporary_dir')
        _config = config_params
    return _config