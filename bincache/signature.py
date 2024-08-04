import hashlib
import subprocess

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
        elif line.startswith('/'):
            path = line.strip()
        else:
            name = line.strip()
        libs.append((name, path, address))
    return libs

def generate_signature(binary, args):
    if not binary:
        return None
    binary_info = hash_file_md5(binary) 
    libs = get_dynamic_libs(binary)
    if libs is None:
        return None
    libs_info = [(libpath, hash_file_md5(libpath)) for libname, libpath, address in libs if libpath]
    hash_data = str(binary_info) + str(libs_info) + " ".join(args)
    return hashlib.md5(hash_data.encode('utf-8')).hexdigest()