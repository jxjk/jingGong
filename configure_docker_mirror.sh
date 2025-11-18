#!/bin/bash

# Docker镜像加速配置脚本

echo "开始配置Docker镜像加速器..."

# 检查是否以root权限运行
if [[ $EUID -ne 0 ]]; then
   echo "请以root权限运行此脚本" 
   exit 1
fi

# 创建Docker配置目录
mkdir -p /etc/docker

# 创建daemon.json配置文件（使用阿里云镜像加速器）
cat > /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://registry.cn-hangzhou.aliyuncs.com",
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ]
}
EOF

echo "Docker镜像加速器配置已完成"

# 重启Docker服务
echo "正在重启Docker服务..."
systemctl daemon-reload
systemctl restart docker

if [ $? -eq 0 ]; then
    echo "Docker服务重启成功"
    echo "您现在可以尝试重新构建镜像:"
    echo "  cd jingGong"
    echo "  docker-compose build"
else
    echo "Docker服务重启失败，请手动检查配置"
fi