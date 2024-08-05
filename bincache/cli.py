import os
import sys
import subprocess
import shutil

from bincache.cache import get, put
from bincache.signature import generate_signature

def execute_command(argv):
    try:
        command = argv[0]
        result = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = result.communicate()
        stdout = stdout.decode('utf-8')
        stderr = stderr.decode('utf-8')
        return result.returncode, stdout, stderr
    except FileNotFoundError:
        return 127, "", f"bincache: command not found: {command}\n"
    except PermissionError:
        return 126, "", f"bincache: permission denied: {command}\n"
    except OSError as e:
        return 1, "", f"bincache: OS error: {command}: {str(e)}\n"
    except Exception as e:
        return 1, "", f"bincache: error executing: {command}: {str(e)}\n"

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
    try:
        binary = shutil.which(sys.argv[1])
        args = sys.argv[2:]
        cache_key = generate_signature(binary, args)
        cached_output = get(cache_key)
        if cached_output is not None:
            print(cached_output, end="")
            sys.exit(0)
    except Exception as e:
        pass
    
    returncode, stdout, stderr = execute_command(sys.argv[1:])
    if returncode == 0 and not stderr:
        try:
            put(cache_key, stdout)
        except Exception as e:
            pass
    print(stdout, end="")
    print(stderr, end="", file=sys.stderr)
    sys.exit(returncode)

if __name__ == "__main__":
    main()