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
    echo -e "\n检查是否配置了阿里云镜像加速器:"
    if grep -q "registry.cn-hangzhou.aliyuncs.com" /etc/docker/daemon.json; then
        echo "  ✓ 已配置阿里云镜像加速器"
    else
        echo "  ✗ 未配置阿里云镜像加速器"
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

# 检查ubuntu基础镜像是否存在
echo -e "\n7. 检查ubuntu基础镜像:"
if docker images | grep -q "ubuntu.*20.04"; then
    echo "  ✓ ubuntu:20.04镜像已存在"
else
    echo "  ✗ ubuntu:20.04镜像不存在，需要拉取"
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
timeout 10 curl -s -o /dev/null -w "HTTP状态码: %{http_code}\n" https://registry.cn-hangzhou.aliyuncs.com

echo -e "\n================== 检查完成 =================="
echo "如果需要实时监控日志，请使用以下命令："
echo "  查看web服务日志: docker-compose logs -f web"
echo "  查看数据库日志: docker-compose logs -f db"
echo ""
echo "如果遇到镜像拉取问题，请运行以下命令配置镜像加速器："
echo "  sudo chmod +x configure_docker_mirror.sh"
echo "  sudo ./configure_docker_mirror.sh"
echo ""
echo "如果自动拉取镜像失败，可以手动拉取："
echo "  docker pull registry.cn-hangzhou.aliyuncs.com/docker/library/ubuntu:20.04"
echo "  docker tag registry.cn-hangzhou.aliyuncs.com/docker/library/ubuntu:20.04 ubuntu:20.04"