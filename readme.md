# ☁️ 阿里云 OSS 简易上传助手 (Aliyun OSS Uploader GUI)

[![Build Status](https://img.shields.io/github/actions/workflow/status/qcgzxw/oss-uploader/release.yml?label=Build)](https://github.com/qcgzxw/oss-uploader/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-yellow.svg)](https://www.python.org/)

一个基于 Python + PyQt5 开发的轻量级阿里云 OSS 图形化上传工具。支持 Windows、macOS 和 Linux (Ubuntu) 系统。

主要解决“快速将文件上传到图床/对象存储并获取链接”的需求，支持拖拽上传、进度显示和自动复制链接。

<div style="display:flex; gap:10px;">
  <img src="screenshots/截图 2025-12-16 11-08-37.png" width="24%">
  <img src="screenshots/截图 2025-12-16 11-08-56.png" width="24%">
  <img src="screenshots/截图 2025-12-15 16-08-51.png" width="24%">
  <img src="screenshots/截图 2025-12-15 16-08-56.png" width="24%">
</div>

## ✨ 功能特性

- **跨平台支持**：完美运行于 Windows, macOS, Ubuntu。
- **极简操作**：支持 **拖拽上传** 或点击选择文件。
- **实时进度**：上传大文件时显示进度条，界面不卡顿。
- **自动处理**：
  - 上传成功后 **自动复制链接** 到剪切板。
  - 支持 **自定义域名** (CNAME)。
  - 支持 **随机文件名** (UUID) 防止覆盖。
- **灵活配置**：
  - 支持自定义上传路径规则（如 `uploads/{year}/{month}/`）。
  - 支持 **剪切板一键导入配置** (JSON格式)。
  - 内置 **连通性测试**，防止参数填错。

## 📥 下载与安装

请前往 [Releases 页面](https://github.com/qcgzxw/oss-uploader/releases) 下载对应系统的可执行文件：

- **Windows**: 下载 `.exe` 文件，双击直接运行。
- **macOS**: 下载对应版本，解压运行（首次运行可能需要在“安全性与隐私”中允许）。
- **Linux**: 下载并赋予执行权限 (`chmod +x`) 后运行。

## ⚙️ 配置指南

首次运行软件点击右上角 **“⚙️ 设置”**，填写阿里云 OSS 的相关信息：

- **AccessKey ID / Secret**: 阿里云控制台获取。
- **Bucket Name**: 你的存储桶名称。
- **Endpoint**: 选择对应的地域节点（如下拉框未列出支持手动输入）。
- **自定义域名**: (可选) 绑定了 CDN 的域名，如 `https://cdn.example.com`。

### ⚡️ 快捷导入配置
你可以将配置整理为 JSON 格式复制到剪切板，启动软件时会自动识别并询问导入：

```json
{
    "access_key_id": "LTAI5txxxx",
    "access_key_secret": "HqyKxxxx",
    "bucket_name": "my-blog-img",
    "endpoint": "oss-cn-shenzhen.aliyuncs.com"
}
````

## 🛠️ 本地开发与构建

如果你想自己修改代码或编译：

### 1\. 环境准备

```bash
# 克隆仓库
git clone [https://github.com/qcgzxw/oss-uploader.git](https://github.com/qcgzxw/oss-uploader.git)
cd oss-uploader

# 安装依赖
pip install -r requirements.txt
```

### 2\. 运行代码

```bash
python src/main.py
```

### 3\. 打包发布

本项目配置了 GitHub Actions，Push打标签 (`v*`) 可自动构建。本地打包使用 PyInstaller：

```bash
# Windows / Linux / Mac
pyinstaller --onefile --windowed --name "OSS-Uploader" src/main.py
```

## 📝 路径变量说明

在设置“保存路径”时，支持以下占位符：

  - `{year}`: 年份 (2025)
  - `{month}`: 月份 (12)
  - `{day}`: 日期 (14)
  - `{username}`: 当前操作系统用户名

**示例**: `static/images/{year}/{month}`

## 🤝 贡献

欢迎提交 Issue 或 Pull Request 来改进这个小工具！

