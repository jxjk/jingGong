from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Count
from django.contrib import messages
from .models import QuotationRequest, QuotationAdjustmentFactor
from .forms import QuotationAdjustmentFactorForm
import csv
from datetime import datetime, timedelta


@staff_member_required
def admin_dashboard(request):
    """管理员仪表板"""
    # 获取统计数据
    total_quotes = QuotationRequest.objects.count()
    processed_quotes = QuotationRequest.objects.filter(is_processed=True).count()
    pending_quotes = QuotationRequest.objects.filter(is_processed=False).count()
    
    # 最近7天的报价统计
    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_quotes = QuotationRequest.objects.filter(
        created_at__gte=seven_days_ago
    ).extra(select={'date': 'date(created_at)'}).values('date').annotate(count=Count('id'))
    
    # 按加工类型统计
    quotes_by_type = QuotationRequest.objects.values('processing_type').annotate(count=Count('id'))
    
    context = {
        'total_quotes': total_quotes,
        'processed_quotes': processed_quotes,
        'pending_quotes': pending_quotes,
        'recent_quotes': recent_quotes,
        'quotes_by_type': quotes_by_type,
    }
    return render(request, 'quotation/admin/dashboard.html', context)


@staff_member_required
def quote_list(request):
    """报价列表"""
    quotes = QuotationRequest.objects.all().order_by('-created_at')
    
    # 搜索功能
    search_query = request.GET.get('search')
    if search_query:
        quotes = quotes.filter(
            name__icontains=search_query
        ) | quotes.filter(
            email__icontains=search_query
        ) | quotes.filter(
            phone__icontains=search_query
        )
    
    context = {
        'quotes': quotes,
        'search_query': search_query,
    }
    return render(request, 'quotation/admin/quote_list.html', context)


@staff_member_required
def quote_detail(request, quote_id):
    """报价详情"""
    quote = get_object_or_404(QuotationRequest, id=quote_id)
    context = {
        'quote': quote,
    }
    return render(request, 'quotation/admin/quote_detail.html', context)


@staff_member_required
def export_quotes_csv(request):
    """导出报价数据为CSV格式"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="quotes_export.csv"'
    
    writer = csv.writer(response)
    # 写入表头
    writer.writerow([
        'ID', '姓名', '邮箱', '电话', '加工类型', '材料', '数量', 
        '精度要求', '表面处理', '创建时间', '已处理', '体积(cm³)', 
        '表面积(cm²)', '复杂度评分', '加工难度评分'
    ])
    
    # 写入数据
    quotes = QuotationRequest.objects.all()
    for quote in quotes:
        writer.writerow([
            quote.id, quote.name, quote.email, quote.phone,
            quote.get_processing_type_display(), quote.get_material_display(), quote.quantity,
            quote.accuracy, quote.get_surface_treatment_display(),
            quote.created_at.strftime('%Y-%m-%d %H:%M:%S'), 
            '是' if quote.is_processed else '否',
            quote.volume or '', quote.surface_area or '', 
            quote.complexity_score or '', quote.machining_difficulty or ''
        ])
    
    return response


@staff_member_required
def adjustment_factors(request):
    """报价调控因子列表"""
    factors = QuotationAdjustmentFactor.objects.all().order_by('name')
    context = {
        'factors': factors,
    }
    return render(request, 'quotation/admin/factors.html', context)


@staff_member_required
def create_adjustment_factor(request):
    """创建报价调控因子"""
    if request.method == 'POST':
        form = QuotationAdjustmentFactorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '因子创建成功！')
            return redirect('quotation:admin_factors')
    else:
        form = QuotationAdjustmentFactorForm()
    
    context = {
        'form': form,
    }
    return render(request, 'quotation/admin/factor_form.html', context)


@staff_member_required
def edit_adjustment_factor(request, factor_id):
    """编辑报价调控因子"""
    factor = get_object_or_404(QuotationAdjustmentFactor, id=factor_id)
    
    if request.method == 'POST':
        form = QuotationAdjustmentFactorForm(request.POST, instance=factor)
        if form.is_valid():
            form.save()
            messages.success(request, '因子更新成功！')
            return redirect('quotation:admin_factors')
    else:
        form = QuotationAdjustmentFactorForm(instance=factor)
    
    context = {
        'form': form,
    }
    return render(request, 'quotation/admin/factor_form.html', context)