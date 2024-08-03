import os
import sys
import hashlib
import subprocess
import tempfile
import pickle
import shutil

from config import get_config
from log import get_logger
from cache import get, put

config = get_config()
logger = get_logger()

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
    cached_output = get(cache_key)
    if cached_output is not None:
        sys.stdout.write(cached_output)
    else:
        result = subprocess.Popen(sys.argv[1:], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = result.communicate()
        stdout = stdout.decode('utf-8')
        stderr = stderr.decode('utf-8')
        if result.returncode == 0 and not stderr:
            try:
                put(cache_key, stdout)
            except Exception as e:
                pass
        sys.stdout.write(stdout)
        sys.stderr.write(stderr)
        sys.exit(result.returncode)