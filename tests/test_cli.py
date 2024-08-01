import os
import hashlib
import subprocess
import io
import pytest
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

def test_main_with_cache(mock_generate_hash, mock_get_cached_output, mock_popen, mock_cache_output, mock_sys_argv):
    mock_generate_hash.return_value = "dummy_cache_key"
    mock_get_cached_output.return_value = "cached_output"
    with patch('sys.stdout.write') as mock_print:
        cli.main()
        mock_print.assert_any_call("cached_output")
        mock_popen.assert_not_called()

def test_main_without_cache(mock_generate_hash, mock_get_cached_output, mock_popen, mock_cache_output, mock_sys_argv):
    mock_generate_hash.return_value = "dummy_cache_key"
    mock_get_cached_output.return_value = None
    
    mock_process = MagicMock()
    mock_popen.return_value = mock_process
    mock_process.communicate.return_value = (b"program output", b"")
    mock_process.returncode = 0

    with patch('sys.stdout.write') as mock_print:
        cli.main()
        mock_print.assert_any_call("program output")
        mock_cache_output.assert_called_once_with("dummy_cache_key", "program output")