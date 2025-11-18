from django.shortcuts import render, redirect
from django.contrib import messages
from .models import QuotationRequest
from .forms import QuotationRequestForm

def quotation_home(request):
    """报价模块首页"""
    return render(request, 'quotation/home.html')

def quotation_request(request):
    """报价请求表单"""
    if request.method == 'POST':
        form = QuotationRequestForm(request.POST, request.FILES)
        if form.is_valid():
            quotation = form.save()
            # 重定向到结果页面，传入报价ID
            return redirect('quotation:result', quotation_id=quotation.id)
    else:
        form = QuotationRequestForm()
    
    return render(request, 'quotation/request.html', {'form': form})

def quotation_result(request, quotation_id):
    """报价结果页面"""
    try:
        quotation = QuotationRequest.objects.get(id=quotation_id)
        
        # 简单的价格计算逻辑（实际项目中应该更加复杂）
        base_prices = {
            'cnc_milling': 100,    # CNC铣削基础价格
            'cnc_turning': 80,     # CNC车削基础价格
            '3d_printing': 50,     # 3D打印基础价格
        }
        
        material_multipliers = {
            'aluminum': 1.0,       # 铝合金
            'steel': 1.5,          # 钢材
            'stainless_steel': 1.8, # 不锈钢
            'plastic': 0.8,        # 塑料
            'other': 1.2,          # 其他
        }
        
        # 计算预估价格
        base_price = base_prices.get(quotation.processing_type, 100)
        material_multiplier = material_multipliers.get(quotation.material, 1.0)
        quantity_factor = max(0.8, 100 / (quotation.quantity + 99))  # 数量折扣因子
        
        estimated_price = base_price * material_multiplier * quantity_factor * quotation.quantity
        
        # 设置价格区间（±20%）
        price_min = round(estimated_price * 0.8, 2)
        price_max = round(estimated_price * 1.2, 2)
        
        context = {
            'quotation': quotation,
            'price_min': price_min,
            'price_max': price_max,
        }
        return render(request, 'quotation/result.html', context)
    except QuotationRequest.DoesNotExist:
        messages.error(request, '未找到指定的报价请求')
        return redirect('quotation:home')