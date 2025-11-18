FROM centos:7

# 安装EPEL仓库和开发工具
RUN yum -y update && \
    yum -y install epel-release && \
    yum -y groupinstall "Development Tools" && \
    yum -y install python3 python3-devel python3-pip postgresql-devel && \
    yum clean all

# 设置工作目录
WORKDIR /app

# 复制依赖文件和入口文件
COPY requirements.txt .
COPY precision_machining_website/entrypoint.sh .

# 安装Python依赖
RUN pip3 install --upgrade pip && pip3 install -r requirements.txt

# 复制项目文件
COPY precision_machining_website/ .

# 给予入口文件执行权限
RUN chmod +x entrypoint.sh

# 收集静态文件
RUN python3 manage.py collectstatic --noinput

# 暴露端口
EXPOSE 8000

# 设置入口点
ENTRYPOINT ["./entrypoint.sh"]

# 启动命令
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "machining_platform.wsgi:application"]