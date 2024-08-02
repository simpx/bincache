import os

def read_file(file_path):
    """Read the contents of a file. Return None if the file does not exist."""
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
