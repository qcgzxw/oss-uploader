import pytest
import sys
from PyQt5.QtWidgets import QApplication

@pytest.fixture(scope="session")
def qapp():
    """创建 QApplication 实例，整个测试会话共享"""
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
    return app
