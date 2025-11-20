from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import Order, OrderStatusHistory, ProductionProgress, Notification


def is_admin(user):
    """检查用户是否为管理员"""
    return user.is_staff


@user_passes_test(is_admin)
def admin_order_list(request):
    """管理员订单列表"""
    # 获取所有订单，支持搜索
    orders = Order.objects.all().order_by('-created_at')
    
    # 搜索功能
    search_query = request.GET.get('search', '')
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(customer_email__icontains=search_query) |
            Q(product_name__icontains=search_query)
        )
    
    # 状态筛选
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # 分页处理
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': Order.ORDER_STATUS_CHOICES,
    }
    return render(request, 'orders/admin/order_list.html', context)


@user_passes_test(is_admin)
def admin_order_detail(request, order_id):
    """管理员订单详情"""
    order = get_object_or_404(Order, id=order_id)
    status_history = order.status_history.all()
    production_progress = order.production_progress.all()
    notifications = order.notifications.all()
    
    context = {
        'order': order,
        'status_history': status_history,
        'production_progress': production_progress,
        'notifications': notifications,
    }
    return render(request, 'orders/admin/order_detail.html', context)


@user_passes_test(is_admin)
def admin_update_order_status(request, order_id):
    """管理员更新订单状态"""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        if new_status in dict(Order.ORDER_STATUS_CHOICES):
            # 更新订单状态
            old_status = order.status
            order.status = new_status
            order.save()
            
            # 创建状态历史记录
            OrderStatusHistory.objects.create(
                order=order,
                status=new_status,
                operator=request.user.get_full_name() or request.user.username,
                notes=notes
            )
            
            # 创建通知给客户
            Notification.objects.create(
                order=order,
                title=f'订单状态更新 - {order.get_status_display_chinese()}',
                content=f'您的订单 {order.order_number} 状态已更新为 {order.get_status_display_chinese()}'
            )
            
            messages.success(request, f'订单状态已从 {dict(Order.ORDER_STATUS_CHOICES)[old_status]} 更新为 {dict(Order.ORDER_STATUS_CHOICES)[new_status]}')
        else:
            messages.error(request, '无效的订单状态')
    
    return redirect('orders:admin_order_detail', order_id=order.id)


@user_passes_test(is_admin)
def admin_add_production_progress(request, order_id):
    """管理员添加生产进度"""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        stage = request.POST.get('stage')
        description = request.POST.get('description')
        
        # 创建生产进度记录
        progress = ProductionProgress.objects.create(
            order=order,
            stage=stage,
            description=description
        )
        
        # 创建通知给客户
        Notification.objects.create(
            order=order,
            title='生产进度更新',
            content=f'您的订单 {order.order_number} 在 {stage} 阶段有新的进度更新'
        )
        
        messages.success(request, '生产进度已添加')
    
    return redirect('orders:admin_order_detail', order_id=order.id)


@user_passes_test(is_admin)
def admin_update_production_progress(request, progress_id):
    """管理员更新生产进度"""
    progress = get_object_or_404(ProductionProgress, id=progress_id)
    
    if request.method == 'POST':
        completed = request.POST.get('completed') == 'on'
        monitoring_description = request.POST.get('monitoring_description', '')
        
        progress.is_completed = completed
        if completed and not progress.completed_at:
            progress.completed_at = timezone.now()
        elif not completed:
            progress.completed_at = None
            
        progress.monitoring_description = monitoring_description
        progress.save()
        
        # 如果已完成，创建通知给客户
        if completed:
            Notification.objects.create(
                order=progress.order,
                title='生产阶段完成',
                content=f'您的订单 {progress.order.order_number} 的 {progress.stage} 阶段已完成'
            )
            messages.success(request, f'生产阶段 {progress.stage} 已标记为完成')
        else:
            messages.success(request, f'生产阶段 {progress.stage} 状态已更新')
    
    return redirect('orders:admin_order_detail', order_id=progress.order.id)


@require_POST
@user_passes_test(is_admin)
def admin_send_notification(request, order_id):
    """管理员发送通知"""
    order = get_object_or_404(Order, id=order_id)
    
    title = request.POST.get('title')
    content = request.POST.get('content')
    
    if title and content:
        Notification.objects.create(
            order=order,
            title=title,
            content=content
        )
        messages.success(request, '通知已发送给客户')
    else:
        messages.error(request, '请填写标题和内容')
    
    return redirect('orders:admin_order_detail', order_id=order.id)