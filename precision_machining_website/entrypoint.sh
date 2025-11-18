#!/bin/bash

# 等待数据库就绪
echo "Waiting for database to be ready..."
sleep 10

# 检查数据库连接
echo "Checking database connection..."
python3 manage.py shell -c "
import sys
import psycopg2
from django.conf import settings
try:
    conn = psycopg2.connect(
        dbname=settings.DATABASES['default']['NAME'],
        user=settings.DATABASES['default']['USER'],
        password=settings.DATABASES['default']['PASSWORD'],
        host=settings.DATABASES['default']['HOST'],
        port=settings.DATABASES['default']['PORT']
    )
    conn.close()
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    sys.exit(1)
"

# 收集静态文件
echo "Collect static files"
python3 manage.py collectstatic --noinput || echo "Warning: Static collection failed"

# 应用数据库迁移
echo "Apply database migrations"
python3 manage.py migrate --noinput

# 创建超级用户（仅在环境变量设置时）
if [ "$CREATE_SUPERUSER" = "true" ]; then
    echo "Create superuser"
    python3 manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD') if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists() else None"
fi

# 启动服务器
echo "Starting server"
exec "$@"