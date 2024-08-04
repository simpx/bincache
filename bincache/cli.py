import os
import sys
import subprocess
import shutil

from bincache.config import get_config
from bincache.log import get_logger
from bincache.cache import get, put
from bincache.signature import generate_signature

config = get_config()
logger = get_logger()

def execute_command(command, args):
    try:
        result = subprocess.Popen([command] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = result.communicate()
        stdout = stdout.decode('utf-8')
        stderr = stderr.decode('utf-8')
        return result.returncode, stdout, stderr
    except FileNotFoundError:
        return 127, "", f"bincache: command not found: {command}\n"
    except PermissionError:
        return 126, "", f"bincache: permission denied: {command}\n"
    except OSError as e:
        return 1, "", f"bincache: OS error: {str(e)}\n"
    except Exception as e:
        return 1, "", f"bincache: error executing {command}: {str(e)}\n"

def main():
    if len(sys.argv) < 2:
        print("Usage: bincache <binary_or_command> <arg1> [arg2 ... argN]")
        print("  <binary_or_command> can be a path to an executable binary or a shell command.")
        print("  <arg1> ... <argN>   are the arguments to be passed to the binary or command.")
        print()
        print("Examples:")
        print("  bincache date")
        print("  bincache ./a.out -l -a")
        sys.exit(1)
    binary = shutil.which(sys.argv[1])
    args = sys.argv[2:]

    cache_key = generate_signature(binary, args)
    cached_output = get(cache_key)
    if cached_output is not None:
        sys.stdout.write(cached_output)
        sys.exit(0)
    
    returncode, stdout, stderr = execute_command(sys.argv[1], args)

    if returncode == 0 and not stderr:
        try:
            put(cache_key, stdout)
        except Exception as e:
            pass
    sys.stdout.write(stdout)
    sys.stderr.write(stderr)
    sys.exit(returncode)

if __name__ == "__main__":
    main()