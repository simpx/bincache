import os
import tempfile
import pytest
import logging
from unittest import mock
from bincache.logger import get_logger, _logger
from bincache import config as bincache_config
from bincache import logger as bincache_log
import bincache.logger as log_module

# 重置 _logger
@pytest.fixture(autouse=True)
def reset_logger():
    bincache_log._logger = None

def test_get_logger_default_config():
    """测试 get_logger 函数在默认配置下的行为"""
    with mock.patch('bincache.logger.get_config', return_value={
        'log_level': 'INFO',
        'log_file': ''
    }):
        logger = get_logger()
        
        # 检查日志级别
        assert logger.level == logging.INFO
        
        # 检查日志处理程序
        assert len(logger.handlers) == 0


def test_get_logger_with_file():
    """测试 get_logger 函数在提供日志文件的情况下的行为"""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = os.path.join(tmpdir, 'test.log')
        
        with mock.patch('bincache.logger.get_config', return_value={
            'log_level': 'DEBUG',
            'log_file': log_file
        }):
            logger = get_logger()
            
            # 检查日志级别
            assert logger.level == logging.DEBUG
            
            # 检查是否有一个日志处理程序
            assert len(logger.handlers) == 1
            
            # 检查日志处理程序的类型
            assert isinstance(logger.handlers[0], logging.FileHandler)
            
            # 检查日志处理程序的文件路径
            assert logger.handlers[0].baseFilename == log_file

            # 检查日志处理程序的格式
            log_formatter = logger.handlers[0].formatter
            assert log_formatter._fmt == '%(asctime)s - PID: %(process)d - PWD: %(pathname)s - %(message)s'