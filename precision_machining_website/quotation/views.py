import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from .models import QuotationRequest, QuotationAdjustmentFactor
from .forms import QuotationRequestForm
from .cad_analyzer import CADModelAnalyzer
import numpy as np

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
                    print(f"开始分析3D模型文件: {file_path}")
                    print(f"文件是否存在: {os.path.exists(file_path)}")
                    print(f"文件大小: {os.path.getsize(file_path) if os.path.exists(file_path) else 'N/A'}")
                    
                    # 使用CAD分析器分析3D模型
                    analyzer = CADModelAnalyzer(file_path)
                    features = analyzer.analyze()
                    print(f"分析完成，提取特征: {features}")
                    
                    # 更新报价请求对象
                    updated_fields = []
                    for key, value in features.items():
                        if hasattr(quotation, key):
                            setattr(quotation, key, value)
                            updated_fields.append(key)
                            print(f"设置字段 {key} = {value}")
                    
                    if updated_fields:
                        quotation.save()
                        print(f"成功更新字段: {updated_fields}")
                    else:
                        print("未找到可更新的字段")
                except Exception as e:
                    print(f"分析3D模型时出错: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 重定向到结果页面，传入报价ID
            return redirect('quotation:quotation_result', quotation_id=quotation.id)
    else:
        form = QuotationRequestForm()
    
    return render(request, 'quotation/request.html', {'form': form})

def quotation_result(request, quotation_id):
    """报价结果页面"""
    quotation = get_object_or_404(QuotationRequest, id=quotation_id)
    
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
    
    # 记录各个因子的详细信息
    factor_details = {
        'base_price': base_price,
        'material_multiplier': material_multiplier,
        'quantity_factor': quantity_factor,
        'quantity': quotation.quantity,
        'factors': []
    }
    
    # 体积因子（cm³）- 使用对数函数限制因子增长
    if quotation.volume:
        # 使用对数函数限制因子增长，避免大模型导致价格过高
        volume_factor = 1 + (np.log10(max(1, quotation.volume)) / 10.0)
        model_factor *= volume_factor
        factor_details['factors'].append({
            'name': '体积因子',
            'value': volume_factor,
            'description': f'体积: {quotation.volume:.2f} cm³'
        })
    
    # 表面积因子（cm²）- 使用对数函数限制因子增长
    if quotation.surface_area:
        # 使用对数函数限制因子增长，避免大模型导致价格过高
        surface_factor = 1 + (np.log10(max(1, quotation.surface_area)) / 10.0)
        model_factor *= surface_factor
        factor_details['factors'].append({
            'name': '表面积因子',
            'value': surface_factor,
            'description': f'表面积: {quotation.surface_area:.2f} cm²'
        })
    
    # 复杂度因子
    if quotation.complexity_score:
        complexity_factor = (1 + quotation.complexity_score / 10.0)
        model_factor *= complexity_factor
        factor_details['factors'].append({
            'name': '复杂度因子',
            'value': complexity_factor,
            'description': f'复杂度评分: {quotation.complexity_score}'
        })
    
    # 加工难度因子
    if quotation.machining_difficulty:
        difficulty_factor = (1 + quotation.machining_difficulty / 5.0)
        model_factor *= difficulty_factor
        factor_details['factors'].append({
            'name': '加工难度因子',
            'value': difficulty_factor,
            'description': f'加工难度评分: {quotation.machining_difficulty}'
        })
    
    # 最小拐角半径因子（越小越难加工）
    if quotation.min_radius and quotation.min_radius < 2.0:
        radius_factor = 1 + (2.0 - quotation.min_radius) / 2.0
        model_factor *= radius_factor
        factor_details['factors'].append({
            'name': '最小拐角因子',
            'value': radius_factor,
            'description': f'最小拐角半径: {quotation.min_radius:.2f} mm'
        })
    
    # 最小刀具直径因子（越小越难加工）
    if quotation.min_tool_diameter and quotation.min_tool_diameter < 3.0:
        tool_factor = 1 + (3.0 - quotation.min_tool_diameter) / 3.0
        model_factor *= tool_factor
        factor_details['factors'].append({
            'name': '刀具因子',
            'value': tool_factor,
            'description': f'最小刀具直径: {quotation.min_tool_diameter:.2f} mm'
        })
    
    # 径长比因子（越大越难加工）
    if quotation.max_aspect_ratio and quotation.max_aspect_ratio > 3.0:
        aspect_factor = 1 + (quotation.max_aspect_ratio - 3.0) / 10.0
        model_factor *= aspect_factor
        factor_details['factors'].append({
            'name': '径长比因子',
            'value': aspect_factor,
            'description': f'最大径长比: {quotation.max_aspect_ratio:.2f}'
        })
    
    # 应用管理员设置的调控因子
    adjustment_factors = QuotationAdjustmentFactor.objects.filter(is_active=True)
    adjustment_factor_value = 1.0
    if adjustment_factors.exists():
        for factor in adjustment_factors:
            adjustment_factor_value *= factor.value
            factor_details['factors'].append({
                'name': f'调控因子[{factor.name}]',
                'value': factor.value,
                'description': factor.description or f'调控因子: {factor.name}'
            })
    
    # 计算最终价格
    estimated_price = base_price * material_multiplier * quantity_factor * model_factor * adjustment_factor_value
    
    # 计算价格区间（±10%）
    price_min = estimated_price * 0.9
    price_max = estimated_price * 1.1
    
    # 保留两位小数
    estimated_price = round(estimated_price, 2)
    price_min = round(price_min, 2)
    price_max = round(price_max, 2)
    
    context = {
        'quotation': quotation,
        'estimated_price': estimated_price,
        'price_min': price_min,
        'price_max': price_max,
        'factor_details': factor_details,
    }
    
    return render(request, 'quotation/result.html', context)

def dfm_analysis(request):
    """DFM分析工具"""
    if request.method == 'POST':
        # 处理上传的3D模型文件
        model_file = request.FILES.get('model_file')
        if model_file:
            try:
                # 保存文件到临时位置
                temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
                os.makedirs(temp_dir, exist_ok=True)
                temp_file_path = os.path.join(temp_dir, model_file.name)
                
                with open(temp_file_path, 'wb+') as destination:
                    for chunk in model_file.chunks():
                        destination.write(chunk)
                
                # 分析模型
                analyzer = CADModelAnalyzer(temp_file_path)
                features = analyzer.analyze()
                
                # 进行DFM分析
                dfm_recommendations = _generate_dfm_recommendations(features)
                
                # 清理临时文件
                os.remove(temp_file_path)
                
                context = {
                    'features': features,
                    'recommendations': dfm_recommendations,
                    'analysis_complete': True
                }
                return render(request, 'quotation/dfm_analysis.html', context)
            except Exception as e:
                messages.error(request, f'分析过程中出错: {str(e)}')
        else:
            messages.error(request, '请上传一个3D模型文件')
    
    return render(request, 'quotation/dfm_analysis.html')

def _generate_dfm_recommendations(features):
    """根据模型特征生成DFM建议"""
    recommendations = []
    
    # 检查最小拐角半径
    min_radius = features.get('min_radius')
    if min_radius is not None:
        if min_radius < 0.5:
            recommendations.append({
                'type': 'warning',
                'title': '极小拐角半径',
                'description': f'检测到最小拐角半径为 {min_radius:.2f}mm，这可能会导致刀具磨损加剧或加工困难。',
                'suggestion': '建议增加拐角半径至0.5mm以上，以提高加工效率和刀具寿命。'
            })
        elif min_radius < 1.0:
            recommendations.append({
                'type': 'info',
                'title': '较小拐角半径',
                'description': f'检测到最小拐角半径为 {min_radius:.2f}mm，属于较小半径。',
                'suggestion': '考虑增加拐角半径至1mm以上，以降低加工难度。'
            })
    
    # 检查最小刀具直径
    min_tool_diameter = features.get('min_tool_diameter')
    if min_tool_diameter is not None:
        if min_tool_diameter < 1.0:
            recommendations.append({
                'type': 'warning',
                'title': '极小刀具直径需求',
                'description': f'检测到需要使用直径小于 {min_tool_diameter:.2f}mm 的刀具进行加工。',
                'suggestion': '小直径刀具易断且成本高，建议优化设计避免过小的结构。'
            })
        elif min_tool_diameter < 2.0:
            recommendations.append({
                'type': 'info',
                'title': '较小刀具直径需求',
                'description': f'检测到需要使用直径小于 {min_tool_diameter:.2f}mm 的刀具进行加工。',
                'suggestion': '小直径刀具加工效率较低，考虑是否可以调整设计。'
            })
    
    # 检查最大径长比
    max_aspect_ratio = features.get('max_aspect_ratio')
    if max_aspect_ratio is not None and max_aspect_ratio > 5.0:
        recommendations.append({
            'type': 'warning',
            'title': '高径长比特征',
            'description': f'检测到特征的径长比达到 {max_aspect_ratio:.2f}，属于高径长比结构。',
            'suggestion': '高径长比特征容易导致振动和变形，建议增加支撑结构或优化几何形状。'
        })
    
    # 检查复杂度评分
    complexity_score = features.get('complexity_score')
    if complexity_score is not None:
        if complexity_score > 8.0:
            recommendations.append({
                'type': 'warning',
                'title': '高复杂度设计',
                'description': f'模型复杂度评分为 {complexity_score:.2f}（满分10分），属于高复杂度设计。',
                'suggestion': '高复杂度会增加加工难度和成本，考虑是否可以简化设计。'
            })
        elif complexity_score > 5.0:
            recommendations.append({
                'type': 'info',
                'title': '中等复杂度设计',
                'description': f'模型复杂度评分为 {complexity_score:.2f}（满分10分）。',
                'suggestion': '中等复杂度设计，注意加工过程中的质量控制。'
            })
    
    # 检查加工难度评分
    machining_difficulty = features.get('machining_difficulty')
    if machining_difficulty is not None:
        if machining_difficulty > 8.0:
            recommendations.append({
                'type': 'warning',
                'title': '高加工难度',
                'description': f'加工难度评分为 {machining_difficulty:.2f}（满分10分），属于高难度加工。',
                'suggestion': '高难度加工需要更专业的设备和工艺，可能导致成本显著增加。'
            })
        elif machining_difficulty > 5.0:
            recommendations.append({
                'type': 'info',
                'title': '中等加工难度',
                'description': f'加工难度评分为 {machining_difficulty:.2f}（满分10分）。',
                'suggestion': '中等加工难度，需要经验丰富的操作人员。'
            })
    
    return recommendations
