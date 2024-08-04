import os
import pickle
import tempfile
from bincache.config import get_config

def get_cache_file_path(key):
    config = get_config()
    prefix = key[:2]
    filename = key[2:]
    cache_file_folder = os.path.join(config['cache_dir'], prefix)
    return os.path.join(cache_file_folder, filename)

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