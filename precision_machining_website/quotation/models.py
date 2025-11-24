from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.models import User
import os


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
    
    # 报价请求状态
    QUOTATION_STATUS = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('quoted', '已报价'),
        ('confirmed', '已确认'),
        ('cancelled', '已取消'),
    ]
    
    # 基本信息
    name = models.CharField(max_length=100, verbose_name='姓名')
    email = models.EmailField(verbose_name='邮箱')
    phone = models.CharField(max_length=20, verbose_name='电话')
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='客户')  # 添加用户关联字段
    contact_person = models.CharField(max_length=100, blank=True, verbose_name='联系人')  # 添加联系人字段
    
    # 项目信息
    part_name = models.CharField(max_length=200, blank=True, verbose_name='零件名称')  # 添加零件名称字段
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
    oc_curved_surfaces = models.IntegerField('曲面数量', blank=True, null=True)
    oc_sharp_edges = models.IntegerField('锐边数量', blank=True, null=True)
    oc_holes = models.IntegerField('孔洞数量', blank=True, null=True)
    oc_undercuts = models.IntegerField('倒勾特征数量', blank=True, null=True)
    oc_min_tolerance = models.FloatField('最小公差要求', blank=True, null=True)
    oc_estimated_weight = models.FloatField('估算重量', blank=True, null=True)
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
    
    # CadQuery分析相关字段
    cq_cnc_difficulty_level = models.CharField(
        'CNC难度等级',
        max_length=20,
        choices=[
            ('EASY', '容易'),
            ('MEDIUM', '中等'),
            ('HARD', '困难')
        ],
        blank=True,
        null=True
    )
    cq_cnc_difficulty_score = models.IntegerField('CNC难度评分', blank=True, null=True)
    cq_estimated_cost = models.FloatField('估算成本', blank=True, null=True)
    cq_fillets = models.IntegerField('圆角数量', blank=True, null=True)
    cq_finishing_time = models.FloatField('精加工时间(分钟)', blank=True, null=True)
    cq_holes = models.IntegerField('孔数量', blank=True, null=True)
    cq_recommended_process = models.CharField('推荐工艺', max_length=50, blank=True, null=True)
    cq_roughing_time = models.FloatField('粗加工时间(分钟)', blank=True, null=True)
    cq_thin_walls = models.BooleanField('薄壁结构', default=False)
    cq_utilization_percent = models.FloatField('材料利用率(%)', blank=True, null=True)
    cq_waste_volume = models.FloatField('材料浪费量', blank=True, null=True)
    
    # 报价信息
    status = models.CharField('报价状态', max_length=20, choices=QUOTATION_STATUS, default='pending')
    estimated_price = models.DecimalField('预估价格', max_digits=10, decimal_places=2, null=True, blank=True)
    final_price = models.DecimalField('最终价格', max_digits=10, decimal_places=2, null=True, blank=True)
    price_explanation = models.TextField('价格说明', blank=True)
    
    # 时间戳
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_processed = models.BooleanField(default=False, verbose_name='已处理')
    
    class Meta:
        verbose_name = '报价请求'
        verbose_name_plural = '报价请求'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.name}的报价请求 - {self.created_at.strftime('%Y-%m-%d')}"

    def can_delete(self, user):
        """检查用户是否有权限删除此报价请求"""
        # 用户可以删除自己的报价请求，或者管理员可以删除任何报价请求
        return user.is_authenticated and (self.customer == user or user.is_staff)

    def get_machining_difficulty_display(self):
        difficulty_mapping = {
            'EASY': '容易',
            'MEDIUM': '中等',
            'HARD': '困难',
            'VERY_HARD': '非常困难'
        }
        return difficulty_mapping.get(self.oc_machining_difficulty, '未评估')

    def save(self, *args, **kwargs):
        # 如果没有提供零件名称，则自动生成
        if not self.part_name:
            if self.model_file:
                # 使用模型文件名作为基础
                filename = os.path.basename(self.model_file.name)
                name_without_ext = os.path.splitext(filename)[0]
                self.part_name = f"{name_without_ext}_{self.created_at.strftime('%Y%m%d')}"
            else:
                # 如果没有模型文件，则使用加工类型和日期
                processing_type_display = dict(self.PROCESSING_TYPES).get(self.processing_type, '未知')
                self.part_name = f"{processing_type_display}_{self.created_at.strftime('%Y%m%d')}"
        
        # 如果用户已登录，设置客户关联
        if not self.customer_id and self.email:
            try:
                self.customer = User.objects.get(email=self.email)
            except User.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)


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
    
    # CadQuery分析相关字段
    cq_cnc_difficulty_level = models.CharField(
        'CNC难度等级',
        max_length=20,
        choices=[
            ('EASY', '容易'),
            ('MEDIUM', '中等'),
            ('HARD', '困难')
        ],
        blank=True,
        null=True
    )
    cq_cnc_difficulty_score = models.IntegerField('CNC难度评分', blank=True, null=True)
    cq_estimated_cost = models.FloatField('估算成本', blank=True, null=True)
    cq_fillets = models.IntegerField('圆角数量', blank=True, null=True)
    cq_finishing_time = models.FloatField('精加工时间(分钟)', blank=True, null=True)
    cq_holes = models.IntegerField('孔数量', blank=True, null=True)
    cq_recommended_process = models.CharField('推荐工艺', max_length=50, blank=True, null=True)
    cq_roughing_time = models.FloatField('粗加工时间(分钟)', blank=True, null=True)
    cq_thin_walls = models.BooleanField('薄壁结构', default=False)
    cq_utilization_percent = models.FloatField('材料利用率(%)', blank=True, null=True)
    cq_waste_volume = models.FloatField('材料浪费量', blank=True, null=True)
    
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
