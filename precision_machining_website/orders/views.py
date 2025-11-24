from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.crypto import get_random_string
from .models import Order, OrderStatusHistory, ProductionProgress, Notification
from .decorators import customer_required
from quotation.models import QuotationRequest


@login_required
@customer_required
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
@customer_required
def order_detail(request, order_id):
    """订单详情页面"""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    status_history = order.status_history.all().order_by('-timestamp')
    production_progress = order.production_progress.all().order_by('-started_at')
    notifications = order.notifications.all().order_by('-created_at')
    
    context = {
        'order': order,
        'status_history': status_history,
        'production_progress': production_progress,
        'notifications': notifications,
    }
    return render(request, 'orders/order_detail.html', context)


@login_required
@customer_required
def create_order_from_quotation(request, quotation_id):
    """从已确认报价创建订单"""
    quotation = get_object_or_404(QuotationRequest, id=quotation_id)
    
    # 检查报价状态是否为已报价
    if quotation.status != 'quoted':
        messages.error(request, '该报价尚未完成审核，无法创建订单。')
        return redirect('quotation:quotation_result', quotation_id=quotation.id)
    
    # 检查是否已经为该报价创建了订单
    existing_order = Order.objects.filter(quotation_request=quotation, customer=request.user).first()
    
    if existing_order:
        messages.info(request, '该报价已创建订单，正在为您跳转到订单详情。')
        return redirect('orders:order_detail', order_id=existing_order.id)
    
    if request.method == 'POST':
        # 创建订单
        order_number = f"ORD{timezone.now().strftime('%Y%m%d')}{get_random_string(6, '0123456789')}"
        
        # 使用报价中的最终价格
        unit_price = quotation.final_price if quotation.final_price else quotation.estimated_price
        total_price = unit_price * quotation.quantity if unit_price else 0
        
        order = Order.objects.create(
            order_number=order_number,
            customer=request.user,
            quotation_request=quotation,
            product_name=f"{quotation.get_processing_type_display()}加工服务",
            product_description=f"材料: {quotation.get_material_display()}\n数量: {quotation.quantity}\n精度要求: {quotation.accuracy}\n表面处理: {quotation.get_surface_treatment_display()}\n附加说明: {quotation.description}",
            quantity=quotation.quantity,
            unit_price=unit_price or 0,
            total_price=total_price or 0,
            customer_name=quotation.name,
            customer_email=quotation.email,
            customer_phone=quotation.phone,
            shipping_address=request.POST.get('shipping_address', ''),
            shipping_contact=request.POST.get('shipping_contact', quotation.name),
            shipping_phone=request.POST.get('shipping_phone', quotation.phone),
            notes=f"基于报价 #{quotation.id} 创建"
        )
        
        # 更新报价状态为已确认
        quotation.status = 'confirmed'
        quotation.save()
        
        # 创建初始状态历史记录
        OrderStatusHistory.objects.create(
            order=order,
            status='pending_review',
            operator='系统',
            notes='订单已创建，等待审核'
        )
        
        messages.success(request, f'订单 {order_number} 创建成功！')
        return redirect('orders:order_detail', order_id=order.id)
    
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
@customer_required
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
@customer_required
def mark_notification_read(request, notification_id):
    """标记通知为已读"""
    notification = get_object_or_404(Notification, id=notification_id, order__customer=request.user)
    notification.is_read = True
    notification.read_at = timezone.now()
    notification.save()
    
    return JsonResponse({'success': True})


@login_required
@customer_required
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