# tests/config_test.py
import os
import tempfile
import pytest
from configparser import ConfigParser
from bincache.config import get_config, parse_size, DEFAULT_CACHE_DIR, CONFIG_FILE

from bincache import config as bincache_config

@pytest.fixture(autouse=True)
def reset_config():
    """在每个测试之前执行，用于重置config.py中的_config变量"""
    bincache_config._config = None

def test_parse_size():
    """测试 parse_size 函数，确保其能正确解析带有单位的字符串并转化为字节大小"""
    assert parse_size("10B") == 10
    assert parse_size("1K") == 1024
    assert parse_size("2M") == 2 * 1024**2
    assert parse_size("1G") == 1 * 1024**3


def test_get_config_defaults():
    """测试 get_config 函数的默认配置，确保在没有配置文件的情况下返回正确的默认值"""
    config = get_config()
    assert config['max_size'] == 5 * 1024 * 1024 * 1024  # 默认 5G
    assert config['log_file'] == ""
    assert config['log_level'] == "INFO"
    assert config['stats'] == False
    assert config['temporary_dir'] == os.path.join(DEFAULT_CACHE_DIR, "tmp")


def test_get_config_with_file():
    """测试 get_config 函数，确保在存在配置文件的情况下能正确读取配置"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = os.path.join(tmpdir, 'cache')
        os.makedirs(cache_dir)
        config_file = os.path.join(cache_dir, CONFIG_FILE)
        
        with open(config_file, 'w') as f:
            f.write("""
            max_size=10M
            log_file=test.log
            log_level=DEBUG
            stats=True
            temporary_dir=/tmp/test_tmp
            """)
        
        os.environ['BINCACHE_DIR'] = cache_dir
        
        config = get_config()
        
        assert config['max_size'] == 10 * 1024**2  # 10M
        assert config['log_file'] == os.path.join(cache_dir, 'test.log')
        assert config['log_level'] == "DEBUG"
        assert config['stats'] == True
        assert config['temporary_dir'] == "/tmp/test_tmp"

def test_get_config_with_invalid_data():
    """测试 get_config 函数，确保会忽略配置文件中的错误配置"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = os.path.join(tmpdir, 'cache')
        os.makedirs(cache_dir)
        config_file = os.path.join(cache_dir, CONFIG_FILE)
        
        with open(config_file, 'w') as f:
            f.write("""
            max_size
            log_file=test.log
            log_level
            stats=True
            temporary_dir=/tmp/test_tmp
            """)
        
        os.environ['BINCACHE_DIR'] = cache_dir
        
        config = get_config()
        
        assert config['max_size'] == 5 * 1024 * 1024 * 1024 # default
        assert config['log_file'] == os.path.join(cache_dir, 'test.log')
        assert config['log_level'] == "INFO" # default
        assert config['stats'] == True
        assert config['temporary_dir'] == "/tmp/test_tmp"

def test_get_config_with_relative_log_file():
    """测试 get_config 函数，确保在 log_file 配置为相对路径时能正确解析为绝对路径"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = os.path.join(tmpdir, 'cache')
        os.makedirs(cache_dir)
        config_file = os.path.join(cache_dir, CONFIG_FILE)
        
        with open(config_file, 'w') as f:
            f.write("""
            log_file=relative/test.log
            """)
        
        os.environ['BINCACHE_DIR'] = cache_dir
        
        config = get_config()
        
        assert config['log_file'] == os.path.join(cache_dir, 'relative', 'test.log')


def test_parse_non_standard_size():
    """测试 parse_size 函数，确保在输入非标准格式时能友好地处理"""
    
    # 没有单位时，直接返回其 int 值
    assert parse_size("1000") == 1000
