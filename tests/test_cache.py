import os
import time
import pickle
import pytest
import tempfile
from unittest import mock
from bincache.cache import get_cache_file_path, put, get, trim_cache_dir_to_limit

@pytest.fixture
def setup_cache_config(monkeypatch, tmpdir):
    temp_cache_dir = str(tmpdir.mkdir("cache"))
    temp_tempdir = str(tmpdir.mkdir("tempdir"))
    mock_config = {'cache_dir': temp_cache_dir, 'temporary_dir': temp_tempdir}
    monkeypatch.setattr('bincache.cache.get_config', lambda: mock_config)
    return mock_config

def test_get_cache_file_path(setup_cache_config):
    key = 'ab1234'
    expected_path = os.path.join(setup_cache_config['cache_dir'], 'ab', '1234')
    actual_path = get_cache_file_path(key)
    assert actual_path == expected_path

def test_put_get(setup_cache_config):
    key = 'ab1234'
    value = {'key': 'value'}
    put(key, value)
    retrieved_value = get(key)
    assert value == retrieved_value

def test_get_with_invalid_key(setup_cache_config):
    key = None
    retrieved_value = get(key)
    assert retrieved_value is None

def test_get_non_existent_key(setup_cache_config):
    key = 'ef9999'
    retrieved_value = get(key)
    assert retrieved_value is None

def test_put_get_small_string(setup_cache_config):
    key = 'small123'
    value = 'a' * 10  # small string
    put(key, value)
    retrieved_value = get(key)
    assert value == retrieved_value

def test_put_get_large_string(setup_cache_config):
    key = 'large123'
    value = 'a' * 10**6  # large string
    put(key, value)
    retrieved_value = get(key)
    assert value == retrieved_value

def test_put_get_binary_content(setup_cache_config):
    key = 'binary123'
    value = b'\x00\xFF\x11\x33\x44'  # binary content
    put(key, value)
    retrieved_value = get(key)
    assert value == retrieved_value

def test_put_get_empty_content(setup_cache_config):
    key = 'empty123'
    value = b''  # empty content
    put(key, value)
    retrieved_value = get(key)
    assert value == retrieved_value

def test_put_get_very_large_content(setup_cache_config):
    key = 'verylarge123'
    value = b'a' * 10**7  # very large binary content
    put(key, value)
    retrieved_value = get(key)
    assert value == retrieved_value

def test_trim_cache_dir_to_limit_no_trim(setup_cache_config):
    key1 = 'key1'
    value1 = 'a' * 100
    key2 = 'key2'
    value2 = 'b' * 100
  
    put(key1, value1)
    put(key2, value2)

    trim_cache_dir_to_limit(setup_cache_config['cache_dir'], 300)

    assert get(key1) == value1
    assert get(key2) == value2

def test_trim_cache_dir_to_limit_with_trim(setup_cache_config):
    key1 = 'key1'
    value1 = 'a' * 100
    key2 = 'key2'
    value2 = 'b' * 100
    key3 = 'key3'
    value3 = 'c' * 100

    put(key1, value1)
    put(key2, value2)
    put(key3, value3)

    os.utime(get_cache_file_path(key1), (time.time() - 3, time.time() - 3))
    os.utime(get_cache_file_path(key2), (time.time() - 2, time.time() - 2))
    os.utime(get_cache_file_path(key3), (time.time() - 1, time.time() - 1))

    trim_cache_dir_to_limit(setup_cache_config['cache_dir'], 200)

    assert get(key1) == None
    assert get(key2) == None
    assert get(key3) == value3

def test_trim_cache_dir_to_limit_with_exact_limit(setup_cache_config):
    key1 = 'key1'
    value1 = 'a' * 100
    size1 = len(pickle.dumps(value1))
    key2 = 'key2'
    value2 = 'b' * 100
    size2 = len(pickle.dumps(value2))
    total_size = size1 + size2

    put(key1, value1)
    put(key2, value2)

    trim_cache_dir_to_limit(setup_cache_config['cache_dir'], total_size)

    assert get(key1) == value1
    assert get(key2) == value2