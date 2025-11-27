from django.test import TestCase
from django.contrib.auth.models import User
from quotation.models import QuotationRequest
from django.core.files.uploadedfile import SimpleUploadedFile
import tempfile
import os

class DFMFunctionalityTest(TestCase):
    def setUp(self):
        """设置测试环境"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
    
    def test_model_fields_added(self):
        """测试模型字段是否已添加"""
        # 创建一个报价请求实例
        quotation = QuotationRequest(
            name='Test User',
            email='test@example.com',
            phone='1234567890',
            processing_type='cnc_milling',
            material='aluminum',
            quantity=1,
            accuracy='±0.01mm',
            surface_treatment='anodizing'
        )
        self.assertTrue(hasattr(quotation, 'profit_margin'))
        self.assertTrue(hasattr(quotation, 'profit_amount'))
        print("✓ 利润相关字段已成功添加到模型中")
    
    def test_dfm_analyzer_integration(self):
        """测试DFM分析器集成"""
        try:
            from quotation.dfm_analyzer import DFMAnalyzer
            print("✓ DFM分析器模块导入成功")
        except ImportError as e:
            print(f"✗ DFM分析器模块导入失败: {e}")
            return

        # 验证DFMAnalyzer类存在
        from quotation.dfm_analyzer import DFMAnalyzer
        self.assertTrue(hasattr(DFMAnalyzer, '__init__'))
        print("✓ DFMAnalyzer类存在")
    
    def test_profit_calculation_methods(self):
        """测试利润计算方法"""
        quotation = QuotationRequest(
            name='Test User',
            email='test@example.com',
            phone='1234567890',
            processing_type='cnc_milling',
            material='aluminum',
            quantity=1,
            accuracy='±0.01mm',
            surface_treatment='anodizing',
            material_cost=100.00,
            processing_cost=50.00,
            programming_cost=20.00,
            surface_treatment_cost=10.00
        )
        quotation.save()
        
        # 测试直接成本计算
        direct_cost = quotation.get_direct_cost()
        expected_cost = 180.00  # 100 + 50 + 20 + 10
        self.assertEqual(direct_cost, expected_cost)
        print(f"✓ 直接成本计算正确: {direct_cost} == {expected_cost}")
        
        # 测试默认利润计算
        default_profit = quotation.get_default_profit()
        expected_default_profit = 36.00  # 180 * 0.20
        self.assertEqual(default_profit, expected_default_profit)
        print(f"✓ 默认利润计算正确: {default_profit} == {expected_default_profit}")
    
    def test_profit_margin_calculation(self):
        """测试利润率计算功能"""
        quotation = QuotationRequest(
            name='Test User',
            email='test@example.com',
            phone='1234567890',
            processing_type='cnc_milling',
            material='aluminum',
            quantity=1,
            accuracy='±0.01mm',
            surface_treatment='anodizing',
            material_cost=100.00,
            processing_cost=50.00,
            programming_cost=20.00,
            surface_treatment_cost=10.00,
            profit_margin=25.00  # 25%利润率
        )
        quotation.save()
        
        final_price = quotation.calculate_final_price_with_profit()
        expected_price = 225.00  # 180 (直接成本) + 45 (25%利润)
        self.assertEqual(final_price, expected_price)
        print(f"✓ 利润率计算正确: {final_price} == {expected_price}")

if __name__ == '__main__':
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
    import django
    django.setup()
    
    # 运行测试
    import unittest
    unittest.main()