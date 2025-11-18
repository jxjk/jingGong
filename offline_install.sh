#!/bin/bash

# 离线安装脚本 - 用于解决网络问题

echo "开始准备离线安装包..."

# 创建目录用于存储离线包
mkdir -p offline_packages

# 在本地有网络的环境中运行以下命令来下载依赖包
# pip3 download -r requirements.txt -d offline_packages

echo "请在有网络的环境中执行以下步骤来准备离线安装包："
echo "1. 创建目录: mkdir -p offline_packages"
echo "2. 下载依赖包: pip3 download -r requirements.txt -d offline_packages"
echo "3. 将整个offline_packages目录上传到服务器"
echo ""
echo "在服务器上，修改Dockerfile使用以下命令安装依赖："
echo "COPY offline_packages /app/offline_packages"
echo "RUN pip3 install --find-links /app/offline_packages --no-index -r requirements.txt"