import os
import sys
import hashlib
import subprocess
import pickle
import shutil
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

def hash_file_md5(file_path):
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            md5.update(chunk)
    return md5.hexdigest()

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

def generate_cache_key(binary, args):
    binary_info = hash_file_md5(binary) 
    libs = get_dynamic_libs(binary)
    libs_info = [(lib, os.path.getmtime(lib)) for lib in libs]
    hash_data = str(binary_info) + str(libs_info) + " ".join(args)
    return hashlib.md5(hash_data.encode('utf-8')).hexdigest()

def get_cache_file_path(binary, args):
    cache_key = generate_cache_key(binary, args)
    prefix = cache_key[:2]
    suffix = cache_key[2:4]
    filename = cache_key[4:]
    cache_object_folder = os.path.join(CACHE_DIR, prefix, suffix)
    return os.path.join(cache_object_folder, filename)

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

def get_cached_output(binary, args):
    cache_file = get_cache_file_path(binary, args)
    data = read_file(cache_file)
    if data:
        return pickle.loads(data)
    return None

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
def find_binary(command):
    #TODO alias
    binary_path = shutil.which(command)
    if binary_path is None:
        print(f"Binary or Command {command} not found")
        sys.exit(1)
    return binary_path

def main():
    if len(sys.argv) < 2:
        print("Usage: bincache <binary_or_command> <arguments>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    binary = find_binary(command)
    args = sys.argv[2:]

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
