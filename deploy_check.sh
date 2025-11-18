#!/bin/bash

# 部署检查脚本
echo "================== 部署状态检查 =================="

# 检查Docker服务状态
echo "1. 检查Docker服务状态:"
systemctl is-active docker

# 检查docker-compose是否安装
echo -e "\n2. 检查docker-compose版本:"
docker-compose --version

# 检查Docker镜像加速配置
echo -e "\n3. 检查Docker镜像加速配置:"
if [ -f /etc/docker/daemon.json ]; then
    echo "Docker daemon配置文件存在:"
    cat /etc/docker/daemon.json
    echo -e "\n检查是否配置了镜像加速器:"
    if grep -q "registry-mirrors" /etc/docker/daemon.json; then
        echo "  ✓ 已配置镜像加速器"
        MIRRORS=$(grep -o '"registry-mirrors"[^}]*' /etc/docker/daemon.json | grep -o '"https://[^"]*"')
        echo "  配置的镜像加速器地址: $MIRRORS"
        # 检查是否为特定的阿里云加速器
        if grep -q "77n6chx1.mirror.aliyuncs.com" /etc/docker/daemon.json; then
            echo "  ✓ 已配置正确的阿里云镜像加速器 (ID: 77n6chx1)"
        fi
    else
        echo "  ✗ 未配置镜像加速器"
    fi
else
    echo "Docker daemon配置文件不存在"
fi

# 检查正在运行的容器
echo -e "\n4. 检查正在运行的容器:"
docker ps

# 检查所有容器（包括停止的）
echo -e "\n5. 检查所有容器:"
docker ps -a

# 检查镜像
echo -e "\n6. 检查构建的镜像:"
docker images | grep jinggong

# 检查ubuntu和postgres基础镜像是否存在
echo -e "\n7. 检查基础镜像:"
if docker images | grep -q "ubuntu.*20.04"; then
    echo "  ✓ ubuntu:20.04镜像已存在"
else
    echo "  ✗ ubuntu:20.04镜像不存在，需要拉取"
fi

if docker images | grep -q "postgres.*13"; then
    echo "  ✓ postgres:13镜像已存在"
else
    echo "  ✗ postgres:13镜像不存在，需要拉取"
fi

# 检查服务状态
echo -e "\n8. 检查服务状态:"
docker-compose ps

# 检查web服务日志（最近20行）
echo -e "\n9. 检查web服务日志（最近20行）:"
docker-compose logs --tail=20 web

# 检查数据库服务日志（最近20行）
echo -e "\n10. 检查数据库服务日志（最近20行）:"
docker-compose logs --tail=20 db

# 检查磁盘使用情况
echo -e "\n11. 检查磁盘使用情况:"
df -h

# 检查内存使用情况
echo -e "\n12. 检查内存使用情况:"
free -h

# 检查网络连接
echo -e "\n13. 检查网络连接到阿里云镜像服务:"
timeout 10 curl -s -o /dev/null -w "HTTP状态码: %{http_code}\n" https://77n6chx1.mirror.aliyuncs.com

echo -e "\n================== 检查完成 =================="
echo "如果需要实时监控日志，请使用以下命令："
echo "  查看web服务日志: docker-compose logs -f web"
echo "  查看数据库日志: docker-compose logs -f db"
echo ""
echo "现在您可以直接启动服务："
echo "  docker-compose up -d"
echo ""
echo "如果自动拉取镜像失败，可以手动拉取："
echo "  # 拉取Ubuntu镜像"
echo "  docker pull registry.cn-hangzhou.aliyuncs.com/docker/library/ubuntu:20.04"
echo "  docker tag registry.cn-hangzhou.aliyuncs.com/docker/library/ubuntu:20.04 ubuntu:20.04"
echo ""
echo "  # 拉取PostgreSQL镜像"
echo "  docker pull registry.cn-hangzhou.aliyuncs.com/docker/library/postgres:13"
echo "  docker tag registry.cn-hangzhou.aliyuncs.com/docker/library/postgres:13 postgres:13"