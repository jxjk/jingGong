from django.db import models
from django.utils.text import slugify
import uuid

class Category(models.Model):
    """作品分类"""
    name = models.CharField(max_length=100, unique=True, verbose_name='分类名称')
    slug = models.SlugField(max_length=100, blank=True, verbose_name='URL标识')
    description = models.TextField(blank=True, verbose_name='分类描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '作品分类'
        verbose_name_plural = '作品分类'
        ordering = ['name']
        
    def __str__(self):
        return self.name
        
    def save(self, *args, **kwargs):
        # 每次保存时都根据名称生成slug，使用英文字符
        if self.name:
            # 定义中文分类名到英文slug的映射
            chinese_to_english = {
                '精密零件': 'precise-part',
                '工装夹具': 'fixture',
                '生产线集成': 'production-line',
                '概念设计': 'concept-design',
            }
            
            # 如果是已知的中文分类，使用对应的英文slug
            if self.name in chinese_to_english:
                self.slug = chinese_to_english[self.name]
            else:
                # 对于其他情况，使用拼音或英文翻译
                # 这里我们使用拼音转换（如果需要更准确的结果可以使用pypinyin库）
                pinyin_dict = {
                    '精密': 'jing-mi',
                    '零件': 'ling-jian',
                    '工装': 'gong-zhuang',
                    '夹具': 'jia-ju',
                    '生产': 'sheng-chan',
                    '线': 'xian',
                    '集成': 'ji-cheng',
                    '概念': 'gai-nian',
                    '设计': 'she-ji',
                }
                
                # 尝试简单的词语替换
                slug_parts = []
                for chinese_word, pinyin in pinyin_dict.items():
                    if chinese_word in self.name:
                        slug_parts.append(pinyin)
                
                if slug_parts:
                    self.slug = '-'.join(slug_parts)
                else:
                    # 如果没有匹配的拼音，使用默认的slugify但不使用unicode
                    self.slug = slugify(self.name, allow_unicode=False)
        
        # 确保slug不为空
        if not self.slug:
            # 如果名称为空或者slugify后为空，则使用UUID的一部分作为slug
            self.slug = f"category-{uuid.uuid4().hex[:8]}"
        super().save(*args, **kwargs)


class Work(models.Model):
    """作品模型"""
    WORK_CATEGORIES = [
        ('precise_part', '精密零件'),
        ('fixture', '工装夹具'),
        ('production_line', '生产线集成'),
        ('concept_design', '概念设计'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='作品标题')
    description = models.TextField(verbose_name='作品描述')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name='分类')
    image = models.ImageField(upload_to='works/images/', blank=True, verbose_name='展示图片')
    project_background = models.TextField(verbose_name='项目背景')
    model_file = models.FileField(upload_to='works/models/', blank=True, verbose_name='3D模型文件')
    process_difficulties = models.TextField(verbose_name='加工难点与解决方案')
    equipment_used = models.TextField(verbose_name='使用设备')
    materials = models.TextField(verbose_name='材料')
    process_techniques = models.TextField(verbose_name='工艺')
    project_duration = models.CharField(max_length=100, verbose_name='项目周期')
    video_url = models.URLField(blank=True, verbose_name='视频链接')
    is_featured = models.BooleanField(default=False, verbose_name='推荐作品')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '作品'
        verbose_name_plural = '作品'
        ordering = ['-created_at']
        
    def __str__(self):
        return self.title