from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Order(models.Model):
    """订单模型"""
    
    # 订单状态选项
    ORDER_STATUS_CHOICES = [
        ('pending_review', '待审核'),
        ('pending_payment', '待付款'),
        ('scheduling', '排产中'),
        ('processing', '加工中'),
        ('quality_check', '质检中'),
        ('shipped', '已发货'),
        ('completed', '完成'),
        ('cancelled', '已取消'),
    ]
    
    # 基本信息
    order_number = models.CharField('订单号', max_length=50, unique=True)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='客户')
    created_at = models.DateTimeField('创建时间', default=timezone.now)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    # 订单状态
    status = models.CharField('订单状态', max_length=20, choices=ORDER_STATUS_CHOICES, default='pending_review')
    
    # 产品信息
    product_name = models.CharField('产品名称', max_length=200)
    product_description = models.TextField('产品描述', blank=True)
    quantity = models.PositiveIntegerField('数量', default=1)
    
    # 价格信息
    unit_price = models.DecimalField('单价', max_digits=10, decimal_places=2)
    total_price = models.DecimalField('总价', max_digits=10, decimal_places=2)
    
    # 交期信息
    promised_delivery_date = models.DateTimeField('承诺交期', null=True, blank=True)
    actual_delivery_date = models.DateTimeField('实际交期', null=True, blank=True)
    
    # 客户信息
    customer_name = models.CharField('客户姓名', max_length=100)
    customer_email = models.EmailField('客户邮箱')
    customer_phone = models.CharField('客户电话', max_length=20)
    customer_company = models.CharField('客户公司', max_length=200, blank=True)
    
    # 收货信息
    shipping_address = models.TextField('收货地址')
    shipping_contact = models.CharField('收货联系人', max_length=100)
    shipping_phone = models.CharField('收货电话', max_length=20)
    
    # 备注
    notes = models.TextField('备注', blank=True)
    
    class Meta:
        verbose_name = '订单'
        verbose_name_plural = '订单'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"订单 {self.order_number} - {self.product_name}"
    
    def get_status_display_chinese(self):
        """获取中文状态显示"""
        status_dict = dict(self.ORDER_STATUS_CHOICES)
        return status_dict.get(self.status, self.status)


class OrderStatusHistory(models.Model):
    """订单状态历史记录"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField('状态', max_length=20, choices=Order.ORDER_STATUS_CHOICES)
    timestamp = models.DateTimeField('时间戳', default=timezone.now)
    operator = models.CharField('操作人', max_length=100, blank=True)
    notes = models.TextField('备注', blank=True)
    
    class Meta:
        verbose_name = '订单状态历史'
        verbose_name_plural = '订单状态历史'
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.order.order_number} - {self.get_status_display()}"


class ProductionProgress(models.Model):
    """生产进度记录"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='production_progress')
    stage = models.CharField('生产阶段', max_length=100)
    description = models.TextField('描述')
    started_at = models.DateTimeField('开始时间', null=True, blank=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)
    is_completed = models.BooleanField('已完成', default=False)
    
    # 车间监控信息（脱敏处理）
    monitoring_image = models.ImageField('监控图片', upload_to='monitoring/', null=True, blank=True)
    monitoring_description = models.CharField('监控描述', max_length=200, blank=True)
    
    class Meta:
        verbose_name = '生产进度'
        verbose_name_plural = '生产进度'
        ordering = ['id']
        
    def __str__(self):
        return f"{self.order.order_number} - {self.stage}"


class Notification(models.Model):
    """通知记录"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField('标题', max_length=200)
    content = models.TextField('内容')
    is_read = models.BooleanField('已读', default=False)
    created_at = models.DateTimeField('创建时间', default=timezone.now)
    read_at = models.DateTimeField('阅读时间', null=True, blank=True)
    
    class Meta:
        verbose_name = '通知'
        verbose_name_plural = '通知'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.order.order_number} - {self.title}"