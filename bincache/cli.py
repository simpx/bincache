import os
import sys
import hashlib
import subprocess
import pickle
import io
import six
import fcntl
from configparser import ConfigParser

# 默认缓存目录和配置文件名
DEFAULT_CACHE_DIR = os.path.join(os.path.expanduser("~"), '.cache', 'bincache')
CONFIG_FILE = 'bincache.conf'
DEFAULT_MAX_SIZE = 5 * 1024 * 1024 * 1024  # 5G
LOCK_FILE_NAME = '.lock'

# 读取配置
def read_config(cache_dir):
    config = ConfigParser()
    config_file = os.path.join(cache_dir, CONFIG_FILE)
    config_params = {'max_size': DEFAULT_MAX_SIZE}
    
    if os.path.exists(config_file):
        config.read(config_file)
        if config.has_option('cache', 'max_size'):
            config_params['max_size'] = parse_size(config.get('cache', 'max_size'))
    return config_params

# 解析大小配置
def parse_size(size_str):
    size_str = size_str.lower()
    units = {"b": 1, "k": 1024, "m": 1024**2, "g": 1024**3}
    for unit in units:
        if size_str.endswith(unit):
            return int(size_str[:-1]) * units[unit]
    return int(size_str)

# 获取缓存目录
def get_cache_dir():
    return os.getenv('BINCACHE_DIR', DEFAULT_CACHE_DIR)

# 根据文件路径和文件名生成摘要
def generate_initial_hash(path):
    hasher = hashlib.sha256()
    hasher.update(six.b(path))
    return hasher.hexdigest()

# 获取缓存文件路径
def get_cache_file_path(binary, args):
    hash1 = generate_initial_hash(binary)
    prefix = hash1[:2]
    suffix = hash1[2:]
    cache_object_folder = os.path.join(get_cache_dir(), prefix, suffix)
    cache_key = generate_hash(binary, args)
    return os.path.join(cache_object_folder, cache_key)

# MD5摘要
def md5(file_path):
    hash_md5 = hashlib.md5()
    with io.open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

# 动态库信息
def get_dynamic_libs(binary):
    result = subprocess.Popen(['ldd', binary], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = result.communicate()
    
    if result.returncode != 0:
        print("Failed to get dynamic libraries for {}".format(binary))
        sys.exit(1)
    
    libs = []
    for line in stdout.decode('utf-8').splitlines():
        if '=>' in line:
            parts = line.split('=>')
            if len(parts) > 1:
                lib_path = parts[1].split('(')[0].strip()
                if lib_path:
                    libs.append(lib_path)
        else:
            lib_path = line.split()[0].strip()
            if lib_path:
                libs.append(lib_path)
    
    return libs

# 文件信息
def get_file_info(file_path):
    return (md5(file_path), )

# 生成hash
def generate_hash(binary, args):
    binary_info = get_file_info(binary)
    libs = get_dynamic_libs(binary)
    libs_info = [(lib, os.path.getmtime(lib)) for lib in libs]
    hash_data = str(binary_info) + str(libs_info) + " ".join(args)
    return hashlib.sha256(six.b(hash_data)).hexdigest()

# 锁定函数
def acquire_lock(lock_file_path, lock_type):
    lock_file = open(lock_file_path, 'w')
    fcntl.flock(lock_file, lock_type)
    return lock_file

def release_lock(lock_file):
    fcntl.flock(lock_file, fcntl.LOCK_UN)
    lock_file.close()

# 缓存输出
def cache_output(binary, args, output):
    cache_file = get_cache_file_path(binary, args)
    cache_object_folder = os.path.dirname(cache_file)
    os.makedirs(cache_object_folder, exist_ok=True)
    lock_file_path = os.path.join(cache_object_folder, LOCK_FILE_NAME)
    
    # Acquire write lock
    lock_file = acquire_lock(lock_file_path, fcntl.LOCK_EX)
    
    try:
        with io.open(cache_file, 'wb') as f:
            pickle.dump(output, f)
        enforce_cache_size()
    finally:
        # Release write lock
        release_lock(lock_file)

# 获取缓存输出
def get_cached_output(binary, args):
    cache_file = get_cache_file_path(binary, args)
    cache_object_folder = os.path.dirname(cache_file)
    lock_file_path = os.path.join(cache_object_folder, LOCK_FILE_NAME)
    
    if os.path.exists(cache_file):
        # Acquire read lock
        lock_file = acquire_lock(lock_file_path, fcntl.LOCK_SH)
        
        try:
            with io.open(cache_file, 'rb') as f:
                return pickle.load(f)
        finally:
            # Release read lock
            release_lock(lock_file)
    return None

# 强制缓存大小
def enforce_cache_size():
    cache_dir = get_cache_dir()
    config = read_config(cache_dir)
    max_size = config['max_size']
    total_size = 0
    folders_with_files = []

    for prefix in os.listdir(cache_dir):
        prefix_path = os.path.join(cache_dir, prefix)
        if os.path.isdir(prefix_path):
            for suffix in os.listdir(prefix_path):
                cache_object_folder = os.path.join(prefix_path, suffix)
                if os.path.isdir(cache_object_folder):
                    folder_size = 0
                    folder_files = []
                    for f in os.listdir(cache_object_folder):
                        if f == LOCK_FILE_NAME:
                            continue
                        file_path = os.path.join(cache_object_folder, f)
                        file_size = os.path.getsize(file_path)
                        total_size += file_size
                        folder_size += file_size
                        last_access_time = os.path.getatime(file_path)
                        folder_files.append((last_access_time, file_size, file_path))
                    folders_with_files.append((folder_size, folder_files, cache_object_folder))

    if total_size <= max_size:
        return

    folders_with_files.sort(reverse=True, key=lambda x: x[0])

    for folder_size, folder_files, cache_object_folder in folders_with_files:
        if total_size <= max_size:
            break
        
        if len(folder_files) > 1:
            folder_files.sort()
            with acquire_lock(os.path.join(cache_object_folder, LOCK_FILE_NAME), fcntl.LOCK_EX) as lock_file:
                for _, file_size, file_path in folder_files:
                    os.remove(file_path)
                    total_size -= file_size
                    if total_size <= max_size:
                        break
        else:
            _, file_size, file_path = folder_files[0]
            os.remove(file_path)
            total_size -= file_size

# 主函数
def main():
    if len(sys.argv) < 2:
        print("Usage: bincache.py <binary> <arguments>")
        sys.exit(1)

    binary = sys.argv[1]
    args = sys.argv[2:]
    cache_key = generate_initial_hash(binary)

    cached_output = get_cached_output(binary, args)
    if cached_output is not None:
        sys.stdout.write(cached_output)
        return

    result = subprocess.Popen([binary] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = result.communicate()
    stdout = stdout.decode('utf-8')
    stderr = stderr.decode('utf-8')

    if result.returncode != 0:
        sys.stderr.write(stderr)
        sys.exit(result.returncode)

    cache_output(binary, args, stdout)
    sys.stdout.write(stdout)

if __name__ == "__main__":
    main()