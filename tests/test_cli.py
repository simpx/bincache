import os
import hashlib
import subprocess
import tempfile
import io
import pytest
import shutil
import multiprocessing
import time
import six
import sys
from unittest.mock import patch, mock_open, MagicMock
from bincache import cli

@pytest.fixture
def mock_file_info():
    with patch('bincache.cli.get_file_info') as mock:
        yield mock

@pytest.fixture
def mock_dynamic_libs():
    with patch('bincache.cli.get_dynamic_libs') as mock:
        yield mock

@pytest.fixture
def mock_popen():
    with patch('subprocess.Popen') as mock:
        yield mock

@pytest.fixture
def mock_getmtime():
    with patch('os.path.getmtime') as mock:
        yield mock

def test_generate_hash(mock_file_info, mock_dynamic_libs, mock_getmtime):
    binary = "/path/to/binary"
    args = ["arg1", "arg2"]
    mock_file_info.return_value = ('dummy_md5',)
    mock_dynamic_libs.return_value = ['/path/to/lib1', '/path/to/lib2']
    mock_getmtime.side_effect = [1234567890, 987654321]
    
    expected_hash_data = str(('dummy_md5',)) + str([('/path/to/lib1', 1234567890), ('/path/to/lib2', 987654321)]) + " ".join(args)
    expected_hash_value = hashlib.sha256(six.b(expected_hash_data)).hexdigest()
    
    result = cli.generate_hash(binary, args)
    assert result == expected_hash_value

def test_get_dynamic_libs(mock_popen):
    binary = "/path/to/binary"
    mock_process = MagicMock()
    mock_popen.return_value = mock_process
    mock_process.communicate.return_value = (b"""/path/to/lib1 => /usr/lib/lib1.so (0x00007f8d6c0a1000)
/path/to/lib2 => /usr/lib/lib2.so (0x00007f8d6c0b2000)""", b"")
    mock_process.returncode = 0

    libs = cli.get_dynamic_libs(binary)
    assert libs == ["/usr/lib/lib1.so", "/usr/lib/lib2.so"]

def test_md5():
    file_path = "/path/to/file"
    expected_md5 = hashlib.md5(b"binary content").hexdigest()
    
    with patch("bincache.cli.io.open", mock_open(read_data=b"binary content"), create=True) as mock_file:
        result = cli.md5(file_path)
        assert result == expected_md5

@pytest.fixture
def mock_cache_output():
    with patch('bincache.cli.cache_output') as mock:
        yield mock

@pytest.fixture
def mock_get_cached_output():
    with patch('bincache.cli.get_cached_output') as mock:
        yield mock

@pytest.fixture
def mock_generate_hash():
    with patch('bincache.cli.generate_hash') as mock:
        yield mock

@pytest.fixture
def mock_sys_argv():
    original_argv = sys.argv
    sys.argv = ["bincache.py", "/path/to/binary", "arg1", "arg2"]
    yield
    sys.argv = original_argv

# Helper function to simulate a binary run
def run_dummy_binary(output_dir, filename, content):
    time.sleep(1)  # Simulate some processing delay
    with open(os.path.join(output_dir, filename), 'w') as f:
        f.write(content)
    return content

# Fixture to create and clean a temporary cache directory
@pytest.fixture
def temp_cache_dir(monkeypatch):
    temp_dir = tempfile.mkdtemp()
    monkeypatch.setenv('BINCACHE_DIR', temp_dir)
    yield temp_dir
    shutil.rmtree(temp_dir)

'''
def test_cache_output_and_retrieval(temp_cache_dir):
    binary = "/dummy/binary"
    args = ["arg1", "arg2"]
    output = "dummy output"

    cli.cache_output(binary, args, output)
    cached_output = cli.get_cached_output(binary, args)

    assert cached_output == output

def test_cache_directory_structure(temp_cache_dir):
    binary = "/dummy/binary"
    args = ["arg1", "arg2"]
    output = "dummy output"

    cli.cache_output(binary, args, output)
    cached_output = get_cached_output(binary, args)

    assert os.path.exists(temp_cache_dir)
    
    prefix_dir = os.listdir(temp_cache_dir)[0]
    suffix_dir = os.listdir(os.path.join(temp_cache_dir, prefix_dir))[0]
    cache_file = os.listdir(os.path.join(temp_cache_dir, prefix_dir, suffix_dir))[0]

    assert cached_output == output
    assert cache_file != ".lock"
'''

def test_parse_size():
    assert cli.parse_size("2G") == 2 * 1024 * 1024 * 1024
    assert cli.parse_size("1024M") == 1024 * 1024 * 1024
    assert cli.parse_size("100K") == 100 * 1024
    assert cli.parse_size("10b") == 10

# Helper function for multiprocessing test
def cache_in_process(binary, args, output, result_dict, proc_num):
    result_dict[proc_num] = run_dummy_binary(tempfile.gettempdir(), binary, output)
    cli.cache_output(binary, args, output)

'''
def test_multiple_process_locking(temp_cache_dir):
    binary = "/dummy/binary"
    args = ["arg1", "arg2"]
    output = "dummy output from process"

    # Create a manager dictionary to store results from processes
    manager = multiprocessing.Manager()
    result_dict = manager.dict()

    # Create multiple processes that will write to the cache simultaneously
    processes = [multiprocessing.Process(target=cache_in_process, args=(binary, args, f"{output} {i}", result_dict, i)) for i in range(5)]

    for p in processes:
        p.start()

    for p in processes:
        p.join()

    # Ensure that cache contains output from at least one of the processes without data corruption
    cached_output = get_cached_output(binary, args)
    assert cached_output.startswith(output.split()[0])

    # Verify that each dummy binary run produced the expected results
    for i in range(5):
        assert result_dict[i] == f"{output} {i}"

def test_cache_size_enforcement(temp_cache_dir):
    config_content = "[cache]\nmax_size = 2K\n"
    with open(os.path.join(temp_cache_dir, 'bincache.conf'), 'w') as config_file:
        config_file.write(config_content)
        
    binary = "/dummy/binary"
    args = ["arg1", "arg2"]

    # Add multiple outputs to exceed the cache size
    for i in range(5):
        output = f"dummy output {i}" + "x" * 500  # Each output ~ 500 bytes
        cli.cache_output(binary, args + [str(i)], output)

    enforce_cache_size()

    # Verify size enforcement
    total_size = sum(os.path.getsize(os.path.join(root, f)) for root, _, files in os.walk(temp_cache_dir) for f in files if f != 'bincache.conf')
    assert total_size <= parse_size('2K')

    # Ensure some of the cache files were removed
    cached_outputs = sum(1 for root, _, files in os.walk(temp_cache_dir) for f in files if f != 'bincache.conf')
    assert cached_outputs < 5
'''
