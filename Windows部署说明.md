# Windows 11 Docker 部署说明

本文档介绍了如何在 Windows 11 系统上使用 Docker 部署精密加工平台项目。

## 前提条件

1. Windows 11 操作系统
2. 已安装 Docker Desktop for Windows
3. 已配置 Docker Desktop 使用 Linux 容器模式

## 部署步骤

### 1. 克隆项目代码

```bash
git clone <项目地址>
cd jingGong
```

### 2. 构建和启动服务

使用专门针对 Windows 环境优化的 docker-compose 配置文件：

```bash
docker-compose -f docker-compose.windows.yml up --build
```

首次运行会自动构建镜像并启动容器，过程可能需要几分钟时间。

### 3. 访问应用

服务启动后，在浏览器中访问 http://localhost:8000

### 4. 管理命令

#### 查看运行状态
```bash
docker-compose -f docker-compose.windows.yml ps
```

#### 查看日志
```bash
docker-compose -f docker-compose.windows.yml logs -f web
```

#### 进入容器执行命令
```bash
docker-compose -f docker-compose.windows.yml exec web bash
```

#### 停止服务
```bash
docker-compose -f docker-compose.windows.yml down
```

#### 重新构建并启动
```bash
docker-compose -f docker-compose.windows.yml down
docker-compose -f docker-compose.windows.yml up --build
```

## 注意事项

1. Windows 环境下文件权限可能会有所不同，已通过配置进行优化
2. 首次启动时，数据库需要初始化，请耐心等待
3. 如果遇到端口冲突，请修改 docker-compose.windows.yml 中的端口映射
4. 所有数据存储在 Docker 卷中，即使容器被删除也不会丢失
5. 如需启用超级用户，请在环境变量中设置相应的参数

## 故障排除

### 1. 构建失败
如果在构建过程中遇到网络问题，请确认 Docker 已配置国内镜像加速器。

### 2. 数据库连接失败
确保 db 服务已经启动并且网络连接正常，可以通过以下命令检查：
```bash
docker-compose -f docker-compose.windows.yml logs db
```

### 3. 权限问题
Windows 环境下可能出现文件权限问题，已通过配置优化，如仍有问题可尝试重启 Docker 服务。

### 4. Docker Desktop 问题
如果遇到 "open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified" 错误，请检查：

1. Docker Desktop 是否正在运行
2. Docker Desktop 是否已切换到 Linux 容器模式
   - 在 Docker Desktop 系统托盘图标上右键点击
   - 确保 "Switch to Windows containers..." 选项可用（如果显示 "Switch to Linux containers..."，请点击切换）
3. 重启 Docker Desktop 服务
4. 在 Windows PowerShell 中运行以下命令检查 Docker 是否正常工作：
   ```bash
   docker info
   docker run hello-world
   ```

### 5. 镜像拉取问题
如果你遇到类似以下错误：
```
failed to resolve reference "docker.io/library/postgres:13": failed to do request
```

这通常是因为 Docker 镜像源配置有问题。请按照以下步骤配置 Docker 镜像加速器：

1. 打开 Docker Desktop 设置
2. 进入 "Docker Engine" 选项卡
3. 在配置文件中添加有效的镜像加速器配置：
   ```json
   {
     "registry-mirrors": [
       "https://hub-mirror.c.163.com",
       "https://mirror.baidubce.com"
     ]
   }
   ```
4. 点击 "Apply & restart" 重启 Docker 服务

注意：请确保使用的镜像源是有效的。一些常用的国内镜像源包括：
- 网易云镜像：https://hub-mirror.c.163.com
- 百度云镜像：https://mirror.baidubce.com
- 阿里云镜像：需要注册阿里云账号获取专属加速地址

如果仍然存在问题，请尝试以下方法：
1. 检查网络连接是否正常
2. 临时禁用防火墙和杀毒软件
3. 使用手机热点测试是否能拉取镜像（判断是否为网络限制问题）