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
        
        # 记录各个因子的详细信息
        factor_details = {
            'base_price': base_price,
            'material_multiplier': material_multiplier,
            'quantity_factor': quantity_factor,
            'quantity': quotation.quantity,
            'factors': []
        }
        
        # 体积因子（cm³）
        if quotation.volume:
            volume_factor = (1 + quotation.volume / 1000.0)
            model_factor *= volume_factor
            factor_details['factors'].append({
                'name': '体积因子',
                'value': quotation.volume,
                'calculation': f"1 + {quotation.volume} / 1000.0 = {volume_factor:.4f}"
            })
        else:
            factor_details['factors'].append({
                'name': '体积因子',
                'value': 'N/A',
                'calculation': '未提供'
            })
        
        # 表面积因子（cm²）
        if quotation.surface_area:
            surface_area_factor = (1 + quotation.surface_area / 1000.0)
            model_factor *= surface_area_factor
            factor_details['factors'].append({
                'name': '表面积因子',
                'value': quotation.surface_area,
                'calculation': f"1 + {quotation.surface_area} / 1000.0 = {surface_area_factor:.4f}"
            })
        else:
            factor_details['factors'].append({
                'name': '表面积因子',
                'value': 'N/A',
                'calculation': '未提供'
            })
        
        # 复杂度因子
        if quotation.complexity_score:
            complexity_factor = (1 + quotation.complexity_score / 10.0)
            model_factor *= complexity_factor
            factor_details['factors'].append({
                'name': '复杂度因子',
                'value': quotation.complexity_score,
                'calculation': f"1 + {quotation.complexity_score} / 10.0 = {complexity_factor:.4f}"
            })
        else:
            factor_details['factors'].append({
                'name': '复杂度因子',
                'value': 'N/A',
                'calculation': '未提供'
            })
        
        # 径长比因子（极端比例会增加加工难度）
        if quotation.max_aspect_ratio and quotation.max_aspect_ratio > 5:
            aspect_ratio_factor = 1.2
            model_factor *= aspect_ratio_factor
            factor_details['factors'].append({
                'name': '径长比因子',
                'value': quotation.max_aspect_ratio,
                'calculation': f"大于5，因子 = {aspect_ratio_factor}"
            })
        elif quotation.max_aspect_ratio:
            factor_details['factors'].append({
                'name': '径长比因子',
                'value': quotation.max_aspect_ratio,
                'calculation': f"小于等于5，因子 = 1.0"
            })
        else:
            factor_details['factors'].append({
                'name': '径长比因子',
                'value': 'N/A',
                'calculation': '未提供'
            })
        
        # 精度要求因子
        precision_factor = 1.0
        if '±0.01' in quotation.accuracy:
            precision_factor = 1.5
        elif '±0.05' in quotation.accuracy:
            precision_factor = 1.2
        elif '±0.1' in quotation.accuracy:
            precision_factor = 1.1
            
        if precision_factor > 1.0:
            model_factor *= precision_factor
            factor_details['factors'].append({
                'name': '精度因子',
                'value': quotation.accuracy,
                'calculation': f"因子 = {precision_factor}"
            })
        else:
            factor_details['factors'].append({
                'name': '精度因子',
                'value': quotation.accuracy,
                'calculation': f"因子 = 1.0"
            })
        
        # 最小拐角半径因子（半径越小，加工越困难）
        if quotation.min_radius and quotation.min_radius < 0.5:
            radius_factor = 1.3
            model_factor *= radius_factor
            factor_details['factors'].append({
                'name': '最小拐角半径因子',
                'value': quotation.min_radius,
                'calculation': f"小于0.5，因子 = {radius_factor}"
            })
        elif quotation.min_radius:
            factor_details['factors'].append({
                'name': '最小拐角半径因子',
                'value': quotation.min_radius,
                'calculation': f"大于等于0.5，因子 = 1.0"
            })
        else:
            factor_details['factors'].append({
                'name': '最小拐角半径因子',
                'value': 'N/A',
                'calculation': '未提供'
            })
            
        # 加工难度因子
        if quotation.machining_difficulty:
            difficulty_factor = (1 + quotation.machining_difficulty / 10.0)
            model_factor *= difficulty_factor
            factor_details['factors'].append({
                'name': '加工难度因子',
                'value': quotation.machining_difficulty,
                'calculation': f"1 + {quotation.machining_difficulty} / 10.0 = {difficulty_factor:.4f}"
            })
        else:
            factor_details['factors'].append({
                'name': '加工难度因子',
                'value': 'N/A',
                'calculation': '未提供'
            })
        
        # 调试信息：打印计算参数
        print(f"报价ID {quotation_id} 的计算参数:")
        print(f"  基础价格: {base_price}")
        print(f"  材料系数: {material_multiplier}")
        print(f"  数量因子: {quantity_factor}")
        print(f"  数量: {quotation.quantity}")
        print(f"  模型因子: {model_factor}")
        print(f"  是否有模型文件: {bool(quotation.model_file)}")
        print(f"  体积: {quotation.volume}")
        print(f"  表面积: {quotation.surface_area}")
        print(f"  复杂度评分: {quotation.complexity_score}")
        
        estimated_price = base_price * material_multiplier * quantity_factor * quotation.quantity * model_factor
        
        # 设置价格区间（±10%，更加精确）
        price_min = round(estimated_price * 0.9, 2)
        price_max = round(estimated_price * 1.1, 2)
        
        context = {
            'quotation': quotation,
            'price_min': price_min,
            'price_max': price_max,
            'factor_details': factor_details  # 添加详细的因子信息到上下文中
        }
        return render(request, 'quotation/result.html', context)
    except QuotationRequest.DoesNotExist:
        messages.error(request, '未找到指定的报价请求')
        return redirect('quotation:home')