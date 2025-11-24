import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods, require_POST
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import QuotationRequest, QuotationAdjustmentFactor
from .forms import QuotationRequestForm
from .cad_analyzer import CADModelAnalyzer
from orders.models import Order
from orders.decorators import customer_required
import numpy as np
import json
import uuid


def quotation_home(request):
    """报价模块首页"""
    # 获取当前用户的报价请求（如果用户已登录）
    user_quotations = None
    if request.user.is_authenticated:
        user_quotations = QuotationRequest.objects.filter(
            customer=request.user
        ).order_by('-created_at')[:5]  # 获取最近5个报价请求
    
    context = {
        'user_quotations': user_quotations,
    }
    return render(request, 'quotation/home.html', context)


def quotation_request(request):
    """报价请求表单"""
    if request.method == 'POST':
        form = QuotationRequestForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            quotation = form.save(commit=False)
            
            # 如果用户已登录，设置用户关联和姓名
            if request.user.is_authenticated:
                quotation.customer = request.user
                # 确保姓名与用户名一致
                quotation.name = request.user.get_full_name() or request.user.username
                # 但可以确保邮箱与登录用户一致
                if not quotation.email:
                    quotation.email = request.user.email
            
            # 保存报价请求
            quotation.save()
            
            # 设置初始状态
            quotation.status = 'pending'
            quotation.save()
            
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
        # 如果用户已登录，预填充邮箱
        initial_data = {}
        if request.user.is_authenticated:
            initial_data['email'] = request.user.email
        
        form = QuotationRequestForm(initial=initial_data, user=request.user)
    
    return render(request, 'quotation/request.html', {'form': form})


def calculate_material_removal_factor(quotation):
    """
    计算材料去除率因子
    基于模型特征估算材料去除效率，影响最终报价
    """
    # 默认因子为1.0（无影响）
    factor = 1.0
    
    # 只有当所有必要参数都存在时才计算因子
    if all([quotation.volume, quotation.bounding_box_length, quotation.bounding_box_width, quotation.bounding_box_height]):
        # 计算包围盒体积（立方毫米）
        box_volume = quotation.bounding_box_length * quotation.bounding_box_width * quotation.bounding_box_height
        
        # 转换为立方厘米（因为1cm³ = 1000mm³）
        box_volume_cm3 = box_volume / 1000.0
        
        # 计算材料去除量（包围盒体积 - 模型体积）
        material_removed = box_volume_cm3 - quotation.volume
        
        # 如果材料去除量为正数，则计算因子
        if material_removed > 0:
            # 使用对数函数计算因子，避免极端值
            # 去除量越大，因子越小（效率越高）
            factor = max(0.5, min(2.0, 2.0 - (np.log10(max(1, material_removed)) / 5.0)))
    
    return factor


def quotation_result(request, quotation_id):
    """报价结果页面"""
    quotation = get_object_or_404(QuotationRequest, id=quotation_id)
    
    # 检查用户权限 - 用户可以查看自己的报价或管理员可以查看所有报价
    if (request.user.is_authenticated and 
        (quotation.customer == request.user or quotation.email == request.user.email or request.user.is_staff)):
        # 用户有权查看此报价
        pass
    elif not request.user.is_authenticated:
        # 未登录用户可以查看报价，但提示登录以获取完整功能
        pass
    else:
        messages.error(request, '您没有权限查看此报价。')
        return redirect('quotation:quotation_home')
    
    # 如果报价状态是待处理，更新为处理中
    if quotation.status == 'pending' and (not request.user.is_authenticated or 
                                          quotation.email == request.user.email or
                                          quotation.customer == request.user):
        quotation.status = 'processing'
        quotation.save()
    
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
            'description': f'模型体积: {quotation.volume:.2f} cm³'
        })
    
    # 表面积因子（cm²）
    if quotation.surface_area:
        surface_factor = 1 + (quotation.surface_area / 1000.0)
        model_factor *= surface_factor
        factor_details['factors'].append({
            'name': '表面积因子',
            'value': surface_factor,
            'description': f'表面积: {quotation.surface_area:.2f} cm²'
        })
    
    # 复杂度因子
    if quotation.complexity_score:
        # 复杂度评分越高，加工难度越大，价格越高
        complexity_factor = 1 + (quotation.complexity_score / 10.0)
        model_factor *= complexity_factor
        factor_details['factors'].append({
            'name': '复杂度因子',
            'value': complexity_factor,
            'description': f'复杂度评分: {quotation.complexity_score:.1f}/5'
        })
    
    # 径长比因子
    if quotation.max_aspect_ratio and quotation.max_aspect_ratio > 1.0:
        # 径长比越大，加工难度越大
        aspect_factor = min(2.0, 1 + (quotation.max_aspect_ratio / 20.0))
        model_factor *= aspect_factor
        factor_details['factors'].append({
            'name': '径长比因子',
            'value': aspect_factor,
            'description': f'最大径长比: {quotation.max_aspect_ratio:.2f}'
        })
    
    # 材料去除率因子（基于模型特征估算）
    material_removal_factor = calculate_material_removal_factor(quotation)
    if material_removal_factor != 1.0:
        model_factor *= material_removal_factor
        factor_details['factors'].append({
            'name': '材料去除率因子',
            'value': material_removal_factor,
            'description': '基于模型几何特征估算材料去除效率'
        })
    
    # 最终价格计算
    estimated_price = base_price * material_multiplier * quantity_factor * model_factor
    
    # 价格区间（±10%）
    price_min = estimated_price * 0.9
    price_max = estimated_price * 1.1
    
    # 更新报价对象的预估价格
    if not quotation.estimated_price:
        quotation.estimated_price = estimated_price
        quotation.save()
    
    context = {
        'quotation': quotation,
        'estimated_price': estimated_price,
        'price_min': price_min,
        'price_max': price_max,
        'factor_details': factor_details,
    }
    
    return render(request, 'quotation/result.html', context)


@login_required
def user_quotation_list(request):
    """用户报价列表"""
    # 获取当前用户的所有报价请求
    quotations = QuotationRequest.objects.filter(customer=request.user).order_by('-created_at')
    
    # 状态选项用于筛选
    status_choices = QuotationRequest.QUOTATION_STATUS
    
    # 状态筛选
    status_filter = request.GET.get('status')
    if status_filter:
        quotations = quotations.filter(status=status_filter)
    
    # 搜索功能
    search_query = request.GET.get('search')
    if search_query:
        quotations = quotations.filter(
            Q(id__icontains=search_query) |
            Q(part_name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # 分页
    paginator = Paginator(quotations, 10)  # 每页显示10个
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_choices': status_choices,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    return render(request, 'quotation/user_quotation_list.html', context)


@login_required
def delete_quotation(request, quotation_id):
    """删除报价"""
    quotation = get_object_or_404(QuotationRequest, id=quotation_id)
    
    # 检查用户权限
    if not quotation.can_delete(request.user):
        messages.error(request, '您没有权限删除此报价。')
        return redirect('quotation:user_quotation_list')
    
    if request.method == 'POST':
        quotation.delete()
        messages.success(request, '报价已成功删除。')
        return redirect('quotation:user_quotation_list')
    
    # GET请求时显示确认页面
    context = {
        'quotation': quotation,
    }
    return render(request, 'quotation/delete_confirm.html', context)