import os
import pickle
import pytest
import tempfile
from unittest import mock
from bincache.cache import get_cache_file_path, put, get

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
