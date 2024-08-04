import os
import sys
import subprocess
import shutil
import pytest
from unittest import mock
from io import StringIO

from bincache.cli import main
from bincache.cache import get, put
from bincache.config import get_config
from bincache.log import get_logger

@pytest.fixture
def mock_config(monkeypatch, tmpdir):
    temp_cache_dir = str(tmpdir.mkdir("cache"))
    temp_tempdir = str(tmpdir.mkdir("tempdir"))
    mock_config = {'cache_dir': temp_cache_dir, 'temporary_dir': temp_tempdir}
    monkeypatch.setattr('bincache.config.get_config', lambda: mock_config)
    return mock_config

@pytest.fixture
def mock_logger(monkeypatch):
    logger = mock.Mock()
    monkeypatch.setattr('bincache.log.get_logger', lambda: logger)

@pytest.fixture
def mock_binary(monkeypatch):
    alias_map = {
        'dummy_command_cache': '/bin/dummy_command',
        'echo': '/bin/echo',
        './error': './error',
        './error_but_cache': './error_but_cache',
        './command_with_stderr': './command_with_stderr',
    }
    cache_map = {
        ('/bin/dummy_command',): {
            'signature': 'dummy_command_signature',
            'cached_output': 'dummy_command_cached_output',
        },
        ('/bin/echo', 'Hello'): {
            'signature': 'echo_signature',
        },
        ('./error',): {
            'signature': 'error_signature',
        },
        ('./error_but_cache',): {
            'signature': 'error_but_cache_signature',
            'cached_output': 'error_but_cached_output',
        },
        ('./command_with_stderr',): {
            'signature': 'command_with_stderr_signature',
        },
    }
    command_map = {
        ('dummy_command_cache',): {
            'stdout': 'dummy_command_stdout',
            'stderr': '',
            'returncode': 0
        },
        ('echo', 'Hello'): {
            'stdout': 'Hello',
            'stderr': '',
            'returncode': 0
        },
        ('./error',): {
            'stdout': 'error_stdout',
            'stderr': 'error_stderr',
            'returncode': 1
        },
        ('./error_but_cache',): {
            'stdout': 'error_stdout',
            'stderr': 'error_stderr',
            'returncode': 1
        },
        ('./command_with_stderr',): {
            'stdout': 'error_stdout',
            'stderr': 'error_stderr',
            'returncode': 0
        },
        ('./not_found',): {
            'raise_error': FileNotFoundError
        }
    }

    def which(cmd):
        return alias_map.get(cmd)

    def generate_signature(binary, args):
        details = cache_map.get((binary,) + tuple(args))
        return details.get('signature') if details else None

    def cache_get(key):
        if key is None:
            return None
        for binary, details in cache_map.items():
            if key == details.get('signature'):
                return details.get('cached_output')
        return None

    def popen_mock(*popen_args, **kwargs):
        cmd = popen_args[0]
        details = command_map.get(tuple(cmd))
        if details:
            if 'raise_error' in details:
                raise details['raise_error']
            mock_proc = mock.Mock()
            mock_proc.communicate.return_value = (details['stdout'].encode('utf-8'), details['stderr'].encode('utf-8'))
            mock_proc.returncode = details.get('returncode')
            return mock_proc
        raise ValueError(f"Unexpected command: {cmd}")
    monkeypatch.setattr('bincache.cli.shutil.which', which)
    monkeypatch.setattr('bincache.cli.generate_signature', generate_signature)
    monkeypatch.setattr('bincache.cli.get', cache_get)
    monkeypatch.setattr(subprocess, 'Popen', popen_mock)

# case: 没有提供命令行参数
def test_no_arguments(monkeypatch, capsys):
    monkeypatch.setattr(sys, 'argv', ['bincache'])
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1

    captured = capsys.readouterr()
    assert "Usage: bincache <binary_or_command> <arg1> [arg2 ... argN]" in captured.out

# case: 命中缓存
def test_cached_output(monkeypatch, mock_binary, mock_logger, capsys):
    monkeypatch.setattr(sys, 'argv', ['bincache', 'dummy_command_cache'])
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0
    captured = capsys.readouterr()
    assert captured.out == "dummy_command_cached_output"

# case: 未命中缓存但执行成功，并验证结果被缓存
def test_exec_command_and_cache(monkeypatch, mock_config, mock_logger, capsys, mock_binary):
    monkeypatch.setattr(sys, 'argv', ['bincache', 'echo', 'Hello'])

    put_mock = mock.Mock()
    monkeypatch.setattr('bincache.cli.put', put_mock)
    
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0

    captured = capsys.readouterr()
    assert captured.out.strip() == "Hello"
    
    # Verify that the command output was cached
    put_mock.assert_called_once_with('echo_signature', 'Hello')

# case: 未命中缓存且执行失败，并验证结果不会被缓存
def test_exec_command_with_error(monkeypatch, mock_config, mock_logger, capsys, mock_binary):
    monkeypatch.setattr(sys, 'argv', ['bincache', './error'])

    put_mock = mock.Mock()
    monkeypatch.setattr('bincache.cli.put', put_mock)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1

    captured = capsys.readouterr()
    assert captured.out.strip() == 'error_stdout'
    assert captured.err.strip() == 'error_stderr'

    # Verify that the command output was not cached
    put_mock.assert_not_called()

# case: 命中缓存，哪怕实际结果可能会失败，也会返回缓存
def test_cached_output_with_error(monkeypatch, mock_binary, mock_logger, capsys):
    monkeypatch.setattr(sys, 'argv', ['bincache', './error_but_cache'])
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0  # Assuming we read from cache and do not execute
    captured = capsys.readouterr()
    assert captured.out == "error_but_cached_output"

# case: 未命中缓存且执行成功，但由于有stderr，所以不会被缓存
def test_exec_command_with_error(monkeypatch, mock_config, mock_logger, capsys, mock_binary):
    monkeypatch.setattr(sys, 'argv', ['bincache', './command_with_stderr'])

    put_mock = mock.Mock()
    monkeypatch.setattr('bincache.cli.put', put_mock)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0

    captured = capsys.readouterr()
    assert captured.out.strip() == 'error_stdout'
    assert captured.err.strip() == 'error_stderr'

    # Verify that the command output was not cached
    put_mock.assert_not_called()

# case: 命令不存在
def test_exec_not_found(monkeypatch, mock_binary, mock_config, mock_logger, capsys):
    monkeypatch.setattr(sys, 'argv', ['bincache', './not_found'])

    put_mock = mock.Mock()
    monkeypatch.setattr('bincache.cli.put', put_mock)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 127

    captured = capsys.readouterr()
    assert captured.out.strip() == ''
    assert captured.err.strip() == 'bincache: command not found: ./not_found'

    # Verify that the command output was not cached
    put_mock.assert_not_called()