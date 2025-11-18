import os
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from .models import QuotationRequest
from .forms import QuotationRequestForm
from .cad_analyzer import CADModelAnalyzer

def quotation_home(request):
    """报价模块首页"""
    return render(request, 'quotation/home.html')

def quotation_request(request):
    """报价请求表单"""
    if request.method == 'POST':
        form = QuotationRequestForm(request.POST, request.FILES)
        if form.is_valid():
            quotation = form.save()
            
            # 如果上传了3D模型文件，则进行分析
            if quotation.model_file:
                try:
                    # 获取文件的绝对路径
                    file_path = quotation.model_file.path
                    
                    # 使用CAD分析器分析3D模型
                    analyzer = CADModelAnalyzer(file_path)
                    features = analyzer.analyze()
                    
                    # 更新报价请求对象
                    for key, value in features.items():
                        setattr(quotation, key, value)
                    
                    quotation.save()
                except Exception as e:
                    print(f"分析3D模型时出错: {e}")
            
            # 重定向到结果页面，传入报价ID
            return redirect('quotation:result', quotation_id=quotation.id)
    else:
        form = QuotationRequestForm()
    
    return render(request, 'quotation/request.html', {'form': form})

def quotation_result(request, quotation_id):
    """报价结果页面"""
    try:
        quotation = QuotationRequest.objects.get(id=quotation_id)
        
        # 基础价格参数
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
        
        # 基于3D模型特征的价格调整因子
        model_factor = 1.0
        
        # 体积因子（cm³）
        if quotation.volume:
            # 体积越大，材料成本越高
            model_factor *= (1 + quotation.volume / 1000.0)
        
        # 表面积因子（cm²）
        if quotation.surface_area:
            # 表面积越大，处理时间越长
            model_factor *= (1 + quotation.surface_area / 1000.0)
        
        # 复杂度因子
        if quotation.complexity_score:
            # 复杂度越高，加工难度越大
            model_factor *= (1 + quotation.complexity_score / 10.0)
        
        # 径长比因子（极端比例会增加加工难度）
        if quotation.max_aspect_ratio and quotation.max_aspect_ratio > 5:
            model_factor *= 1.2
        
        # 精度要求因子
        if '±0.01' in quotation.accuracy:
            model_factor *= 1.5
        elif '±0.05' in quotation.accuracy:
            model_factor *= 1.2
        elif '±0.1' in quotation.accuracy:
            model_factor *= 1.1
        
        # 最小拐角半径因子（半径越小，加工越困难）
        if quotation.min_radius and quotation.min_radius < 0.5:
            model_factor *= 1.3
            
        # 加工难度因子
        if quotation.machining_difficulty:
            model_factor *= (1 + quotation.machining_difficulty / 10.0)
        
        estimated_price = base_price * material_multiplier * quantity_factor * quotation.quantity * model_factor
        
        # 设置价格区间（±10%，更加精确）
        price_min = round(estimated_price * 0.9, 2)
        price_max = round(estimated_price * 1.1, 2)
        
        context = {
            'quotation': quotation,
            'price_min': price_min,
            'price_max': price_max,
        }
        return render(request, 'quotation/result.html', context)
    except QuotationRequest.DoesNotExist:
        messages.error(request, '未找到指定的报价请求')
        return redirect('quotation:home')