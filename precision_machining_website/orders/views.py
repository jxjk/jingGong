from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Order, OrderStatusHistory, ProductionProgress, Notification
from quotation.models import QuotationRequest


@login_required
def order_list(request):
    """订单列表页面"""
    # 获取当前用户的订单
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    
    # 分页处理
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'orders/order_list.html', context)


@login_required
def order_detail(request, order_id):
    """订单详情页面"""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    status_history = order.status_history.all()
    production_progress = order.production_progress.all()
    notifications = order.notifications.all()
    
    context = {
        'order': order,
        'status_history': status_history,
        'production_progress': production_progress,
        'notifications': notifications,
    }
    return render(request, 'orders/order_detail.html', context)


@login_required
def create_order_from_quotation(request, quotation_id):
    """从报价创建订单"""
    # 这里应该实现从报价创建订单的逻辑
    # 由于这是一个示例，我们只返回一个简单的页面
    quotation = get_object_or_404(QuotationRequest, id=quotation_id)
    
    context = {
        'quotation': quotation,
    }
    return render(request, 'orders/create_order.html', context)


def order_status_api(request, order_id):
    """获取订单状态的API接口"""
    order = get_object_or_404(Order, id=order_id)
    
    # 检查用户权限
    if request.user != order.customer and not request.user.is_staff:
        return JsonResponse({'error': '权限不足'}, status=403)
    
    data = {
        'order_id': order.id,
        'order_number': order.order_number,
        'status': order.status,
        'status_display': order.get_status_display_chinese(),
        'updated_at': order.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
    }
    
    return JsonResponse(data)


@login_required
def notification_list(request):
    """通知列表"""
    notifications = Notification.objects.filter(order__customer=request.user).order_by('-created_at')
    
    # 分页处理
    paginator = Paginator(notifications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'orders/notification_list.html', context)


@require_POST
@login_required
def mark_notification_read(request, notification_id):
    """标记通知为已读"""
    notification = get_object_or_404(Notification, id=notification_id, order__customer=request.user)
    notification.is_read = True
    notification.read_at = timezone.now()
    notification.save()
    
    return JsonResponse({'success': True})


@login_required
def production_monitoring(request, order_id):
    """生产监控页面"""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    
    # 获取生产进度信息
    progress_items = order.production_progress.filter(is_completed=False)
    
    context = {
        'order': order,
        'progress_items': progress_items,
    }
    return render(request, 'orders/production_monitoring.html', context)