FROM ubuntu:20.04

# 避免交互式安装
ENV DEBIAN_FRONTEND=noninteractive

# 设置pip使用阿里云镜像源
ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV PIP_TRUSTED_HOST=mirrors.aliyun.com

# 更换为阿里云Ubuntu镜像源，解决apt-get update问题
RUN sed -i 's/archive.ubuntu.com/mirrors.aliyun.com\/ubuntu/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/mirrors.aliyun.com\/ubuntu/g' /etc/apt/sources.list

# 安装系统依赖
RUN apt-get clean && apt-get update --fix-missing && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    libpq-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装Miniforge以更好地支持cadquery
RUN curl -L -o miniforge.sh https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh && \
    bash miniforge.sh -b -p /opt/miniforge3 && \
    rm miniforge.sh

# 初始化conda
ENV PATH=/opt/miniforge3/bin:$PATH
RUN conda init bash

# 设置工作目录
WORKDIR /app

# 复制依赖文件和入口文件
COPY requirements.txt .
COPY precision_machining_website/entrypoint.sh .

# 创建conda环境并安装依赖
RUN conda create -n cq_env python=3.9 && \
    conda activate cq_env && \
    conda config --add channels conda-forge && \
    conda install -c conda-forge cadquery && \
    pip3 install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/ && \
    pip3 install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 复制项目文件
COPY precision_machining_website/ .

# 创建静态文件和媒体文件目录
RUN mkdir -p static
RUN mkdir -p media
RUN mkdir -p staticfiles

# 给予入口文件执行权限
RUN chmod +x entrypoint.sh

# 收集静态文件（忽略错误）
RUN python3 manage.py collectstatic --noinput || echo "Static collection failed, continuing..."

# 暴露端口
EXPOSE 8000

# 设置入口点
ENTRYPOINT ["./entrypoint.sh"]

# 启动命令
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "machining_platform.wsgi:application"]