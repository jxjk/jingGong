from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse
from django.core.paginator import Paginator
from .models import QuotationRequest, QuotationAdjustmentFactor, DFMAnalysis
from .forms import QuotationAdjustmentFactorForm
import csv
from datetime import datetime, timedelta

def is_admin(user):
    return user.is_staff


@user_passes_test(is_admin)
def admin_dashboard(request):
    """管理员仪表盘"""
    total_quotes = QuotationRequest.objects.count()
    pending_quotes = QuotationRequest.objects.filter(is_processed=False).count()
    total_dfm_analyses = DFMAnalysis.objects.count()
    
    recent_quotes = QuotationRequest.objects.all().order_by('-created_at')[:5]
    
    return render(request, 'quotation/admin/dashboard.html', {
        'total_quotes': total_quotes,
        'pending_quotes': pending_quotes,
        'total_dfm_analyses': total_dfm_analyses,
        'recent_quotes': recent_quotes
    })


@user_passes_test(is_admin)
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


@user_passes_test(is_admin)
def quote_detail(request, quote_id):
    """报价详情"""
    quote = get_object_or_404(QuotationRequest, id=quote_id)
    context = {
        'quote': quote,
    }
    return render(request, 'quotation/admin/quote_detail.html', context)


@user_passes_test(is_admin)
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


@user_passes_test(is_admin)
def adjustment_factors(request):
    """报价调控因子列表"""
    factors = QuotationAdjustmentFactor.objects.all().order_by('name')
    context = {
        'factors': factors,
    }
    return render(request, 'quotation/admin/factors.html', context)


@user_passes_test(is_admin)
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


@user_passes_test(is_admin)
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


@user_passes_test(is_admin)
def dfm_analysis_list(request):
    """DFM分析列表"""
    analyses = DFMAnalysis.objects.all().order_by('-created_at')
    paginator = Paginator(analyses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'quotation/admin/dfm_analysis_list.html', {
        'page_obj': page_obj
    })


@user_passes_test(is_admin)
def dfm_analysis_detail(request, analysis_id):
    """DFM分析详情"""
    analysis = get_object_or_404(DFMAnalysis, id=analysis_id)
    return render(request, 'quotation/admin/dfm_analysis_detail.html', {
        'analysis': analysis
    })
