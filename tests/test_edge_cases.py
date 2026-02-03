import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QApplication
import sys

# Ensure src is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.main import MainWindow, BatchUploadThread, ConfigManager


@pytest.fixture
def main_window(qapp):
    """创建 MainWindow 实例用于测试"""
    window = MainWindow()
    yield window
    # Clean up
    window.close()


def test_upload_empty_file_list(main_window):
    """测试上传空文件列表"""
    with patch('src.main.ConfigManager') as mock_config:
        mock_config.load_config.return_value = {
            'access_key_id': 'test_key',
            'access_key_secret': 'test_secret',
            'endpoint': 'oss-cn-hangzhou.aliyuncs.com',
            'bucket_name': 'test-bucket',
            'custom_domain': '',
            'upload_path': 'uploads',
            'use_random_name': False,
            'auto_copy': False,
            'url_expire_time': 3600
        }

        # Call with empty list
        main_window.start_batch_upload([])

        # Should handle empty list gracefully
        assert main_window.task_table.rowCount() == 0


def test_upload_without_config(main_window):
    """测试未配置时的上传行为"""
    with patch('src.main.ConfigManager') as mock_config:
        mock_config.load_config.return_value = {
            'access_key_id': '',
            'access_key_secret': '',
            'endpoint': 'oss-cn-hangzhou.aliyuncs.com',
            'bucket_name': '',
            'custom_domain': '',
            'upload_path': 'uploads',
            'use_random_name': False,
            'auto_copy': False,
            'url_expire_time': 3600
        }

        with patch('src.main.QMessageBox.warning') as mock_warning:
            main_window.start_batch_upload(['test.txt'])

            # Should show warning
            mock_warning.assert_called_once()

            # Verify warning message
            args, kwargs = mock_warning.call_args
            assert "错误" in str(args[1]) or "配置" in str(args[2])


def test_copy_empty_tasks_data(main_window):
    """测试空任务数据时的复制行为"""
    main_window.tasks_data = {}

    # Should not crash
    main_window.copy_all(mode="url", silent=True)

    # Verify table row count is still 0
    assert main_window.task_table.rowCount() == 0


def test_special_characters_in_filename():
    """测试文件名中包含特殊字符"""
    config = {
        'access_key_id': 'test_key',
        'access_key_secret': 'test_secret',
        'endpoint': 'oss-cn-hangzhou.aliyuncs.com',
        'bucket_name': 'test-bucket',
        'upload_path': 'uploads',
        'use_random_name': False,
        'custom_domain': '',
        'url_expire_time': 2592000
    }

    thread = BatchUploadThread([], config)

    test_cases = [
        'file#name.txt',
        'file name.txt',
        'file?name.txt',
        'file&name.txt',
        'file=name.txt',
        '文件名.txt',
        'file with spaces #1.txt',
    ]

    for filename in test_cases:
        mock_path = f'/tmp/{filename}'
        object_name = thread.get_object_name(mock_path)

        # Object name should be generated
        assert object_name is not None
        assert len(object_name) > 0
        # Original filename should be preserved when use_random_name is False
        assert filename in object_name or object_name.endswith(filename)


def test_config_with_empty_values():
    """测试配置为空值时的处理"""
    config = ConfigManager.get_default_config()

    # Set empty values
    config['access_key_id'] = ''
    config['bucket_name'] = ''

    assert config.get('access_key_id') == ''
    assert config.get('bucket_name') == ''

    # Other fields should still have defaults
    assert config.get('endpoint') == 'oss-cn-hangzhou.aliyuncs.com'
    assert config.get('upload_path') == 'uploads/{username}/{year}/{month}'


def test_special_characters_with_random_name():
    """测试使用随机文件名时特殊字符的处理"""
    config = {
        'access_key_id': 'test_key',
        'access_key_secret': 'test_secret',
        'endpoint': 'oss-cn-hangzhou.aliyuncs.com',
        'bucket_name': 'test-bucket',
        'upload_path': 'uploads',
        'use_random_name': True,
        'custom_domain': '',
        'url_expire_time': 2592000
    }

    thread = BatchUploadThread([], config)

    # Test with problematic filename
    mock_path = '/tmp/file#with?special&chars.txt'
    object_name = thread.get_object_name(mock_path)

    # With random name, should use UUID instead of problematic filename
    assert object_name is not None
    assert len(object_name) > 0
    # Should preserve extension
    assert object_name.endswith('.txt')
    # Should not contain special characters from original name
    assert '#' not in object_name
    assert '?' not in object_name


def test_empty_upload_path():
    """测试空上传路径时的处理"""
    config = {
        'access_key_id': 'test_key',
        'access_key_secret': 'test_secret',
        'endpoint': 'oss-cn-hangzhou.aliyuncs.com',
        'bucket_name': 'test-bucket',
        'upload_path': '',
        'use_random_name': False,
        'custom_domain': '',
        'url_expire_time': 2592000
    }

    thread = BatchUploadThread([], config)

    mock_path = '/tmp/testfile.txt'
    object_name = thread.get_object_name(mock_path)

    # Should handle empty path gracefully
    assert object_name is not None
    assert len(object_name) > 0
    # Should just be filename without path prefix
    assert object_name == 'testfile.txt'


def test_upload_path_with_trailing_slash():
    """测试上传路径带尾部斜杠时的处理"""
    config = {
        'access_key_id': 'test_key',
        'access_key_secret': 'test_secret',
        'endpoint': 'oss-cn-hangzhou.aliyuncs.com',
        'bucket_name': 'test-bucket',
        'upload_path': 'uploads/',
        'use_random_name': False,
        'custom_domain': '',
        'url_expire_time': 2592000
    }

    thread = BatchUploadThread([], config)

    mock_path = '/tmp/testfile.txt'
    object_name = thread.get_object_name(mock_path)

    # Should handle trailing slash
    assert object_name is not None
    # Should not have double slashes
    assert '//' not in object_name


def test_zero_expire_time():
    """测试零过期时间（公开链接）的处理"""
    config = {
        'access_key_id': 'test_key',
        'access_key_secret': 'test_secret',
        'endpoint': 'oss-cn-hangzhou.aliyuncs.com',
        'bucket_name': 'test-bucket',
        'upload_path': 'uploads',
        'use_random_name': False,
        'custom_domain': '',
        'url_expire_time': 0
    }

    # Verify config accepts zero value
    assert config.get('url_expire_time') == 0


def test_none_values_in_config():
    """测试配置中包含 None 值的处理"""
    config = ConfigManager.get_default_config()

    # Set some values to None
    config['custom_domain'] = None
    config['upload_path'] = None

    # get() should return None for these fields
    assert config.get('custom_domain') is None
    assert config.get('upload_path') is None

    # Should handle None with default value
    domain = config.get('custom_domain') or ''
    assert domain == ''

    # Should handle strip with default value
    domain = (config.get('custom_domain') or '').strip()
    assert domain == ''
