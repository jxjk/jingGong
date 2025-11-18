# 精工智造 - 机械加工解决方案平台

这是一个基于Django框架开发的网站项目，用于展示机械加工作品和服务。

## 功能特点

1. 作品展示模块：
   - 支持作品分类展示（精密零件、工装夹具、生产线集成、概念设计）
   - 图片和视频展示
   - 详细的作品信息展示
   - 分页功能

## 技术栈

- Django 3.2
- Python 3
- PostgreSQL (生产环境)
- SQLite (开发环境)
- Bootstrap 5 (前端框架)
- Docker (容器化部署)

## 快速开始

### 使用Docker运行（推荐）

```bash
# 构建并启动服务
docker-compose up --build

# 创建超级用户（首次运行时）
docker-compose exec web python manage.py createsuperuser

# 访问应用
http://localhost:8000/
```

### 本地开发环境

```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser

# 收集静态文件
python manage.py collectstatic

# 启动开发服务器
python manage.py runserver
```

## 目录结构

```
precision_machining_website/
├── machining_platform/     # Django项目配置
├── gallery/               # 作品展示应用
├── templates/             # 模板文件
├── static/                # 静态文件
├── media/                 # 媒体文件（用户上传）
├── Dockerfile             # Docker构建文件
├── docker-compose.yml     # Docker编排文件
├── requirements.txt       # Python依赖
└── README.md             # 项目说明文档
```

## 部署注意事项

1. CentOS 7兼容性：
   - 使用了适用于CentOS 7的Python和包管理器
   - 选择了兼容的Django版本（3.2）

2. 安全性考虑：
   - 用户上传文件存储在独立的media目录
   - 静态文件和媒体文件分离
   - SECRET_KEY不应在代码中硬编码（生产环境应使用环境变量）

3. 性能优化：
   - 使用Gunicorn作为生产级WSGI服务器
   - 静态文件收集和缓存优化
   - 数据库查询优化（通过Django ORM）

## 后续开发计划

1. 实现快速自助报价模块
2. 开发用户中心模块
3. 实现知识库与工具模块
4. 开发后台管理模块

## 许可证

本项目仅供学习和参考使用。