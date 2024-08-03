import os
import sys
import hashlib
import subprocess
import pickle
import io
from configparser import ConfigParser
from .storage_backend import read_file, write_file, remove_file

# Cache directory, default ~/.cache/bincache
DEFAULT_CACHE_DIR = os.path.join(os.path.expanduser("~"), '.cache', 'bincache')
DEFAULT_MAX_SIZE = 5 * 1024 * 1024 * 1024  # 5G
DEFAULT_LOG_FILE = ""
DEFAULT_STATS = False

CACHE_DIR = os.getenv('BINCACHE_DIR', DEFAULT_CACHE_DIR)
CONFIG_FILE = 'bincache.conf'

def parse_size(size_str):
    size_str = size_str.upper()
    units = {"B": 1, "K": 1024, "M": 1024**2, "G": 1024**3}
    for unit in units:
        if size_str.endswith(unit):
            return int(size_str[:-1]) * units[unit]
    return int(size_str)

def read_config(config_file):

    config_params = {
        'max_size': DEFAULT_MAX_SIZE,
        'log_file': DEFAULT_LOG_FILE,
        'stats': DEFAULT_STATS
    }
    if os.path.exists(config_file):
        config = ConfigParser(allow_no_value=True)
        config.read(config_file)
        if config.has_option('DEFAULT', 'max_size'):
            config_params['max_size'] = parse_size(config.get('DEFAULT', 'max_size'))
            config_params['log_file'] = config.get('DEFAULT', 'log_file')
            config_params['stats'] = config.getboolean('DEFAULT', 'stats')
    return config_params

config = read_config(os.path.join(CACHE_DIR, CONFIG_FILE))

# 根据文件路径和文件名生成摘要
def generate_initial_hash(path):
    hasher = hashlib.sha256()
    hasher.update(path.encode('utf-8'))
    return hasher.hexdigest()

# 获取缓存文件路径
def get_cache_file_path(binary, args):
    hash1 = generate_initial_hash(binary)
    prefix = hash1[:2]
    suffix = hash1[2:]
    cache_object_folder = os.path.join(CACHE_DIR, prefix, suffix)
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
        print(f"Failed to get dynamic libraries for {binary}")
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
    return hashlib.sha256(hash_data.encode('utf-8')).hexdigest()

# 缓存输出
def cache_output(binary, args, output):
    cache_file = get_cache_file_path(binary, args)
    cache_object_folder = os.path.dirname(cache_file)
    os.makedirs(cache_object_folder, exist_ok=True)
    
    try:
        data = pickle.dumps(output)
        write_file(cache_file, data)
        enforce_cache_size()
    except Exception as e:
        print(f"Error caching output: {e}")

# 获取缓存输出
def get_cached_output(binary, args):
    cache_file = get_cache_file_path(binary, args)
    
    data = read_file(cache_file)
    if data:
        return pickle.loads(data)
    
    return None

# 强制缓存大小
def enforce_cache_size():
    cache_dir = CACHE_DIR
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
                        file_path = os.path.join(cache_object_folder, f)
                        if os.path.isfile(file_path):
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
            for _, file_size, file_path in folder_files:
                remove_file(file_path)
                total_size -= file_size
                if total_size <= max_size:
                    break
        else:
            _, file_size, file_path = folder_files[0]
            remove_file(file_path)
            total_size -= file_size

# 增加gc命令
def garbage_collection():
    cache_dir = CACHE_DIR
    
    try:
        for prefix in os.listdir(cache_dir):
            prefix_path = os.path.join(cache_dir, prefix)
            if os.path.isdir(prefix_path):
                for suffix in os.listdir(prefix_path):
                    cache_object_folder = os.path.join(prefix_path, suffix)
                    if os.path.isdir(cache_object_folder):
                        cache_files = [f for f in os.listdir(cache_object_folder) if os.path.isfile(os.path.join(cache_object_folder, f))]
                        
                        # 删除空的缓存目录
                        if not cache_files:
                            os.rmdir(cache_object_folder)
                        
                        # 保留最新的一个缓存文件
                        elif len(cache_files) > 1:
                            cache_files_paths = [os.path.join(cache_object_folder, f) for f in cache_files]
                            cache_files_paths.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                            for file_path in cache_files_paths[1:]:
                                remove_file(file_path)
                        if not os.listdir(cache_object_folder):
                            os.rmdir(cache_object_folder)
    except Exception as e:
        print(f"Garbage collection failed: {e}")

# 主函数
def main():
    if len(sys.argv) < 2:
        print("Usage: bincache.py <binary> <arguments> or bincache.py --gc")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "--gc":
        garbage_collection()
        return
    
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
