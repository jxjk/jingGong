FROM registry.cn-hangzhou.aliyuncs.com/docker/library/ubuntu:20.04

# 避免交互式安装
ENV DEBIAN_FRONTEND=noninteractive

# 设置apt使用阿里云镜像源
RUN sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list

# 设置pip使用阿里云镜像源
ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV PIP_TRUSTED_HOST=mirrors.aliyun.com

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件和入口文件
COPY requirements.txt .
COPY precision_machining_website/entrypoint.sh .

# 安装Python依赖（使用阿里云镜像源加速）
RUN pip3 install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/ && \
    pip3 install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

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