import sys
import os
import json
import uuid
import oss2
import datetime
import getpass
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QLabel, QPushButton, QProgressBar, QDialog,
                             QLineEdit, QFormLayout, QMessageBox, QFileDialog,
                             QComboBox, QCheckBox, QTabWidget, QGroupBox, QHBoxLayout, QStyle)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

# --- 常量配置 ---
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".aliyun_oss_uploader_config.json")
VERSION = "1.1.0"

# 阿里云区域列表 (用于下拉框)
ALIYUN_ENDPOINTS = [
    ("华东1（杭州）", "oss-cn-hangzhou.aliyuncs.com"),
    ("华东2（上海）", "oss-cn-shanghai.aliyuncs.com"),
    ("华北1（青岛）", "oss-cn-qingdao.aliyuncs.com"),
    ("华北2（北京）", "oss-cn-beijing.aliyuncs.com"),
    ("华北3（张家口）", "oss-cn-zhangjiakou.aliyuncs.com"),
    ("华北5（呼和浩特）", "oss-cn-huhehaote.aliyuncs.com"),
    ("华南1（深圳）", "oss-cn-shenzhen.aliyuncs.com"),
    ("华南2（河源）", "oss-cn-heyuan.aliyuncs.com"),
    ("华南3（广州）", "oss-cn-guangzhou.aliyuncs.com"),
    ("西南1（成都）", "oss-cn-chengdu.aliyuncs.com"),
    ("中国（香港）", "oss-cn-hongkong.aliyuncs.com"),
    ("美国（硅谷）", "oss-us-west-1.aliyuncs.com"),
    ("美国（弗吉尼亚）", "oss-us-east-1.aliyuncs.com"),
    ("新加坡", "oss-ap-southeast-1.aliyuncs.com"),
]


class ConfigManager:
    @staticmethod
    def get_default_config():
        return {
            "access_key_id": "",
            "access_key_secret": "",
            "endpoint": "oss-cn-hangzhou.aliyuncs.com",
            "bucket_name": "",
            "custom_domain": "",
            # 新增配置
            "upload_path": "uploads/{username}/{year}/{month}",
            "use_random_name": False,
            "auto_copy": True
        }

    @staticmethod
    def load_config():
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置，防止旧版本配置文件缺少新字段报错
                    default = ConfigManager.get_default_config()
                    default.update(config)
                    return default
            except:
                return ConfigManager.get_default_config()
        return ConfigManager.get_default_config()

    @staticmethod
    def save_config(data):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def validate_clipboard_data(text):
        """尝试解析剪切板内容是否为配置Json"""
        try:
            data = json.loads(text)
            required_keys = ["access_key_id", "access_key_secret", "bucket_name"]
            if all(k in data for k in required_keys):
                return data
        except:
            pass
        return None


# --- 上传线程 ---
class UploadThread(QThread):
    progress_signal = pyqtSignal(int)
    success_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, file_path, config):
        super().__init__()
        self.file_path = file_path
        self.config = config

    def get_object_name(self):
        """根据配置生成云端存储路径"""
        filename = os.path.basename(self.file_path)
        ext = os.path.splitext(filename)[1]

        # 1. 处理文件名 (随机 or 原名)
        if self.config.get('use_random_name'):
            final_name = f"{uuid.uuid4().hex}{ext}"
        else:
            final_name = filename

        # 2. 处理目录路径
        path_pattern = self.config.get('upload_path', '')
        # 替换占位符
        now = datetime.datetime.now()
        username = getpass.getuser()

        # 简单替换逻辑
        folder = path_pattern.replace("{username}", username) \
            .replace("{year}", now.strftime("%Y")) \
            .replace("{month}", now.strftime("%m")) \
            .replace("{day}", now.strftime("%d")) \
            .replace("{YY}", now.strftime("%y")) \
            .replace("{MM}", now.strftime("%m"))

        # 去除首尾斜杠并组合
        folder = folder.strip('/')
        if folder:
            return f"{folder}/{final_name}"
        return final_name

    def run(self):
        try:
            auth = oss2.Auth(self.config['access_key_id'], self.config['access_key_secret'])
            endpoint = self.config['endpoint']
            if not endpoint.startswith('http'):
                endpoint = 'https://' + endpoint

            bucket = oss2.Bucket(auth, endpoint, self.config['bucket_name'])
            object_name = self.get_object_name()

            def percentage(consumed_bytes, total_bytes):
                if total_bytes:
                    rate = int(100 * (float(consumed_bytes) / float(total_bytes)))
                    self.progress_signal.emit(rate)

            # 执行上传
            bucket.put_object_from_file(object_name, self.file_path, progress_callback=percentage)

            # 生成链接
            domain = self.config.get('custom_domain', '').strip()
            if domain:
                if not domain.startswith('http'):
                    domain = 'https://' + domain
                if domain.endswith('/'):
                    domain = domain[:-1]
                url = f"{domain}/{object_name}"
            else:
                clean_endpoint = self.config['endpoint'].replace('http://', '').replace('https://', '')
                url = f"https://{self.config['bucket_name']}.{clean_endpoint}/{object_name}"

            self.success_signal.emit(url)

        except Exception as e:
            self.error_signal.emit(str(e))


# --- 设置对话框 (重构版) ---
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("阿里云 OSS 配置设置")
        self.resize(450, 400)

        self.config = ConfigManager.load_config()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 使用 Tab 页签分类
        tabs = QTabWidget()
        tabs.addTab(self.create_auth_tab(), "账号设置")
        tabs.addTab(self.create_pref_tab(), "上传偏好")
        layout.addWidget(tabs)

        # 底部按钮区
        btn_layout = QHBoxLayout()

        self.btn_check = QPushButton("连通性测试")
        self.btn_check.setIcon(self.style().standardIcon(QStyle.SP_DriveNetIcon))
        self.btn_check.clicked.connect(self.check_connection)

        self.btn_save = QPushButton("保存配置")
        self.btn_save.setDefault(True)  # 回车默认触发
        self.btn_save.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.btn_save.clicked.connect(self.save_and_close)

        btn_layout.addWidget(self.btn_check)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def create_auth_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)
        form.setSpacing(10)

        # AK
        self.input_ak = QLineEdit(self.config.get('access_key_id'))
        form.addRow("AccessKey ID <font color='red'>*</font>:", self.input_ak)

        # SK
        self.input_sk = QLineEdit(self.config.get('access_key_secret'))
        self.input_sk.setEchoMode(QLineEdit.Password)
        form.addRow("AccessKey Secret <font color='red'>*</font>:", self.input_sk)

        # Bucket
        self.input_bucket = QLineEdit(self.config.get('bucket_name'))
        form.addRow("Bucket Name <font color='red'>*</font>:", self.input_bucket)

        # Endpoint (下拉框)
        self.combo_endpoint = QComboBox()
        self.combo_endpoint.setEditable(True)  # 允许用户手动输入，兼容私有云或未列出的节点
        current_endpoint = self.config.get('endpoint', '')

        # 填充数据
        found = False
        for name, host in ALIYUN_ENDPOINTS:
            self.combo_endpoint.addItem(f"{name} ({host})", host)
            if host == current_endpoint:
                self.combo_endpoint.setCurrentIndex(self.combo_endpoint.count() - 1)
                found = True

        if not found and current_endpoint:
            self.combo_endpoint.addItem(current_endpoint, current_endpoint)
            self.combo_endpoint.setCurrentText(current_endpoint)

        form.addRow("Endpoint (地域) <font color='red'>*</font>:", self.combo_endpoint)

        # Domain
        self.input_domain = QLineEdit(self.config.get('custom_domain'))
        self.input_domain.setPlaceholderText("https://cdn.example.com")
        form.addRow("自定义域名 (选填):", self.input_domain)

        return widget

    def create_pref_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 路径设置
        group_path = QGroupBox("保存路径")
        form_path = QFormLayout(group_path)
        self.input_path = QLineEdit(self.config.get('upload_path'))
        self.input_path.setPlaceholderText("例如: uploads/{year}/{month}")
        label_hint = QLabel("支持占位符: {year}, {month}, {day}, {username}")
        label_hint.setStyleSheet("color: gray; font-size: 10px;")
        form_path.addRow("路径规则:", self.input_path)
        form_path.addRow("", label_hint)
        layout.addWidget(group_path)

        # 行为设置
        group_behavior = QGroupBox("行为选项")
        vbox = QVBoxLayout(group_behavior)

        self.check_random = QCheckBox("启用随机文件名 (使用UUID，防止同名覆盖)")
        self.check_random.setChecked(self.config.get('use_random_name', False))

        self.check_copy = QCheckBox("上传完成后自动复制链接")
        self.check_copy.setChecked(self.config.get('auto_copy', True))

        vbox.addWidget(self.check_random)
        vbox.addWidget(self.check_copy)
        layout.addWidget(group_behavior)

        layout.addStretch()
        return widget

    def get_current_endpoint(self):
        # 获取下拉框实际的 data (host)，如果是手输的则取 text
        host = self.combo_endpoint.currentData()
        if not host:
            # 如果是手输或编辑过的，data可能是None，需要解析
            text = self.combo_endpoint.currentText()
            # 简单的逻辑：如果包含括号，尝试取括号内的，否则取全部
            if "(" in text and ")" in text:
                import re
                match = re.search(r'\((.*?)\)', text)
                if match:
                    return match.group(1)
            return text
        return host

    def check_connection(self):
        ak = self.input_ak.text().strip()
        sk = self.input_sk.text().strip()
        bucket_name = self.input_bucket.text().strip()
        endpoint = self.get_current_endpoint()

        if not ak or not sk or not bucket_name or not endpoint:
            QMessageBox.warning(self, "参数缺失", "请先填写标红的必填项。")
            return

        self.btn_check.setText("测试中...")
        self.btn_check.setEnabled(False)
        QApplication.processEvents()  # 刷新界面

        try:
            auth = oss2.Auth(ak, sk)
            real_endpoint = endpoint if endpoint.startswith('http') else f'https://{endpoint}'
            bucket = oss2.Bucket(auth, real_endpoint, bucket_name)
            # 尝试获取Bucket信息来验证权限
            bucket.get_bucket_info()
            QMessageBox.information(self, "成功", "✅ 连接成功！参数配置正确。")
        except oss2.exceptions.ServerError as e:
            QMessageBox.critical(self, "失败", f"❌ 服务端错误: {e.status}\n可能Endpoint错误或Bucket不存在")
        except oss2.exceptions.AccessDenied as e:
            QMessageBox.critical(self, "失败", f"❌ 权限拒绝: AccessDenied\n请检查 AK/SK 是否正确")
        except Exception as e:
            QMessageBox.critical(self, "失败", f"❌ 连接失败:\n{str(e)}")
        finally:
            self.btn_check.setText("连通性测试")
            self.btn_check.setEnabled(True)

    def save_and_close(self):
        data = {
            "access_key_id": self.input_ak.text().strip(),
            "access_key_secret": self.input_sk.text().strip(),
            "bucket_name": self.input_bucket.text().strip(),
            "endpoint": self.get_current_endpoint(),
            "custom_domain": self.input_domain.text().strip(),
            "upload_path": self.input_path.text().strip(),
            "use_random_name": self.check_random.isChecked(),
            "auto_copy": self.check_copy.isChecked()
        }
        ConfigManager.save_config(data)
        self.accept()


# --- 主界面 ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("阿里云 OSS 上传工具")
        self.resize(500, 380)
        self.setAcceptDrops(True)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 顶部栏
        top_layout = QHBoxLayout()
        self.lbl_status = QLabel("就绪")
        self.lbl_status.setStyleSheet("color: gray;")
        self.btn_settings = QPushButton("⚙️ 设置")
        self.btn_settings.setFixedSize(80, 30)
        self.btn_settings.clicked.connect(self.open_settings)
        top_layout.addWidget(self.lbl_status)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_settings)
        layout.addLayout(top_layout)

        # 拖拽区域
        self.drop_area = QLabel("\n点击或拖拽文件至此\n")
        self.drop_area.setAlignment(Qt.AlignCenter)
        self.drop_area.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 10px;
                background-color: #f9f9f9;
                color: #555;
                font-size: 16px;
            }
            QLabel:hover {
                border-color: #4CAF50;
                background-color: #e8f5e9;
            }
        """)
        self.drop_area.setFixedHeight(150)
        self.drop_area.mousePressEvent = self.open_file_dialog
        layout.addWidget(self.drop_area)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # 结果框
        self.result_input = QLineEdit()
        self.result_input.setPlaceholderText("上传成功后链接显示于此")
        self.result_input.setReadOnly(True)
        layout.addWidget(self.result_input)

        # 复制按钮
        self.btn_copy = QPushButton("复制链接")
        self.btn_copy.setEnabled(False)
        self.btn_copy.clicked.connect(self.manual_copy)
        layout.addWidget(self.btn_copy)

        # 初始化检查
        QTimer.singleShot(100, self.startup_checks)

    def startup_checks(self):
        # 1. 检查配置是否存在
        config = ConfigManager.load_config()
        if not config.get('access_key_id'):
            # 2. 检查剪切板是否有配置
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            imported_data = ConfigManager.validate_clipboard_data(text)

            if imported_data:
                reply = QMessageBox.question(self, "检测到配置",
                                             "剪切板中似乎包含 OSS 配置信息，是否自动导入？",
                                             QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    # 合并默认配置以防缺失字段
                    full_config = ConfigManager.get_default_config()
                    full_config.update(imported_data)
                    ConfigManager.save_config(full_config)
                    QMessageBox.information(self, "成功", "配置已导入！")
                    return

            self.open_settings()

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec_()
        # 设置关闭后，刷新一下当前状态文案等（可选）

    def open_file_dialog(self, event):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件")
        if file_path:
            self.start_upload(file_path)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if os.path.isfile(file_path):
                self.start_upload(file_path)

    def start_upload(self, file_path):
        config = ConfigManager.load_config()
        if not config.get('access_key_id'):
            QMessageBox.warning(self, "错误", "请先配置 OSS 参数")
            return

        # UI 重置
        self.drop_area.setText(f"正在上传:\n{os.path.basename(file_path)}")
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.btn_copy.setEnabled(False)
        self.btn_copy.setText("复制链接")  # 修复：每次上传前重置文案
        self.result_input.clear()
        self.drop_area.setEnabled(False)
        self.lbl_status.setText("🚀 上传中...")

        self.thread = UploadThread(file_path, config)
        self.thread.progress_signal.connect(self.progress_bar.setValue)
        self.thread.success_signal.connect(self.upload_finished)
        self.thread.error_signal.connect(self.upload_error)
        self.thread.start()

    def upload_finished(self, url):
        self.progress_bar.hide()
        self.drop_area.setEnabled(True)
        self.drop_area.setText("\n点击或拖拽文件至此\n")
        self.result_input.setText(url)
        self.btn_copy.setEnabled(True)
        self.lbl_status.setText("✅ 上传完成")

        # 自动复制逻辑
        config = ConfigManager.load_config()
        if config.get('auto_copy', True):
            self.manual_copy(auto=True)

    def upload_error(self, msg):
        self.progress_bar.hide()
        self.drop_area.setEnabled(True)
        self.drop_area.setText("上传失败")
        self.lbl_status.setText("❌ 上传失败")
        QMessageBox.critical(self, "错误", msg)

    def manual_copy(self, auto=False):
        QApplication.clipboard().setText(self.result_input.text())
        self.btn_copy.setText("已复制！")
        if auto:
            # 自动复制时，给个明显的反馈
            self.lbl_status.setText("✅ 已自动复制链接")



if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Microsoft YaHei" if sys.platform == "win32" else "Arial", 10)
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
