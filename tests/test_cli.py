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

def test_no_arguments(monkeypatch, capsys):
    # 模拟命令行参数为空
    monkeypatch.setattr(sys, 'argv', ['bincache'])
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1

    captured = capsys.readouterr()
    assert "Usage: bincache <binary_or_command> <arg1> [arg2 ... argN]" in captured.out