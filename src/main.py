import sys
import os
import json
import uuid

import oss2
import datetime
import getpass
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QLabel, QPushButton, QDialog, QLineEdit, QFormLayout,
                             QMessageBox, QFileDialog, QComboBox, QCheckBox,
                             QTabWidget, QGroupBox, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QProgressBar, QMenu, QAction, QStyle, QSpinBox, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl
from PyQt5.QtGui import QFont, QIcon, QDesktopServices, QCursor, QColor

# --- 常量配置 ---
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".aliyun_oss_uploader_config.json")
HISTORY_FILE = os.path.join(os.path.expanduser("~"), ".aliyun_oss_history.json")
VERSION = "1.5.0"

STYLESHEET = """
/* === 全局基础设置 === */
QWidget {
    font-family: "Microsoft YaHei UI", "Segoe UI", Roboto, sans-serif;
    font-size: 14px;
    color: #333333;
    outline: none;
}
QMainWindow, QDialog { background-color: #F5F7FA; }

/* === 卡片容器 (去除无效 box-shadow) === */
QFrame#CardFrame {
    background-color: #FFFFFF;
    border-radius: 12px;
    border: 1px solid #E6E9ED;
}

/* === 标题与状态 === */
QLabel#TitleLabel { font-size: 20px; font-weight: bold; color: #2C3E50; }
QLabel#StatusLabel { color: #7F8C8D; font-size: 13px; }

/* === 按钮通用样式 === */
QPushButton {
    background-color: #FFFFFF;
    border: 1px solid #DCDFE6;
    border-radius: 6px;
    padding: 8px 16px;
    color: #606266;
}
QPushButton:hover { background-color: #ECF5FF; color: #409EFF; border-color: #C6E2FF; }
QPushButton:pressed { background-color: #D9ECFF; border-color: #3A8EE6; }
QPushButton:disabled { background-color: #F2F6FC; border-color: #EBEEF5; color: #C0C4CC; }

/* === 主按钮 (蓝色) === */
QPushButton#PrimaryButton { background-color: #409EFF; border: 1px solid #409EFF; color: #FFFFFF; }
QPushButton#PrimaryButton:hover { background-color: #66B1FF; border-color: #66B1FF; }
QPushButton#PrimaryButton:pressed { background-color: #3A8EE6; border-color: #3A8EE6; }

/* === 危险按钮 (红色) === */
QPushButton#DangerButton:hover { color: #F56C6C; background-color: #FEF0F0; border-color: #FBC4C4; }

/* === 批量复制按钮 (带下拉箭头) 的特殊修复 === */
QPushButton#DropdownButton {
    background-color: #409EFF; border: 1px solid #409EFF; color: #FFFFFF;
    text-align: center;
}
QPushButton#DropdownButton::menu-indicator {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    right: 10px;
    width: 10px;
    image: none;
}
QPushButton#DropdownButton:hover { background-color: #66B1FF; }

/* === 下拉菜单美化 (QMenu) === */
QMenu {
    background-color: #FFFFFF;
    border: 1px solid #EBEEF5;
    border-radius: 4px;
    padding: 5px 0;
}
QMenu::item {
    padding: 8px 30px 8px 20px; /* 上下8，右30，左20 */
    background-color: transparent;
    color: #606266;
}
QMenu::item:selected {
    background-color: #ECF5FF;
    color: #409EFF;
}

/* === 输入框与下拉框 === */
QLineEdit, QComboBox {
    border: 1px solid #DCDFE6; border-radius: 4px; padding: 6px; background: #FFFFFF;
}
QLineEdit:focus, QComboBox:focus { border-color: #409EFF; }

/* === 数字输入框 === */
QSpinBox {
    border: 1px solid #DCDFE6;
    border-radius: 4px;
    padding: 6px;
    background: #FFFFFF;
    selection-background-color: #409EFF;
}
/* === 表格内的按钮 (历史记录/操作列) === */
QTableWidget QPushButton {
    background-color: #FFFFFF;
    border: 1px solid #DCDFE6;
    color: #606266;
    padding: 4px 8px; /* 减小内边距 */
    font-size: 12px;  /* 减小字号 */
    border-radius: 4px;
    min-height: 20px;
}
QTableWidget QPushButton:hover {
    border-color: #409EFF;
    color: #409EFF;
}

/* === 拖拽区 === */
QLabel#DropArea {
    border: 2px dashed #DCDFE6; border-radius: 12px; background-color: #FFFFFF;
    color: #909399; font-size: 16px; font-weight: bold;
}
QLabel#DropArea:hover { border-color: #409EFF; background-color: #F2F6FC; color: #409EFF; }

/* === 弹窗 === */
QMessageBox {
    background-color: #F5F7FA;
}
QMessageBox QLabel {
    color: #333333;
    padding: 15px; /* 增加文字周围间距 */
    font-size: 14px;
}
QMessageBox QPushButton {
    width: 80px; /* 统一按钮宽度 */
}
"""

# 资源路径
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# 阿里云区域
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


# --- 历史记录 ---
class HistoryManager:
    @staticmethod
    def load_history():
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    @staticmethod
    def add_record(filename, url):
        records = HistoryManager.load_history()
        new_record = {
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "filename": filename,
            "url": url
        }
        records.insert(0, new_record)
        if len(records) > 500: records = records[:500]
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=4, ensure_ascii=False)


# --- 配置管理 ---
class ConfigManager:
    @staticmethod
    def get_default_config():
        return {
            "access_key_id": "",
            "access_key_secret": "",
            "endpoint": "oss-cn-hangzhou.aliyuncs.com",
            "bucket_name": "",
            "custom_domain": "",
            "upload_path": "uploads/{username}/{year}/{month}",
            "use_random_name": False,
            "auto_copy": True,
            "url_expire_time": 2592000
        }

    @staticmethod
    def load_config():
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
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
        try:
            data = json.loads(text)
            required_keys = ["access_key_id", "access_key_secret", "bucket_name"]
            if all(k in data for k in required_keys):
                return data
        except:
            pass
        return None


# --- 批量上传线程 ---
class BatchUploadThread(QThread):
    # index: 列表中的索引
    progress_signal = pyqtSignal(int, int)  # index, percent
    success_signal = pyqtSignal(int, str, str)  # index, filename, url
    error_signal = pyqtSignal(int, str)  # index, error_msg
    all_finished_signal = pyqtSignal()

    def __init__(self, file_paths, config):
        super().__init__()
        self.file_paths = file_paths
        self.config = config
        self.is_running = True

    def get_object_name(self, original_path):
        filename = os.path.basename(original_path)
        ext = os.path.splitext(filename)[1]

        if self.config.get('use_random_name'):
            final_name = f"{uuid.uuid4().hex}{ext}"
        else:
            final_name = filename

        path_pattern = self.config.get('upload_path', '')
        now = datetime.datetime.now()
        username = getpass.getuser()

        folder = path_pattern.replace("{username}", username) \
            .replace("{year}", now.strftime("%Y")) \
            .replace("{month}", now.strftime("%m")) \
            .replace("{day}", now.strftime("%d"))
        folder = folder.strip('/')
        if folder: return f"{folder}/{final_name}"
        return final_name

    def run(self):
        try:
            auth = oss2.Auth(self.config['access_key_id'], self.config['access_key_secret'])
            endpoint = self.config['endpoint']
            if not endpoint.startswith('http'): endpoint = 'https://' + endpoint
            bucket = oss2.Bucket(auth, endpoint, self.config['bucket_name'])
        except Exception as e:
            # 如果初始化失败，所有文件都报错
            for i in range(len(self.file_paths)):
                self.error_signal.emit(i, f"初始化失败: {str(e)}")
            self.all_finished_signal.emit()
            return
        expire_time = int(self.config.get('url_expire_time', 2592000))
        domain = self.config.get('custom_domain', '').strip()
        if domain:
            if not domain.startswith('http'): domain = 'https://' + domain
            if domain.endswith('/'): domain = domain[:-1]
        else:
            # 如果没有自定义域名，使用默认 Endpoint
            clean_endpoint = self.config['endpoint'].replace('http://', '').replace('https://', '')
            domain = f"https://{self.config['bucket_name']}.{clean_endpoint}"

        for idx, file_path in enumerate(self.file_paths):
            if not self.is_running: break

            file_name = os.path.basename(file_path)
            try:
                object_name = self.get_object_name(file_path)

                def percentage(consumed_bytes, total_bytes):
                    if total_bytes:
                        rate = int(100 * (float(consumed_bytes) / float(total_bytes)))
                        self.progress_signal.emit(idx, rate)

                bucket.put_object_from_file(object_name, file_path, progress_callback=percentage)

                # 生成链接
                if expire_time > 0:
                    # == 私有模式：生成签名链接 ==
                    signed_url = bucket.sign_url('GET', object_name, expire_time, slash_safe=True)

                    # 如果配置了自定义域名，我们需要替换掉官方签名的 Host 部分
                    if self.config.get('custom_domain', '').strip():
                        if '?' in signed_url:
                            query_params = signed_url.split('?')[1]
                            url = f"{domain}/{object_name}?{query_params}"
                        else:
                            url = signed_url
                    else:
                        url = signed_url
                else:
                    # == 公开模式：直接拼接 ==
                    url = f"{domain}/{object_name}"
                HistoryManager.add_record(file_name, url)
                self.success_signal.emit(idx, file_name, url)

            except Exception as e:
                self.error_signal.emit(idx, str(e))

        self.all_finished_signal.emit()

    def stop(self):
        self.is_running = False


# --- 历史记录窗口 ---
class HistoryWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("上传历史记录")
        self.resize(800, 600)
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["时间", "文件名", "链接 (双击打开)", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(3, 80)
        # 美化表格
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)

        layout.addWidget(self.table)

        btn_close = QPushButton("关闭")
        btn_close.setFixedSize(100, 36)
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)

    def load_data(self):
        records = HistoryManager.load_history()
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            self.table.setItem(row, 0, QTableWidgetItem(record.get('date', '')))
            self.table.setItem(row, 1, QTableWidgetItem(record.get('filename', '')))
            url_item = QTableWidgetItem(record.get('url', ''))
            url_item.setForeground(QColor("#409EFF"))
            url_item.setData(Qt.UserRole, record.get('url', ''))
            self.table.setItem(row, 2, url_item)

            btn_copy = QPushButton("复制")
            btn_copy.setCursor(Qt.PointingHandCursor)
            btn_copy.clicked.connect(lambda _, u=record.get('url', ''): self.copy_link(u))

            container = QWidget()
            l = QHBoxLayout(container)
            l.setContentsMargins(4, 4, 4, 4)
            l.setAlignment(Qt.AlignCenter)  # 居中对齐
            l.addWidget(btn_copy)
            self.table.setCellWidget(row, 3, container)

    def on_cell_double_clicked(self, row, col):
        if col == 2:
            url = self.table.item(row, col).data(Qt.UserRole)
            if url: QDesktopServices.openUrl(QUrl(url))

    def copy_link(self, url):
        QApplication.clipboard().setText(url)
        QMessageBox.information(self, "复制成功", "链接已复制到剪切板")

# --- 设置对话框 ---
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OSS 配置")
        self.resize(450, 420)
        self.config = ConfigManager.load_config()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        tabs = QTabWidget()
        tabs.addTab(self.create_auth_tab(), "账号设置")
        tabs.addTab(self.create_pref_tab(), "上传偏好")
        layout.addWidget(tabs)

        btn_layout = QHBoxLayout()
        self.btn_check = QPushButton("连通性测试")
        self.btn_check.setMinimumWidth(120)
        self.btn_check.setIcon(self.style().standardIcon(QStyle.SP_DriveNetIcon))
        self.btn_check.clicked.connect(self.check_connection)

        self.btn_save = QPushButton("保存配置")
        self.btn_save.setObjectName("PrimaryButton")  # 蓝色高亮
        self.btn_save.setMinimumWidth(120)
        self.btn_save.setDefault(True)
        self.btn_save.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.btn_save.clicked.connect(self.save_and_close)

        btn_layout.addWidget(self.btn_check)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def create_auth_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)
        form.setSpacing(15)
        form.setContentsMargins(20, 30, 20, 20)

        self.btn_import = QPushButton(" 从剪切板导入配置")
        self.btn_import.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.btn_import.clicked.connect(self.import_from_clipboard)
        form.addRow(self.btn_import)

        self.input_ak = QLineEdit(self.config.get('access_key_id'))
        form.addRow("AccessKey ID *:", self.input_ak)
        self.input_sk = QLineEdit(self.config.get('access_key_secret'))
        self.input_sk.setEchoMode(QLineEdit.Password)
        form.addRow("AccessKey Secret *:", self.input_sk)
        self.input_bucket = QLineEdit(self.config.get('bucket_name'))
        form.addRow("Bucket Name *:", self.input_bucket)

        self.combo_endpoint = QComboBox()
        self.combo_endpoint.setEditable(True)
        for name, host in ALIYUN_ENDPOINTS: self.combo_endpoint.addItem(f"{name} ({host})", host)
        curr = self.config.get('endpoint', '')
        if curr:
            clean_host = curr.replace("http://", "").replace("https://", "").strip("/")
            index = self.combo_endpoint.findData(clean_host)
            if index >= 0:
                self.combo_endpoint.setCurrentIndex(index)
            else:
                self.combo_endpoint.setCurrentText(curr)
        form.addRow("Endpoint *:", self.combo_endpoint)

        self.input_domain = QLineEdit(self.config.get('custom_domain'))
        self.input_domain.setPlaceholderText("可选，如 https://cdn.example.com")
        form.addRow("自定义域名:", self.input_domain)
        return widget

    def create_pref_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 30, 20, 20)
        layout.setSpacing(20)

        group_path = QGroupBox("路径设置")
        form_path = QFormLayout(group_path)
        self.input_path = QLineEdit(self.config.get('upload_path'))
        form_path.addRow("保存规则:", self.input_path)
        layout.addWidget(group_path)

        group_behavior = QGroupBox("高级选项")
        vbox = QVBoxLayout(group_behavior)
        vbox.setSpacing(15)

        time_layout = QHBoxLayout()
        self.spin_expire = QSpinBox()
        self.spin_expire.setRange(0, 315360000)  # 0 到 10年
        self.spin_expire.setValue(int(self.config.get('url_expire_time', 2592000)))
        self.spin_expire.setFixedWidth(120)

        lbl_hint = QLabel("(0 = 不过期/公开链接)")
        lbl_hint.setStyleSheet("color: gray;")

        time_layout.addWidget(QLabel("链接有效期:"))
        time_layout.addWidget(self.spin_expire)
        time_layout.addWidget(QLabel("秒"))
        time_layout.addWidget(lbl_hint)
        time_layout.addStretch()

        vbox.addLayout(time_layout)
        self.check_random = QCheckBox("启用随机文件名 (UUID)")
        self.check_random.setChecked(self.config.get('use_random_name', False))
        self.check_copy = QCheckBox("自动复制第一个文件的链接")
        self.check_copy.setChecked(self.config.get('auto_copy', True))

        vbox.addWidget(self.check_random)
        vbox.addWidget(self.check_copy)
        layout.addWidget(group_behavior)
        layout.addStretch()
        return widget

    def import_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()

        # 复用 ConfigManager 的校验逻辑
        data = ConfigManager.validate_clipboard_data(text)

        if data:
            # 填充数据到输入框
            self.input_ak.setText(data.get('access_key_id', ''))
            self.input_sk.setText(data.get('access_key_secret', ''))
            self.input_bucket.setText(data.get('bucket_name', ''))

            # 智能处理 Endpoint
            ep = data.get('endpoint', '')
            if ep:
                index = self.combo_endpoint.findData(ep)
                if index >= 0:
                    self.combo_endpoint.setCurrentIndex(index)
                else:
                    self.combo_endpoint.setCurrentText(ep)

            # 反馈提示
            QMessageBox.information(self, "导入成功", "✅ 配置已填充，请检查无误后点击保存。")
        else:
            QMessageBox.warning(self, "导入失败", "❌ 剪切板内容无效。\n请确保剪切板中包含正确的 JSON 配置格式。")

    def get_endpoint(self):
        host = self.combo_endpoint.currentData()
        if not host:
            text = self.combo_endpoint.currentText()
            import re
            match = re.search(r'\((.*?)\)', text)
            if match: return match.group(1)
            return text
        return host

    def check_connection(self):
        try:
            auth = oss2.Auth(self.input_ak.text().strip(), self.input_sk.text().strip())
            ep = self.get_endpoint()
            ep = ep if ep.startswith('http') else f'https://{ep}'
            bucket = oss2.Bucket(auth, ep, self.input_bucket.text().strip())
            bucket.get_bucket_info()
            QMessageBox.information(self, "成功", "连接成功！")
        except Exception as e:
            QMessageBox.critical(self, "失败", str(e))

    def save_and_close(self):
        data = {
            "access_key_id": self.input_ak.text().strip(),
            "access_key_secret": self.input_sk.text().strip(),
            "bucket_name": self.input_bucket.text().strip(),
            "endpoint": self.get_endpoint(),
            "custom_domain": self.input_domain.text().strip(),
            "upload_path": self.input_path.text().strip(),
            "use_random_name": self.check_random.isChecked(),
            "auto_copy": self.check_copy.isChecked(),
            "url_expire_time": self.spin_expire.value()
        }
        ConfigManager.save_config(data)
        self.accept()


# --- 主界面 ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"阿里云 OSS 上传工具 v{VERSION}")
        self.resize(900, 650)

        icon_path = resource_path(os.path.join('assets', 'icon.ico'))
        if os.path.exists(icon_path): self.setWindowIcon(QIcon(icon_path))

        self.setAcceptDrops(True)
        self.setup_ui()

        QTimer.singleShot(100, self.startup_checks)
        self.tasks_data = {}

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        # 主布局
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # 1. Header (标题 + 顶部按钮)
        header_layout = QHBoxLayout()

        title_box = QVBoxLayout()
        self.lbl_title = QLabel("OSS Uploader")
        self.lbl_title.setObjectName("TitleLabel")
        self.lbl_status = QLabel("Ready to upload")
        self.lbl_status.setObjectName("StatusLabel")
        title_box.addWidget(self.lbl_title)
        title_box.addWidget(self.lbl_status)

        header_layout.addLayout(title_box)
        header_layout.addStretch()

        self.btn_history = QPushButton(" 历史记录")
        self.btn_history.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.btn_history.setMinimumHeight(38)
        self.btn_history.clicked.connect(self.open_history)

        self.btn_settings = QPushButton(" 设置")
        self.btn_settings.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        self.btn_settings.setMinimumHeight(38)
        self.btn_settings.clicked.connect(self.open_settings)

        header_layout.addWidget(self.btn_history)
        header_layout.addWidget(self.btn_settings)
        main_layout.addLayout(header_layout)

        # 2. Content Card (白色卡片)
        card = QFrame()
        card.setObjectName("CardFrame")  # 关键：应用卡片样式
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(25, 25, 25, 25)
        card_layout.setSpacing(20)

        # 拖拽区
        self.drop_area = QLabel("\n点击选择文件 或 拖拽至此\n(支持批量上传)")
        self.drop_area.setObjectName("DropArea")
        self.drop_area.setAlignment(Qt.AlignCenter)
        self.drop_area.setFixedHeight(120)
        self.drop_area.setCursor(Qt.PointingHandCursor)
        self.drop_area.mousePressEvent = self.open_file_dialog
        card_layout.addWidget(self.drop_area)

        # 表格
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(4)
        self.task_table.setHorizontalHeaderLabels(["文件名", "进度", "链接", "操作"])
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.task_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.task_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.task_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.task_table.setColumnWidth(0, 240)
        self.task_table.setColumnWidth(1, 140)
        self.task_table.setColumnWidth(3, 100)

        # 表格美化
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.setShowGrid(False)
        self.task_table.setAlternatingRowColors(False)
        self.task_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.task_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        card_layout.addWidget(self.task_table)

        # 3. Action Bar (底部按钮)
        action_layout = QHBoxLayout()

        self.btn_copy_menu = QPushButton("批量复制")
        self.btn_copy_menu.setObjectName("DropdownButton")
        self.btn_copy_menu.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton))
        self.btn_copy_menu.setMinimumHeight(38)
        self.btn_copy_menu.setCursor(Qt.PointingHandCursor)

        menu = QMenu(self)
        action_urls = QAction("复制所有链接 (URL)", self)
        action_markdown = QAction("复制 Markdown 格式", self)
        menu.addAction(action_urls)
        menu.addAction(action_markdown)
        action_urls.triggered.connect(lambda: self.copy_all(mode="url"))
        action_markdown.triggered.connect(lambda: self.copy_all(mode="markdown"))
        self.btn_copy_menu.setMenu(menu)

        self.btn_clear = QPushButton(" 清空列表")
        self.btn_clear.setObjectName("DangerButton")
        self.btn_clear.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        self.btn_clear.setMinimumHeight(38)
        self.btn_clear.clicked.connect(self.clear_table)

        action_layout.addWidget(self.btn_copy_menu)
        action_layout.addStretch()
        action_layout.addWidget(self.btn_clear)

        card_layout.addLayout(action_layout)
        main_layout.addWidget(card)

    def startup_checks(self):
        # 1. 检查本地配置是否存在
        config = ConfigManager.load_config()

        # 只有在没有配置（AK为空）的情况下才检测剪切板
        if not config.get('access_key_id'):
            # 2. 读取剪切板
            clipboard = QApplication.clipboard()
            text = clipboard.text()

            # 3. 验证剪切板内容是否为有效配置
            imported_data = ConfigManager.validate_clipboard_data(text)

            if imported_data:
                # 4. 询问用户是否导入
                reply = QMessageBox.question(self, "检测到配置",
                                             "剪切板中似乎包含 OSS 配置信息，是否自动导入？",
                                             QMessageBox.Yes | QMessageBox.No)

                if reply == QMessageBox.Yes:
                    # 合并默认配置，防止缺失字段
                    full_config = ConfigManager.get_default_config()
                    full_config.update(imported_data)
                    ConfigManager.save_config(full_config)
                    QMessageBox.information(self, "成功", "配置已导入！")
                    return  # 导入成功后不再弹出设置窗口

            # 5. 如果没有导入，则打开设置窗口让用户手动填写
            self.open_settings()

    def open_settings(self):
        SettingsDialog(self).exec_()

    def open_history(self):
        HistoryWindow(self).exec_()

    def open_file_dialog(self, event):
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件")
        if files: self.start_batch_upload(files)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e):
        files = [u.toLocalFile() for u in e.mimeData().urls() if os.path.isfile(u.toLocalFile())]
        if files: self.start_batch_upload(files)

    def start_batch_upload(self, file_paths):
        config = ConfigManager.load_config()
        if not config.get('access_key_id'): return QMessageBox.warning(self, "错误", "请先配置")

        self.drop_area.setEnabled(False)
        self.tasks_data = {}  # 重置数据
        self.task_table.setRowCount(0)  # 清空旧表
        self.task_table.setRowCount(len(file_paths))

        # 初始化表格行
        for i, path in enumerate(file_paths):
            fname = os.path.basename(path)
            # 1. 文件名
            self.task_table.setItem(i, 0, QTableWidgetItem(fname))
            # 2. 进度条 (初始)
            pbar = QProgressBar()
            pbar.setRange(0, 100)
            pbar.setValue(0)
            pbar.setTextVisible(False)
            pbar.setStyleSheet(
                "QProgressBar { border: 0px; background-color: #eee; border-radius: 4px; } QProgressBar::chunk { background-color: #4CAF50; border-radius: 4px; }")
            container = QWidget()
            pl = QVBoxLayout(container)
            pl.setContentsMargins(5, 5, 5, 5)
            pl.addWidget(pbar)
            self.task_table.setCellWidget(i, 1, container)
            # 3. 链接 (空)
            self.task_table.setItem(i, 2, QTableWidgetItem("等待中..."))
            # 4. 操作 (禁用)
            btn = QPushButton("复制")
            btn.setEnabled(False)
            container_btn = QWidget()
            bl = QVBoxLayout(container_btn)
            bl.setContentsMargins(2, 2, 2, 2)
            bl.addWidget(btn)
            self.task_table.setCellWidget(i, 3, container_btn)

        self.lbl_status.setText(f"正在上传 {len(file_paths)} 个文件...")

        self.thread = BatchUploadThread(file_paths, config)
        self.thread.progress_signal.connect(self.update_row_progress)
        self.thread.success_signal.connect(self.on_row_success)
        self.thread.error_signal.connect(self.on_row_error)
        self.thread.all_finished_signal.connect(self.on_all_finished)
        self.thread.start()

    def update_row_progress(self, idx, percent):
        # 获取 CellWidget 里的 ProgressBar
        widget = self.task_table.cellWidget(idx, 1)
        if widget:
            pbar = widget.findChild(QProgressBar)
            if pbar: pbar.setValue(percent)

    def on_row_success(self, idx, fname, url):
        # 更新链接列
        item_url = QTableWidgetItem(url)
        item_url.setForeground(Qt.blue)
        self.task_table.setItem(idx, 2, item_url)

        # 更新按钮
        widget = self.task_table.cellWidget(idx, 3)
        if widget:
            btn = widget.findChild(QPushButton)
            if btn:
                btn.setEnabled(True)
                btn.setCursor(Qt.PointingHandCursor)
                # 绑定复制
                try:
                    btn.clicked.disconnect()
                except:
                    pass
                btn.clicked.connect(lambda: self.copy_single(url, btn))

        # 记录数据
        self.tasks_data[idx] = {'filename': fname, 'url': url}

    def on_row_error(self, idx, msg):
        self.task_table.setItem(idx, 2, QTableWidgetItem(f"失败: {msg}"))
        self.task_table.item(idx, 2).setForeground(Qt.red)

    def on_all_finished(self):
        self.drop_area.setEnabled(True)
        self.lbl_status.setText("✅ 队列处理完成")

        # 自动复制逻辑 (只复制链接)
        config = ConfigManager.load_config()
        if config.get('auto_copy', True) and self.tasks_data:
            self.copy_all(mode="url", silent=True)
            self.lbl_status.setText("✅ 已自动复制链接到剪切板")

    def copy_single(self, url, btn):
        QApplication.clipboard().setText(url)
        original_text = btn.text()
        btn.setText("已复制")
        QTimer.singleShot(1000, lambda: btn.setText(original_text))

    def copy_all(self, mode="url", silent=False):
        if not self.tasks_data: return

        # 按索引排序，保证顺序和上传顺序一致
        sorted_indices = sorted(self.tasks_data.keys())
        lines = []
        for i in sorted_indices:
            data = self.tasks_data[i]
            if mode == "url":
                lines.append(data['url'])
            elif mode == "markdown":
                # Markdown 格式: ![文件名](链接)
                lines.append(f"![{data['filename']}]({data['url']})")

        text = "\n".join(lines)
        QApplication.clipboard().setText(text)
        if not silent:
            desc = "所有链接" if mode == "url" else "Markdown"
            self.lbl_status.setText(f"已复制 {len(lines)} 条 {desc}")
            QMessageBox.information(self, "复制成功", f"已将 {len(lines)} 条记录复制为 {desc} 格式。")

    def clear_table(self):
        self.task_table.setRowCount(0)
        self.tasks_data = {}


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    font = QFont("Microsoft YaHei UI", 10)  # 统一字体
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
