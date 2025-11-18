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

# 获取阿里云镜像加速器地址
echo "请输入您的阿里云镜像加速器地址（格式如：https://<ID>.mirror.aliyuncs.com）："
read -r MIRROR_URL

if [ -z "$MIRROR_URL" ]; then
    echo "未输入镜像加速器地址，使用默认地址"
    MIRROR_URL="https://registry.cn-hangzhou.aliyuncs.com"
fi

# 创建daemon.json配置文件
cat > /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": ["$MIRROR_URL"]
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
    echo ""
    echo "或者直接启动服务:"
    echo "  docker-compose up -d"
else
    echo "Docker服务重启失败，请手动检查配置"
fi

echo ""
echo "关键说明：阿里云镜像加速器已完整代理 Docker Hub 官方镜像（包括 library/ubuntu 和 library/postgres）"
echo "配置后无需修改 docker-compose.yml，Docker会自动通过加速器拉取镜像"