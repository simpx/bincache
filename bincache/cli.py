import os
import sys
import hashlib
import subprocess
import pickle
import shutil
from configparser import ConfigParser

#################
# Configuration #
#################
# Cache directory, default ~/.cache/bincache
DEFAULT_CACHE_DIR = os.path.join(os.path.expanduser("~"), '.cache', 'bincache')
DEFAULT_MAX_SIZE = 5 * 1024 * 1024 * 1024  # 5G
DEFAULT_LOG_FILE = ""
DEFAULT_STATS = False
CACHE_DIR = os.getenv('BINCACHE_DIR', DEFAULT_CACHE_DIR)
DEFAULT_TEMPORARY_DIR = os.path.join(CACHE_DIR, 'temporary_dir')
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
        'stats': DEFAULT_STATS,
        'temporary_dir': DEFAULT_TEMPORARY_DIR
    }
    if os.path.exists(config_file):
        config = ConfigParser(allow_no_value=True)
        config.read(config_file)
        if config.has_option('DEFAULT', 'max_size'):
            config_params['max_size'] = parse_size(config.get('DEFAULT', 'max_size'))
        if config.has_option('DEFAULT', 'log_file'):
            config_params['log_file'] = config.get('DEFAULT', 'log_file')
        if config.has_option('DEFAULT', 'stats'):
            config_params['stats'] = config.getboolean('DEFAULT', 'stats')
        if config.has_option('DEFAULT', 'temporary_dir'):
            config_params['temporary_dir'] = config.get('DEFAULT', 'temporary_dir')
    return config_params

config = read_config(os.path.join(CACHE_DIR, CONFIG_FILE))

##################
# File Operation #
##################
def read_file(file_path):
    try:
        with open(file_path, 'rb') as f:
            return f.read()
    except FileNotFoundError:
        return None

def write_file(file_path, data):
    """Write data to a file using a temporary file and then renaming it to ensure atomicity."""
    temp_path = file_path + ".tmp"
    with open(temp_path, 'wb') as f:
        f.write(data)
    os.rename(temp_path, file_path)

def remove_file(file_path):
    """Remove a file if it exists."""
    try:
        os.remove(file_path)
    except FileNotFoundError:
        pass


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
    filename = cache_key[2:]
    cache_file_folder = os.path.join(CACHE_DIR, prefix)
    return os.path.join(cache_file_folder, filename)

def cache_output(binary, args, output):
    cache_file_path = get_cache_file_path(binary, args)
    cache_file_folder = os.path.dirname(cache_file_path)
    os.makedirs(cache_file_folder, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(delete=False, dir=config['temporary_dir']) as temp_file:
            temp_path = temp_file.name
            pickle.dump(output, temp_file)
        try:
            os.rename(temp_path, file_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    except Exception as e:
        pass

def get_cached_output(binary, args):
    cache_file = get_cache_file_path(binary, args)
    try:
        with open(cache_file, 'rb') as f:
            data = f.read()
            return pickle.loads(data)
    except FileNotFoundError:
        return None

def find_binary(command):
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
        sys.stdout.write(cached_stdout)
        return
    
    result = subprocess.Popen([binary] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = result.communicate()
    stdout = stdout.decode('utf-8')
    stderr = stderr.decode('utf-8')
    
    # Don't cache if there was stderr, even if returncode was 0
    if result.returncode != 0 or stderr:
        sys.stdout.write(stdout)
        sys.stderr.write(stderr)
        sys.exit(result.returncode)
    else:
        cache_output(binary, args, stdout)
        sys.stdout.write(stdout)

if __name__ == "__main__":
    main()
