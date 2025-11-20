from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Order, OrderStatusHistory, ProductionProgress, Notification


class OrderModelTest(TestCase):
    def setUp(self):
        # 创建测试用户
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 创建测试订单
        self.order = Order.objects.create(
            order_number='ORD001',
            customer=self.user,
            product_name='测试产品',
            product_description='这是一个测试产品',
            quantity=10,
            unit_price=100.00,
            total_price=1000.00,
            customer_name='张三',
            customer_email='zhangsan@example.com',
            customer_phone='13800138000',
            shipping_address='北京市朝阳区测试地址',
            shipping_contact='李四',
            shipping_phone='13900139000'
        )

    def test_order_creation(self):
        """测试订单创建"""
        self.assertEqual(self.order.order_number, 'ORD001')
        self.assertEqual(self.order.customer, self.user)
        self.assertEqual(self.order.status, 'pending_review')
        self.assertEqual(str(self.order), '订单 ORD001 - 测试产品')

    def test_order_status_display(self):
        """测试订单状态显示"""
        self.assertEqual(self.order.get_status_display_chinese(), '待审核')

    def test_order_status_history(self):
        """测试订单状态历史"""
        # 创建状态历史记录
        history = OrderStatusHistory.objects.create(
            order=self.order,
            status='pending_payment',
            operator='管理员',
            notes='审核通过'
        )
        
        self.assertEqual(history.status, 'pending_payment')
        self.assertEqual(str(history), '订单 ORD001 - 待付款')

    def test_production_progress(self):
        """测试生产进度"""
        # 创建生产进度记录
        progress = ProductionProgress.objects.create(
            order=self.order,
            stage='CNC加工',
            description='正在进行CNC加工',
            monitoring_description='设备运行正常'
        )
        
        self.assertEqual(progress.stage, 'CNC加工')
        self.assertFalse(progress.is_completed)
        self.assertEqual(str(progress), '订单 ORD001 - CNC加工')

    def test_notification(self):
        """测试通知"""
        # 创建通知
        notification = Notification.objects.create(
            order=self.order,
            title='订单状态更新',
            content='您的订单已进入排产中状态'
        )
        
        self.assertEqual(notification.title, '订单状态更新')
        self.assertFalse(notification.is_read)
        self.assertEqual(str(notification), '订单 ORD001 - 订单状态更新')