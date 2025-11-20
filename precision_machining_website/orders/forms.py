from django import forms
from .models import Order, ProductionProgress


class OrderCreateForm(forms.ModelForm):
    """订单创建表单"""
    class Meta:
        model = Order
        fields = [
            'product_name', 'product_description', 'quantity',
            'customer_name', 'customer_email', 'customer_phone', 'customer_company',
            'shipping_address', 'shipping_contact', 'shipping_phone',
            'notes'
        ]
        widgets = {
            'product_description': forms.Textarea(attrs={'rows': 4}),
            'shipping_address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class ProductionProgressForm(forms.ModelForm):
    """生产进度表单"""
    class Meta:
        model = ProductionProgress
        fields = ['stage', 'description', 'monitoring_description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'monitoring_description': forms.TextInput(),
        }