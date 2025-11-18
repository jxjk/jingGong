from django.db import migrations
from django.utils.text import slugify

def populate_slug_fields(apps, schema_editor):
    Category = apps.get_model('gallery', 'Category')
    # 定义中文分类名到英文slug的映射
    chinese_to_english = {
        '精密零件': 'precise-part',
        '工装夹具': 'fixture',
        '生产线集成': 'production-line',
        '概念设计': 'concept-design',
    }
    
    for category in Category.objects.all():
        if not category.slug:
            # 如果是已知的中文分类，使用对应的英文slug
            if category.name in chinese_to_english:
                category.slug = chinese_to_english[category.name]
            else:
                # 对于其他情况，使用普通的slugify但不使用unicode
                slug_base = slugify(category.name, allow_unicode=False)
                if not slug_base:
                    # 如果转换后为空，则使用UUID的一部分
                    slug_base = f"category-{category.id}"
                slug = slug_base
                counter = 1
                while Category.objects.filter(slug=slug).exists():
                    slug = f"{slug_base}-{counter}"
                    counter += 1
                category.slug = slug
            category.save()

def reverse_populate_slug_fields(apps, schema_editor):
    # 回滚操作不需要做任何事情
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('gallery', '0002_category_slug'),
    ]

    operations = [
        migrations.RunPython(populate_slug_fields, reverse_populate_slug_fields),
    ]