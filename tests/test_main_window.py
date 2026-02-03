import pytest
import sys
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock, call
from PyQt5.QtWidgets import QApplication

# 确保 src 目录在 Python 路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.main import MainWindow, BatchUploadThread


@pytest.fixture
def main_window(qapp):
    """创建 MainWindow 实例"""
    window = MainWindow()
    yield window
    # 清理
    window.close()


def test_signal_connection_no_leak(main_window):
    """测试重复上传时不会累积信号连接"""
    # 创建模拟线程
    mock_thread = MagicMock(spec=BatchUploadThread)
    main_window.thread = mock_thread

    # 设置 mock 的信号
    mock_thread.progress_signal = MagicMock()
    mock_thread.success_signal = MagicMock()
    mock_thread.error_signal = MagicMock()
    mock_thread.all_finished_signal = MagicMock()

    # 模拟 disconnect 调用
    mock_thread.progress_signal.disconnect = MagicMock()
    mock_thread.success_signal.disconnect = MagicMock()
    mock_thread.error_signal.disconnect = MagicMock()
    mock_thread.all_finished_signal.disconnect = MagicMock()

    # 准备测试文件
    with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
        f.write(b'test content')
        test_file = f.name

    # Patch 配置
    mock_config = {
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

    with patch('src.main.ConfigManager') as mock_config_mgr:
        mock_config_mgr.load_config.return_value = mock_config
        with patch('src.main.BatchUploadThread', return_value=mock_thread):
            # 调用上传
            main_window.start_batch_upload([test_file])

    # 清理测试文件
    os.unlink(test_file)

    # 验证所有旧的信号连接都被断开了
    assert mock_thread.progress_signal.disconnect.called
    assert mock_thread.success_signal.disconnect.called
    assert mock_thread.error_signal.disconnect.called
    assert mock_thread.all_finished_signal.disconnect.called

    # 验证 disconnect 被调用时传入了正确的槽函数
    mock_thread.progress_signal.disconnect.assert_any_call(main_window.update_row_progress)
    mock_thread.success_signal.disconnect.assert_any_call(main_window.on_row_success)
    mock_thread.error_signal.disconnect.assert_any_call(main_window.on_row_error)
    mock_thread.all_finished_signal.disconnect.assert_any_call(main_window.on_all_finished)


def test_signal_connection_with_no_existing_thread(main_window):
    """测试第一次上传时（没有旧线程）也能正常工作"""
    # 确保 thread 为 None
    main_window.thread = None

    # 准备测试文件
    with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
        f.write(b'test content')
        test_file = f.name

    # Patch 配置
    mock_config = {
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

    with patch('src.main.ConfigManager') as mock_config_mgr:
        mock_config_mgr.load_config.return_value = mock_config
        with patch('src.main.BatchUploadThread') as mock_thread_class:
            mock_thread = MagicMock()
            mock_thread_class.return_value = mock_thread
            # 调用上传 - 应该不会抛出异常
            main_window.start_batch_upload([test_file])

    # 清理测试文件
    os.unlink(test_file)

    # 验证创建了新线程
    assert mock_thread_class.called
    # 验证新线程被启动
    assert mock_thread.start.called


def test_signal_connection_handles_disconnect_error(main_window):
    """测试当 disconnect 抛出 TypeError 时的错误处理"""
    # 创建模拟线程
    mock_thread = MagicMock(spec=BatchUploadThread)
    main_window.thread = mock_thread

    # 设置 mock 的信号
    mock_thread.progress_signal = MagicMock()
    mock_thread.success_signal = MagicMock()
    mock_thread.error_signal = MagicMock()
    mock_thread.all_finished_signal = MagicMock()

    # 模拟 disconnect 抛出 TypeError（信号未连接时会发生）
    mock_thread.progress_signal.disconnect = MagicMock(side_effect=TypeError("not connected"))
    mock_thread.success_signal.disconnect = MagicMock(side_effect=TypeError("not connected"))
    mock_thread.error_signal.disconnect = MagicMock(side_effect=TypeError("not connected"))
    mock_thread.all_finished_signal.disconnect = MagicMock(side_effect=TypeError("not connected"))

    # 准备测试文件
    with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
        f.write(b'test content')
        test_file = f.name

    # Patch 配置
    mock_config = {
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

    with patch('src.main.ConfigManager') as mock_config_mgr:
        mock_config_mgr.load_config.return_value = mock_config
        with patch('src.main.BatchUploadThread', return_value=mock_thread):
            # 调用上传 - 应该捕获 TypeError 并继续执行
            main_window.start_batch_upload([test_file])

    # 清理测试文件
    os.unlink(test_file)

    # 验证 disconnect 被调用（即使抛出了异常）
    assert mock_thread.progress_signal.disconnect.called
    # 验证新线程仍然被创建和启动
    assert mock_thread.start.called
