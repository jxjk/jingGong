from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views.generic import UpdateView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Q
from decimal import Decimal
from .models import QuotationRequest
from .forms import QuotationUpdateForm


@staff_member_required
def admin_quotation_detail(request, pk):
    """管理员查看和编辑报价详情"""
    quotation = get_object_or_404(QuotationRequest, pk=pk)
    original_price = quotation.final_price
    
    if request.method == 'POST':
        form = QuotationUpdateForm(request.POST, instance=quotation)
        if form.is_valid():
            # 保存修改
            updated_quotation = form.save()
            messages.success(request, f'报价已更新，最终价格从 ¥{original_price} 调整为 ¥{updated_quotation.final_price}')
            return redirect('quotation:admin_quotation_detail', pk=quotation.pk)
    else:
        form = QuotationUpdateForm(instance=quotation)
    
    context = {
        'quotation': quotation,
        'form': form,
        'is_admin': True,  # 标识管理员视图
    }
    return render(request, 'quotation/admin_quotation_detail.html', context)


@staff_member_required
def update_profit_margin(request, pk):
    """管理员更新利润率的API接口"""
    if request.method == 'POST':
        quotation = get_object_or_404(QuotationRequest, pk=pk)
        try:
            profit_margin = Decimal(request.POST.get('profit_margin', 0))
            # 设置利润率
            quotation.profit_margin = profit_margin
            # 重新计算价格
            final_price = quotation.calculate_final_price_with_profit()
            quotation.final_price = final_price
            quotation.save()
            
            return JsonResponse({
                'success': True,
                'new_price': float(quotation.final_price),
                'profit_amount': float(quotation.profit_amount) if quotation.profit_amount else 0
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@staff_member_required
def admin_quotation_list(request):
    """管理员查看所有报价列表"""
    quotations = QuotationRequest.objects.all().order_by('-created_at')
    
    # 支持搜索功能
    search_query = request.GET.get('search')
    if search_query:
        quotations = quotations.filter(
            Q(id__icontains=search_query) |
            Q(name__icontains=search_query) |
            Q(part_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # 支持状态筛选
    status_filter = request.GET.get('status')
    if status_filter:
        quotations = quotations.filter(status=status_filter)
    
    context = {
        'quotations': quotations,
        'status_choices': QuotationRequest.QUOTATION_STATUS,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    return render(request, 'quotation/admin_quotation_list.html', context)


@staff_member_required
def admin_dashboard(request):
    """管理员仪表板"""
    # 获取统计信息
    total_quotations = QuotationRequest.objects.count()
    pending_quotations = QuotationRequest.objects.filter(status='pending').count()
    quoted_quotations = QuotationRequest.objects.filter(status='quoted').count()
    processing_quotations = QuotationRequest.objects.filter(status='processing').count()
    
    context = {
        'total_quotations': total_quotations,
        'pending_quotations': pending_quotations,
        'quoted_quotations': quoted_quotations,
        'processing_quotations': processing_quotations,
    }
    return render(request, 'quotation/admin_dashboard.html', context)


@staff_member_required
def quote_list(request):
    """报价列表（别名函数）"""
    return admin_quotation_list(request)


@staff_member_required
def quotation_detail(request, quote_id):
    """报价详情（别名函数）"""
    return admin_quotation_detail(request, quote_id)


# 为了保持代码完整性，我们需要添加所有URL中引用的函数
@staff_member_required
def adjustment_factors(request):
    """报价调控因子管理页面"""
    from .models import QuotationAdjustmentFactor
    factors = QuotationAdjustmentFactor.objects.all()
    context = {
        'factors': factors
    }
    return render(request, 'quotation/adjustment_factors.html', context)


@staff_member_required
def create_adjustment_factor(request):
    """创建报价调控因子"""
    pass  # 实现将取决于具体需求


@staff_member_required
def edit_adjustment_factor(request, factor_id):
    """编辑报价调控因子"""
    pass  # 实现将取决于具体需求


@staff_member_required
def dfm_analysis_list(request):
    """DFM分析列表"""
    from .models import DFMAnalysis
    analyses = DFMAnalysis.objects.all().order_by('-created_at')
    context = {
        'analyses': analyses
    }
    return render(request, 'quotation/dfm_analysis_list.html', context)


@staff_member_required
def dfm_analysis_detail(request, analysis_id):
    """DFM分析详情"""
    from .models import DFMAnalysis
    analysis = get_object_or_404(DFMAnalysis, id=analysis_id)
    context = {
        'analysis': analysis
    }
    return render(request, 'quotation/dfm_analysis_detail.html', context)


@staff_member_required
def export_quotes_csv(request):
    """导出报价为CSV"""
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="quotations.csv"'
    response['Access-Control-Allow-Origin'] = '*'
    
    writer = csv.writer(response)
    writer.writerow(['ID', '姓名', '邮箱', '零件名称', '加工类型', '材料', '数量', '最终价格', '状态', '创建时间'])
    
    quotations = QuotationRequest.objects.all()
    for quote in quotations:
        writer.writerow([
            quote.id,
            quote.name,
            quote.email,
            quote.part_name,
            quote.get_processing_type_display(),
            quote.get_material_display(),
            quote.quantity,
            quote.final_price or quote.estimated_price,
            quote.get_status_display(),
            quote.created_at
        ])
    
    return response