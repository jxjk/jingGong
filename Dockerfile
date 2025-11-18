FROM ubuntu:20.04

# 避免交互式安装
ENV DEBIAN_FRONTEND=noninteractive

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

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip3 install --upgrade pip && pip3 install -r requirements.txt

# 复制入口文件
COPY precision_machining_website/entrypoint.sh .

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