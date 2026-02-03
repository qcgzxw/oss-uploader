"""测试异常处理改进"""
import pytest
import os
import json
from unittest.mock import patch, mock_open, MagicMock
from src.main import ConfigManager, HistoryManager


class TestConfigManagerExceptions:
    """测试 ConfigManager 的异常处理"""

    def test_config_manager_invalid_json(self):
        """测试配置文件损坏时的处理"""
        with patch('builtins.open', mock_open(read_data='invalid json')):
            with patch('os.path.exists', return_value=True):
                config = ConfigManager.load_config()
                assert config is not None
                assert 'access_key_id' in config
                assert 'access_key_secret' in config
                assert 'endpoint' in config

    def test_config_manager_file_not_found(self):
        """测试配置文件不存在时的处理"""
        with patch('os.path.exists', return_value=False):
            config = ConfigManager.load_config()
            assert config is not None
            assert 'access_key_id' in config
            assert config == ConfigManager.get_default_config()

    def test_config_manager_save_permission_error(self):
        """测试配置保存时的权限错误"""
        with patch('builtins.open', side_effect=PermissionError("No write permission")):
            with pytest.raises(PermissionError):
                ConfigManager.save_config({'test': 'value'})

    def test_config_manager_io_error(self):
        """测试配置文件读取时的 IO 错误"""
        with patch('builtins.open', side_effect=IOError("Disk error")):
            with patch('os.path.exists', return_value=True):
                config = ConfigManager.load_config()
                assert config is not None
                assert 'access_key_id' in config

    def test_config_manager_os_error(self):
        """测试配置文件读取时的 OS 错误"""
        with patch('builtins.open', side_effect=OSError("System error")):
            with patch('os.path.exists', return_value=True):
                config = ConfigManager.load_config()
                assert config is not None
                assert 'access_key_id' in config

    def test_config_manager_valid_json(self):
        """测试有效的 JSON 配置文件"""
        valid_config = {
            "access_key_id": "test_key",
            "access_key_secret": "test_secret",
            "endpoint": "oss-cn-hangzhou.aliyuncs.com",
            "bucket_name": "test-bucket"
        }
        with patch('builtins.open', mock_open(read_data=json.dumps(valid_config))):
            with patch('os.path.exists', return_value=True):
                config = ConfigManager.load_config()
                assert config['access_key_id'] == "test_key"
                assert config['access_key_secret'] == "test_secret"


class TestHistoryManagerExceptions:
    """测试 HistoryManager 的异常处理"""

    def test_history_manager_corrupted_file(self):
        """测试历史记录文件损坏时的处理"""
        with patch('builtins.open', mock_open(read_data='corrupted data')):
            with patch('os.path.exists', return_value=True):
                history = HistoryManager.load_history()
                assert history == []

    def test_history_manager_file_not_found(self):
        """测试历史记录文件不存在时的处理"""
        with patch('os.path.exists', return_value=False):
            history = HistoryManager.load_history()
            assert history == []

    def test_history_manager_io_error(self):
        """测试历史记录文件读取时的 IO 错误"""
        with patch('builtins.open', side_effect=IOError("Disk error")):
            with patch('os.path.exists', return_value=True):
                history = HistoryManager.load_history()
                assert history == []

    def test_history_manager_os_error(self):
        """测试历史记录文件读取时的 OS 错误"""
        with patch('builtins.open', side_effect=OSError("System error")):
            with patch('os.path.exists', return_value=True):
                history = HistoryManager.load_history()
                assert history == []

    def test_history_manager_valid_json(self):
        """测试有效的 JSON 历史记录文件"""
        valid_history = [
            {"date": "2024-01-01 12:00:00", "filename": "test.jpg", "url": "https://example.com/test.jpg"}
        ]
        with patch('builtins.open', mock_open(read_data=json.dumps(valid_history))):
            with patch('os.path.exists', return_value=True):
                history = HistoryManager.load_history()
                assert len(history) == 1
                assert history[0]['filename'] == "test.jpg"


class TestConfigManagerValidateClipboard:
    """测试 ConfigManager.validate_clipboard_data 的异常处理"""

    def test_validate_clipboard_invalid_json(self):
        """测试无效的 JSON 剪切板数据"""
        assert ConfigManager.validate_clipboard_data('invalid json') is None

    def test_validate_clipboard_missing_keys(self):
        """测试缺少必需键的剪切板数据"""
        incomplete_config = {
            "access_key_id": "test_key"
        }
        assert ConfigManager.validate_clipboard_data(json.dumps(incomplete_config)) is None

    def test_validate_clipboard_valid_data(self):
        """测试有效的剪切板配置数据"""
        valid_config = {
            "access_key_id": "test_key",
            "access_key_secret": "test_secret",
            "bucket_name": "test-bucket",
            "endpoint": "oss-cn-hangzhou.aliyuncs.com"
        }
        result = ConfigManager.validate_clipboard_data(json.dumps(valid_config))
        assert result is not None
        assert result['access_key_id'] == "test_key"
