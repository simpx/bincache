import os
import sys
import hashlib
import subprocess
import tempfile
import pickle
import shutil

from .config import read_config
from .log import get_logger

config = read_config(os.path.join(CACHE_DIR, CONFIG_FILE))
logger = get_logger(config)

def hash_file_md5(file_path):
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            md5.update(chunk)
    return md5.hexdigest()

'''
return list of ('libname, 'libpath', 'address') or None
'''
def get_dynamic_libs(binary):
    result = subprocess.Popen(['ldd', binary], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = result.communicate()
    if result.returncode != 0:
        print(f"Failed to get dynamic libraries for {binary}")
        return None
    libs = []
    for line in stdout.decode('utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        name, path, address = "", "", ""
        if '(' in line and ')' in line:
            address_start = line.index('(') + 1
            address_end = line.index(')')
            address = line[address_start:address_end].strip()
            line = line[:address_start - 1].strip()
        if '=>' in line:
            parts = line.split('=>')
            name = parts[0].strip()
            path = parts[1].strip()
        else:
            path = line.strip()
        libs.append((name, path, address))
    return libs

def generate_cache_key(binary, args):
    if not binary:
        return None
    binary_info = hash_file_md5(binary) 
    libs = get_dynamic_libs(binary)
    if libs is None:
        return None
    libs_info = [(libname, hash_file_md5(libpath)) for libname, libpath, address in libs if libpath]
    hash_data = str(binary_info) + str(libs_info) + " ".join(args)
    return hashlib.md5(hash_data.encode('utf-8')).hexdigest()

def get_cache_file_path(cache_key):
    prefix = cache_key[:2]
    filename = cache_key[2:]
    cache_file_folder = os.path.join(CACHE_DIR, prefix)
    return os.path.join(cache_file_folder, filename)

def cache_put(cache_key, output):
    cache_file_path = get_cache_file_path(cache_key)
    if cache_file_path is None:
        return
    cache_file_folder = os.path.dirname(cache_file_path)
    os.makedirs(cache_file_folder, exist_ok=True)
    if config['temporary_dir']:
        os.makedirs(config['temporary_dir'], exist_ok=True)
        with tempfile.NamedTemporaryFile(delete=False, dir=config['temporary_dir']) as temp_file:
            temp_path = temp_file.name
            pickle.dump(output, temp_file)
        try:
            os.rename(temp_path, cache_file_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    else:
        pickle.dump(output, cache_file_path)

def cache_get(cache_key):
    if not cache_key:
        return None
    cache_file_path = get_cache_file_path(cache_key)
    if not cache_file_path:
        return None
    try:
        with open(cache_file_path, 'rb') as f:
            data = f.read()
            return pickle.loads(data)
    except FileNotFoundError:
        return None

def find_binary(command):
    binary_path = shutil.which(command)
    if binary_path is None:
        print(f"Binary or Command {command} not found")
        return None
    return binary_path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: bincache <binary_or_command> <arguments>")
        sys.exit(1)
    binary = find_binary(sys.argv[1])
    args = sys.argv[2:]
    cache_key = generate_cache_key(binary, args)
    cached_output = cache_get(cache_key)
    if cached_output is not None:
        sys.stdout.write(cached_output)
    else:
        result = subprocess.Popen(sys.argv[1:], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = result.communicate()
        stdout = stdout.decode('utf-8')
        stderr = stderr.decode('utf-8')
        if result.returncode == 0 and not stderr:
            try:
                cache_put(cache_key, stdout)
            except Exception as e:
                pass
        sys.stdout.write(stdout)
        sys.stderr.write(stderr)
        sys.exit(result.returncode)