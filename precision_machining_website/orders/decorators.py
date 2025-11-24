from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from functools import wraps
from .models import Order


def customer_required(view_func):
    """
    装饰器：确保只有订单的创建者（客户）可以访问特定的订单页面
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 确保用户已登录
        if not request.user.is_authenticated:
            return login_required(view_func)(request, *args, **kwargs)
        
        # 检查用户是否为管理员
        if request.user.is_staff:
            messages.error(request, '管理员无法访问客户订单页面，请使用管理后台功能。')
            return redirect('orders:admin_order_list')
        
        # 检查订单是否属于当前用户
        order_id = kwargs.get('order_id')
        if order_id:
            order = get_object_or_404(Order, id=order_id)
            if order.customer != request.user:
                messages.error(request, '您没有权限访问该订单。')
                return redirect('orders:order_list')
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def admin_required(view_func):
    """
    装饰器：确保只有管理员可以访问管理后台功能
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 确保用户已登录
        if not request.user.is_authenticated:
            return login_required(view_func)(request, *args, **kwargs)
        
        # 检查用户是否为管理员
        if not request.user.is_staff:
            messages.error(request, '您没有权限访问管理后台。')
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view