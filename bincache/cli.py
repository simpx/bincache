import os
import sys
import hashlib
import subprocess
import pickle
import io
import six

def md5(file_path):
    hash_md5 = hashlib.md5()
    with io.open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

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

def get_file_info(file_path):
    return (md5(file_path),)

def generate_hash(binary, args):
    binary_info = get_file_info(binary)
    libs = get_dynamic_libs(binary)
    libs_info = [(lib, os.path.getmtime(lib)) for lib in libs]
    hash_data = str(binary_info) + str(libs_info) + " ".join(args)
    return hashlib.sha256(six.b(hash_data)).hexdigest()

def cache_output(cache_key, output):
    cache_dir = 'bincache'
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    cache_file = os.path.join(cache_dir, cache_key)
    with io.open(cache_file, 'wb') as f:
        pickle.dump(output, f)

def get_cached_output(cache_key):
    cache_dir = 'bincache'
    cache_file = os.path.join(cache_dir, cache_key)
    if os.path.exists(cache_file):
        with io.open(cache_file, 'rb') as f:
            return pickle.load(f)  # 反序列化二进制数据
    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: bincache.py <binary> <arguments>")
        sys.exit(1)
    binary = sys.argv[1]
    args = sys.argv[2:]
    cache_key = generate_hash(binary, args)
    
    cached_output = get_cached_output(cache_key)
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
    cache_output(cache_key, stdout)
    sys.stdout.write(stdout)

if __name__ == "__main__":
    main()