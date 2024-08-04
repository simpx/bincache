import os
import pickle
import tempfile
from bincache.config import get_config
from bincache import logger

def get_cache_file_path(key):
    config = get_config()
    prefix = key[:2]
    filename = key[2:]
    cache_file_folder = os.path.join(config['cache_dir'], prefix)
    return os.path.join(cache_file_folder, filename)

# TODO Add file locking or other mechanism to handle multi-process access
def trim_cache_dir_to_limit(cache_dir, limit_size_in_bytes):
    """removing old files if the total size exceeds the limit."""
    total_size = 0
    file_paths = []
    for root, dirs, files in os.walk(cache_dir):
        # Ignore the files in the first level directory (configuration files)
        if root == cache_dir:
            continue
        for name in files:
            file_path = os.path.join(root, name)
            file_size = os.path.getsize(file_path)
            total_size += file_size
            file_paths.append((file_path, os.path.getmtime(file_path), file_size))
    logger.info(f"totle_size: {total_size}, limit_size_in_bytes: {limit_size_in_bytes}")
    if total_size <= limit_size_in_bytes:
        return
    # Sort files by modification time (oldest first)
    file_paths.sort(key=lambda x: x[1])
    for file_path, _, file_size in file_paths:
        os.remove(file_path)
        logger.info(f"{file_path} removed, totle_size: {total_size}, limit_size_in_bytes: {limit_size_in_bytes}")
        total_size -= file_size
        if total_size <= limit_size_in_bytes:
            break

def put(key, value):
    config = get_config()
    cache_file_path = get_cache_file_path(key)
    if cache_file_path is None:
        return
    cache_file_folder = os.path.dirname(cache_file_path)
    os.makedirs(cache_file_folder, exist_ok=True)
    if config['temporary_dir']:
        os.makedirs(config['temporary_dir'], exist_ok=True)
        with tempfile.NamedTemporaryFile(delete=False, dir=config['temporary_dir']) as temp_file:
            temp_path = temp_file.name
            pickle.dump(value, temp_file)
        try:
            os.rename(temp_path, cache_file_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    else:
        pickle.dump(value, cache_file_path)

    if 'max_size' in config:
        trim_cache_dir_to_limit(config['cache_dir'], config['max_size'])

def get(key):
    if not key:
        return None
    cache_file_path = get_cache_file_path(key)
    if not cache_file_path:
        return None
    try:
        with open(cache_file_path, 'rb') as f:
            data = f.read()
            return pickle.loads(data)
    except FileNotFoundError:
        return None