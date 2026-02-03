import pytest
import time
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock, call
from PyQt5.QtCore import QThread

from src.main import BatchUploadThread


def test_thread_stops_cleanly(qapp):
    """测试线程能够正确停止并清理资源"""
    # 创建临时测试文件
    test_files = []
    for i in range(3):
        fd, path = tempfile.mkstemp(suffix=f"_test{i}.txt")
        with os.fdopen(fd, 'w') as f:
            f.write(f"test content {i}")
        test_files.append(path)

    config = {
        'access_key_id': 'test_key',
        'access_key_secret': 'test_secret',
        'endpoint': 'oss-cn-hangzhou.aliyuncs.com',
        'bucket_name': 'test-bucket',
        'upload_path': 'uploads/{username}/{year}/{month}',
        'use_random_name': False,
        'custom_domain': '',
        'url_expire_time': 2592000
    }

    try:
        thread = BatchUploadThread(test_files, config)

        # Mock OSS bucket - 模拟上传需要一定时间
        mock_bucket = MagicMock()

        def slow_put_object(*args, **kwargs):
            # 模拟上传需要时间
            time.sleep(0.2)

        mock_bucket.put_object_from_file.side_effect = slow_put_object
        mock_bucket.sign_url.return_value = "https://example.com/test.txt"

        with patch('oss2.Bucket', return_value=mock_bucket):
            thread.start()
            time.sleep(0.1)  # 让线程启动并开始上传

            # 调用 stop 方法
            thread.stop()
            thread.wait(2000)  # 等待最多 2 秒

            # 验证线程已停止
            assert thread.isFinished() or not thread.isRunning()

    finally:
        # 清理测试文件
        for path in test_files:
            if os.path.exists(path):
                os.remove(path)


def test_thread_cleanup_on_error(qapp):
    """测试线程在上传错误时也能正确清理"""
    # 创建临时测试文件
    fd, path = tempfile.mkstemp(suffix="_test.txt")
    with os.fdopen(fd, 'w') as f:
        f.write("test content")

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

    try:
        test_files = [path]
        thread = BatchUploadThread(test_files, config)

        errors_received = []
        finished_received = []

        def capture_error(idx, msg):
            errors_received.append((idx, msg))

        def capture_finished():
            finished_received.append(True)

        thread.error_signal.connect(capture_error)
        thread.all_finished_signal.connect(capture_finished)

        # Mock OSS bucket - 在上传时抛出异常
        mock_bucket = MagicMock()
        mock_bucket.put_object_from_file.side_effect = Exception("Upload failed")

        with patch('src.main.oss2.Bucket', return_value=mock_bucket):
            thread.start()
            # 给 Qt 事件循环一些时间处理信号
            thread.wait(5000)
            qapp.processEvents()

        # 应该收到错误信号（上传失败）
        assert len(errors_received) > 0, f"Expected errors but got: {errors_received}"
        assert len(finished_received) > 0, "Expected finished signal"
        assert thread.isFinished(), "Thread should finish after error"

    finally:
        if os.path.exists(path):
            os.remove(path)


def test_stop_flag_behavior(qapp):
    """测试 stop 标志位能够正确中断循环"""
    # 创建测试文件
    fd, path = tempfile.mkstemp(suffix="_test.txt")
    with os.fdopen(fd, 'w') as f:
        f.write("test content")

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

    try:
        thread = BatchUploadThread([path], config)

        # Mock bucket
        mock_bucket = MagicMock()
        upload_count = [0]

        def counting_put_object(*args, **kwargs):
            upload_count[0] += 1
            time.sleep(0.1)

        mock_bucket.put_object_from_file.side_effect = counting_put_object
        mock_bucket.sign_url.return_value = "https://example.com/test.txt"

        with patch('oss2.Bucket', return_value=mock_bucket):
            # 先设置停止标志
            thread.stop()
            thread.start()
            thread.wait(2000)

            # 线程应该因为 is_running=False 而立即退出
            # 不应该调用上传函数
            assert upload_count[0] == 0
            assert thread.isFinished()

    finally:
        if os.path.exists(path):
            os.remove(path)


def test_stop_during_upload(qapp):
    """测试在上传过程中停止线程"""
    # 创建多个测试文件
    test_files = []
    for i in range(5):
        fd, path = tempfile.mkstemp(suffix=f"_test{i}.txt")
        with os.fdopen(fd, 'w') as f:
            f.write(f"test content {i}")
        test_files.append(path)

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

    try:
        thread = BatchUploadThread(test_files, config)

        # Mock bucket
        mock_bucket = MagicMock()
        uploaded_files = []

        def slow_put_object(object_name, file_path, **kwargs):
            uploaded_files.append(object_name)
            time.sleep(0.15)  # 每个上传需要时间

        mock_bucket.put_object_from_file.side_effect = slow_put_object
        mock_bucket.sign_url.return_value = "https://example.com/test.txt"

        with patch('oss2.Bucket', return_value=mock_bucket):
            thread.start()
            time.sleep(0.25)  # 让第一个文件开始上传

            # 在上传过程中停止
            thread.stop()
            thread.wait(2000)

            # 验证：不是所有文件都被上传了（因为被中断）
            assert len(uploaded_files) < len(test_files)
            assert thread.isFinished() or not thread.isRunning()

    finally:
        for path in test_files:
            if os.path.exists(path):
                os.remove(path)


def test_stop_sets_flag_correctly(qapp):
    """测试 stop 方法正确设置 is_running 标志"""
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

    # 初始状态应该是 True
    assert thread.is_running == True

    # 调用 stop
    thread.stop()

    # 标志应该被设置为 False
    assert thread.is_running == False
