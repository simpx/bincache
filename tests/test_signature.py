import os
import tempfile
import hashlib
import pytest
import subprocess
from unittest import mock
from bincache.signature import hash_file_md5, get_dynamic_libs, generate_signature

def test_hash_file_md5():
    content = b"test content for hashing"
    expected_md5 = hashlib.md5(content).hexdigest()
    
    with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
        tmpfile.write(content)
        tmpfile_path = tmpfile.name
    
    try:
        calculated_md5 = hash_file_md5(tmpfile_path)
        assert calculated_md5 == expected_md5
    finally:
        os.remove(tmpfile_path)

def test_get_dynamic_libs():
    example_output = b"""
    linux-vdso.so.1 =>  (0x00007fff6ab93000)
	libstdc++.so.6 => /lib64/libstdc++.so.6 (0x00007fc5c64c6000)
	libm.so.6 => /lib64/libm.so.6 (0x00007fc5c61c4000)
	libgcc_s.so.1 => /lib64/libgcc_s.so.1 (0x00007fc5c5fad000)
	libc.so.6 => /lib64/libc.so.6 (0x00007fc5c5bdf000)
	/lib64/ld-linux-x86-64.so.2 (0x00007fc5c6853000)
    """
    with mock.patch('subprocess.Popen') as mock_popen:
        process_mock = mock.Mock()
        attrs = {'communicate.return_value': (example_output, b''), 'returncode': 0}
        process_mock.configure_mock(**attrs)
        mock_popen.return_value = process_mock
        
        libs = get_dynamic_libs('dummy_binary')

        expected_libs = [
            ('linux-vdso.so.1', '', '0x00007fff6ab93000'),
            ('libstdc++.so.6', '/lib64/libstdc++.so.6', '0x00007fc5c64c6000'),
            ('libm.so.6', '/lib64/libm.so.6', '0x00007fc5c61c4000'),
            ('libgcc_s.so.1', '/lib64/libgcc_s.so.1', '0x00007fc5c5fad000'),
            ('libc.so.6', '/lib64/libc.so.6', '0x00007fc5c5bdf000'),
            ('', '/lib64/ld-linux-x86-64.so.2', '0x00007fc5c6853000')
        ]
        
        assert libs == expected_libs
@mock.patch('bincache.signature.hash_file_md5', autospec=True)
@mock.patch('bincache.signature.get_dynamic_libs', autospec=True)
def test_generate_signature(mock_get_dynamic_libs, mock_hash_file_md5):
    # 定义根据文件路径返回不同的哈希值的逻辑
    def hash_side_effect(path):
        hash_dict = {
            'dummy_binary': 'hash_of_dummy_binary',
            '/lib64/libstdc++.so.6': 'hash_of_libstdc++',
            '/lib64/libm.so.6': 'hash_of_libm',
            '/lib64/libgcc_s.so.1': 'hash_of_libgcc_s',
            '/lib64/libc.so.6': 'hash_of_libc',
            '/lib64/ld-linux-x86-64.so.2': 'hash_of_ld-linux-x86-64.so.2'
        }
        return hash_dict.get(path, 'hash_of_unknown_lib')
    
    mock_hash_file_md5.side_effect = hash_side_effect
    
    # 模拟 get_dynamic_libs 返回的动态库信息
    mock_get_dynamic_libs.return_value = [
        ('linux-vdso.so.1', '', '0x00007fff6ab93000'),
        ('libstdc++.so.6', '/lib64/libstdc++.so.6', '0x00007fc5c64c6000'),
        ('libm.so.6', '/lib64/libm.so.6', '0x00007fc5c61c4000'),
        ('libgcc_s.so.1', '/lib64/libgcc_s.so.1', '0x00007fc5c5fad000'),
        ('libc.so.6', '/lib64/libc.so.6', '0x00007fc5c5bdf000'),
        ('', '/lib64/ld-linux-x86-64.so.2', '0x00007fc5c6853000')
    ]
    
    binary = 'dummy_binary'
    args = ['arg1', 'arg2']
    
    # 计算生成的签名应包含的哈希值和信息
    expected_binary_hash = 'hash_of_dummy_binary'
    expected_libs_info = [
        ('/lib64/libstdc++.so.6', 'hash_of_libstdc++'),
        ('/lib64/libm.so.6', 'hash_of_libm'),
        ('/lib64/libgcc_s.so.1', 'hash_of_libgcc_s'),
        ('/lib64/libc.so.6', 'hash_of_libc'),
        ('/lib64/ld-linux-x86-64.so.2', 'hash_of_ld-linux-x86-64.so.2')
    ]
    expected_signature_source = f"{expected_binary_hash}{expected_libs_info}arg1 arg2"
    expected_signature = hashlib.md5(expected_signature_source.encode('utf-8')).hexdigest()
    
    # 调用 generate_signature 函数生成签名
    signature = generate_signature(binary, args)
    
    # 验证生成的签名是否正确
    assert signature == expected_signature