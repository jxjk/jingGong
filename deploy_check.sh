#!/bin/bash

# 部署检查脚本
echo "================== 部署状态检查 =================="

# 检查Docker服务状态
echo "1. 检查Docker服务状态:"
systemctl is-active docker

# 检查docker-compose是否安装
echo -e "\n2. 检查docker-compose版本:"
docker-compose --version

# 检查正在运行的容器
echo -e "\n3. 检查正在运行的容器:"
docker ps

# 检查所有容器（包括停止的）
echo -e "\n4. 检查所有容器:"
docker ps -a

# 检查镜像
echo -e "\n5. 检查构建的镜像:"
docker images | grep jinggong

# 检查服务状态
echo -e "\n6. 检查服务状态:"
docker-compose ps

# 检查web服务日志（最近20行）
echo -e "\n7. 检查web服务日志（最近20行）:"
docker-compose logs --tail=20 web

# 检查数据库服务日志（最近20行）
echo -e "\n8. 检查数据库服务日志（最近20行）:"
docker-compose logs --tail=20 db

# 检查磁盘使用情况
echo -e "\n9. 检查磁盘使用情况:"
df -h

# 检查内存使用情况
echo -e "\n10. 检查内存使用情况:"
free -h

echo -e "\n================== 检查完成 =================="
echo "如果需要实时监控日志，请使用以下命令："
echo "  查看web服务日志: docker-compose logs -f web"
echo "  查看数据库日志: docker-compose logs -f db"