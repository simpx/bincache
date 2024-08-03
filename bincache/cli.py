import os
import sys
import subprocess
import shutil

from config import get_config
from log import get_logger
from cache import get, put

config = get_config()
logger = get_logger()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: bincache <binary_or_command> <arguments>")
        sys.exit(1)
    binary = shutil.which(sys.argv[1])
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