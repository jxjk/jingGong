import os
import sys
import django

# 添加项目目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'machining_platform.settings')
django.setup()

from gallery.models import Category, Work
from django.utils.text import slugify

def populate_data():
    # 创建分类
    categories_data = [
        {'name': '精密零件', 'description': '高精度零部件加工，适用于航空航天、医疗器械等领域', 'slug': 'precise-part'},
        {'name': '模具制造', 'description': '各类注塑模具、冲压模具的设计与制造', 'slug': 'mould-manufacturing'},
        {'name': '原型制作', 'description': '快速原型制作，验证产品设计理念', 'slug': 'prototype'},
        {'name': '维修保养', 'description': 'CNC设备维修与保养服务', 'slug': 'maintenance'},
    ]
    
    categories = []
    for cat_data in categories_data:
        category, created = Category.objects.get_or_create(
            name=cat_data['name'],
            defaults={
                'description': cat_data['description'],
                'slug': cat_data['slug']
            }
        )
        categories.append(category)
        if created:
            print(f"Created category: {category.name}")
        else:
            print(f"Category already exists: {category.name}")
    
    # 创建示例作品
    works_data = [
        {
            'title': '汽车刹车盘加工',
            'description': '为本地汽修店定制的高性能刹车盘，采用优质铸铁材料，经过精密加工确保制动安全性',
            'category': categories[0],
            'project_background': '接到本地汽修连锁店订单，需要批量加工高性能刹车盘',
            'process_difficulties': '需要保证尺寸精度和表面光洁度，同时控制成本以满足个体户的价格敏感性',
            'equipment_used': 'CNC立式加工中心、三坐标测量仪',
            'materials': '优质灰口铸铁',
            'process_techniques': '数控车削、精密磨削、热处理',
            'project_duration': '15天',
        },
        {
            'title': '电子产品散热器外壳',
            'description': '为本地电子公司定制的铝合金散热器外壳，轻量化设计，优异的散热性能',
            'category': categories[0],
            'project_background': '本地初创电子企业需要小批量散热器外壳样品进行产品测试',
            'process_difficulties': '复杂几何形状，薄壁结构加工易变形',
            'equipment_used': 'CNC立式加工中心、精密磨床',
            'materials': '6061铝合金',
            'process_techniques': '数控铣削、CNC钻孔、表面阳极氧化处理',
            'project_duration': '10天',
        },
        {
            'title': '塑料注塑模具',
            'description': '为客户定制的日用品塑料外壳注塑模具，可实现大批量生产',
            'category': categories[1],
            'project_background': '个体经营客户需要为其新产品制作注塑模具',
            'process_difficulties': '复杂的内部水路设计和顶出机构，需要精确配合',
            'equipment_used': 'CNC立式加工中心、电火花加工机、精密磨床',
            'materials': 'P20模具钢、718硬化钢',
            'process_techniques': '数控铣削、电火花加工、精密研磨',
            'project_duration': '25天',
        },
        {
            'title': '医疗手持设备原型',
            'description': '为医疗创新团队制作的概念验证原型，用于展示和功能测试',
            'category': categories[2],
            'project_background': '医疗创业团队委托制作其创新产品的功能原型',
            'process_difficulties': '不规则曲面加工，多部件精密装配',
            'equipment_used': 'CNC立式加工中心、3D打印设备',
            'materials': '医用级ABS塑料、不锈钢',
            'process_techniques': '数控铣削、3D打印、激光雕刻',
            'project_duration': '12天',
        }
    ]
    
    for work_data in works_data:
        work, created = Work.objects.get_or_create(
            title=work_data['title'],
            defaults=work_data
        )
        if created:
            print(f"Created work: {work.title}")
        else:
            print(f"Work already exists: {work.title}")

if __name__ == '__main__':
    populate_data()