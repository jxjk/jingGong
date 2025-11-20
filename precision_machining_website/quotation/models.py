from django.db import models
from django.utils import timezone

class QuotationRequest(models.Model):
    """报价请求模型"""
    # 加工类型选项
    PROCESSING_TYPES = [
        ('cnc_milling', 'CNC铣削'),
        ('cnc_turning', 'CNC车削'),
        ('3d_printing', '3D打印'),
    ]
    
    # 材料选项
    MATERIALS = [
        ('aluminum', '铝合金'),
        ('steel', '钢材'),
        ('stainless_steel', '不锈钢'),
        ('plastic', '塑料'),
        ('other', '其他'),
    ]
    
    # 表面处理选项
    SURFACE_TREATMENTS = [
        ('none', '无'),
        ('anodizing', '阳极氧化'),
        ('painting', '喷漆'),
        ('polishing', '抛光'),
        ('other', '其他'),
    ]
    
    # 基本信息
    name = models.CharField(max_length=100, verbose_name='姓名')
    email = models.EmailField(verbose_name='邮箱')
    phone = models.CharField(max_length=20, verbose_name='电话')
    
    # 项目信息
    processing_type = models.CharField(max_length=20, choices=PROCESSING_TYPES, verbose_name='加工类型')
    material = models.CharField(max_length=20, choices=MATERIALS, verbose_name='材料')
    quantity = models.PositiveIntegerField(verbose_name='数量')
    accuracy = models.CharField(max_length=50, verbose_name='精度要求')
    surface_treatment = models.CharField(max_length=20, choices=SURFACE_TREATMENTS, verbose_name='表面处理')
    description = models.TextField(blank=True, verbose_name='附加说明')
    
    # 文件上传
    model_file = models.FileField(upload_to='quotation_models/', blank=True, verbose_name='3D模型文件')
    
    # 3D模型分析结果
    volume = models.FloatField(null=True, blank=True, verbose_name='体积 (cm³)')
    surface_area = models.FloatField(null=True, blank=True, verbose_name='表面积 (cm²)')
    bounding_box_length = models.FloatField(null=True, blank=True, verbose_name='包围盒长度 (mm)')
    bounding_box_width = models.FloatField(null=True, blank=True, verbose_name='包围盒宽度 (mm)')
    bounding_box_height = models.FloatField(null=True, blank=True, verbose_name='包围盒高度 (mm)')
    min_radius = models.FloatField(null=True, blank=True, verbose_name='最小拐角半径 (mm)')
    max_aspect_ratio = models.FloatField(null=True, blank=True, verbose_name='最大径长比')
    complexity_score = models.FloatField(null=True, blank=True, verbose_name='复杂度评分')
    min_tool_diameter = models.FloatField(null=True, blank=True, verbose_name='最小刀具直径 (mm)')
    machining_difficulty = models.FloatField(null=True, blank=True, verbose_name='加工难度评分')
    
    # OpenCASCADE分析相关字段
    surface_area = models.FloatField('表面积', blank=True, null=True)
    volume = models.FloatField('体积', blank=True, null=True)
    curved_surfaces = models.IntegerField('曲面数量', blank=True, null=True)
    sharp_edges = models.IntegerField('锐边数量', blank=True, null=True)
    holes = models.IntegerField('孔洞数量', blank=True, null=True)
    undercuts = models.IntegerField('倒勾特征数量', blank=True, null=True)
    min_tolerance = models.FloatField('最小公差要求', blank=True, null=True)
    estimated_weight = models.FloatField('估算重量', blank=True, null=True)
    oc_machining_difficulty = models.CharField(
        'OpenCASCADE加工难度', 
        max_length=20, 
        choices=[
            ('EASY', '容易'),
            ('MEDIUM', '中等'),
            ('HARD', '困难'),
            ('VERY_HARD', '非常困难')
        ],
        blank=True,
        null=True
    )
    
    # 时间戳
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    is_processed = models.BooleanField(default=False, verbose_name='已处理')
    
    class Meta:
        verbose_name = '报价请求'
        verbose_name_plural = '报价请求'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.name}的报价请求 - {self.created_at.strftime('%Y-%m-%d')}"

    def get_machining_difficulty_display(self):
        difficulty_mapping = {
            'EASY': '容易',
            'MEDIUM': '中等',
            'HARD': '困难',
            'VERY_HARD': '非常困难'
        }
        return difficulty_mapping.get(self.oc_machining_difficulty, '未评估')


class QuotationAdjustmentFactor(models.Model):
    """报价调控因子模型"""
    name = models.CharField(max_length=100, unique=True, verbose_name='因子名称')
    description = models.TextField(blank=True, verbose_name='描述')
    value = models.FloatField(default=1.0, verbose_name='因子值')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '报价调控因子'
        verbose_name_plural = '报价调控因子'
        ordering = ['name']
        
    def __str__(self):
        return f"{self.name} ({self.value})"


class DFMAnalysis(models.Model):
    """DFM分析模型"""
    # 基本信息
    name = models.CharField(max_length=100, verbose_name='分析名称')
    email = models.EmailField(verbose_name='邮箱')
    company = models.CharField(max_length=100, blank=True, verbose_name='公司')
    
    # 文件上传
    model_file = models.FileField(upload_to='dfm_models/', verbose_name='3D模型文件')
    
    # 分析结果
    volume = models.FloatField(null=True, blank=True, verbose_name='体积 (cm³)')
    surface_area = models.FloatField(null=True, blank=True, verbose_name='表面积 (cm²)')
    bounding_box_length = models.FloatField(null=True, blank=True, verbose_name='包围盒长度 (mm)')
    bounding_box_width = models.FloatField(null=True, blank=True, verbose_name='包围盒宽度 (mm)')
    bounding_box_height = models.FloatField(null=True, blank=True, verbose_name='包围盒高度 (mm)')
    min_radius = models.FloatField(null=True, blank=True, verbose_name='最小拐角半径 (mm)')
    max_aspect_ratio = models.FloatField(null=True, blank=True, verbose_name='最大径长比')
    complexity_score = models.FloatField(null=True, blank=True, verbose_name='复杂度评分')
    min_tool_diameter = models.FloatField(null=True, blank=True, verbose_name='最小刀具直径 (mm)')
    machining_difficulty = models.FloatField(null=True, blank=True, verbose_name='加工难度评分')
    
    # DFM建议
    recommendations = models.TextField(blank=True, verbose_name='优化建议')
    
    # 时间戳
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    is_processed = models.BooleanField(default=False, verbose_name='已处理')
    
    class Meta:
        verbose_name = 'DFM分析'
        verbose_name_plural = 'DFM分析'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.name}的DFM分析 - {self.created_at.strftime('%Y-%m-%d')}"
