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
from .models import QuotationRequest, QuotationAdjustmentFactor, DFMAnalysis
from .forms import QuotationRequestForm
from .cad_analyzer import CADModelAnalyzer
import sys
import os
# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from trimesh_dfm_analyzer import TrimeshDFMAnalyzer, integrate_trimesh_dfm_analysis_with_quotation
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
                    
                    # 首先使用CAD分析器分析3D模型
                    analyzer = CADModelAnalyzer(file_path)
                    features = analyzer.analyze()
                    print(f"CAD分析完成，提取特征: {features}")
                    
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
                    
                    # 然后进行DFM分析
                    print("开始DFM分析...")
                    quotation = integrate_trimesh_dfm_analysis_with_quotation(quotation, file_path)
                    print("DFM分析完成并集成到报价请求中")
                    
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
    base_processing_prices = {
        'cnc_milling': 80,    # CNC铣削基础加工价格
        'cnc_turning': 60,     # CNC车削基础加工价格
        '3d_printing': 30,     # 3D打印基础加工价格
    }
    
    material_base_costs = {
        'aluminum': 30,       # 铝合金基础材料成本
        'steel': 50,          # 钢材基础材料成本
        'stainless_steel': 80, # 不锈钢基础材料成本
        'plastic': 20,        # 塑料基础材料成本
        'other': 40,          # 其他材料基础成本
    }
    
    surface_treatment_costs = {
        'none': 0,           # 无处理
        'anodizing': 15,     # 阳极氧化
        'painting': 10,      # 喷漆
        'polishing': 12,     # 抛光
        'other': 20,         # 其他
    }
    
    # 获取基础价格
    base_processing_price = base_processing_prices.get(quotation.processing_type, 60)
    base_material_cost = material_base_costs.get(quotation.material, 40)
    base_surface_treatment_cost = surface_treatment_costs.get(quotation.surface_treatment, 0)
    
    # 计算DMF（Design for Manufacturing）相关因子
    dmf_volume_factor = 1.0
    dmf_surface_area_factor = 1.0
    dmf_complexity_factor = 1.0
    dmf_precision_factor = 1.0
    dmf_feature_factor = 1.0
    
    # 体积因子（基于模型体积的材料成本调整）
    if quotation.volume:
        # 使用对数函数限制因子增长，避免大模型导致价格过高
        dmf_volume_factor = 1 + (np.log10(max(1, quotation.volume)) / 10.0)
        # 保存DMF因子到模型
        quotation.dmf_volume_factor = dmf_volume_factor

    # 表面积因子（影响加工时间和表面处理成本）
    if quotation.surface_area:
        dmf_surface_area_factor = 1 + (quotation.surface_area / 1000.0)
        quotation.dmf_surface_area_factor = dmf_surface_area_factor

    # 复杂度因子（影响加工难度和编程时间）
    if quotation.complexity_score:
        # 复杂度评分越高，加工难度越大，价格越高
        dmf_complexity_factor = 1 + (quotation.complexity_score / 5.0)  # 基于5分制评分
        quotation.dmf_complexity_factor = dmf_complexity_factor

    # 精度因子（精度要求越高，加工成本越高）
    if quotation.accuracy:
        # 解析精度要求字符串，例如 "IT6", "IT7", "±0.01mm" 等
        accuracy = quotation.accuracy.lower()
        if 'it6' in accuracy or '±0.01' in accuracy or '0.01' in accuracy:
            dmf_precision_factor = 1.5
        elif 'it7' in accuracy or '±0.02' in accuracy or '0.02' in accuracy:
            dmf_precision_factor = 1.3
        elif 'it8' in accuracy or '±0.05' in accuracy or '0.05' in accuracy:
            dmf_precision_factor = 1.1
        else:
            dmf_precision_factor = 1.0
        quotation.dmf_precision_factor = dmf_precision_factor

    # 特征因子（基于模型的特殊特征，如孔、倒角等）
    if quotation.oc_holes or quotation.cq_holes or quotation.oc_curved_surfaces or quotation.cq_fillets:
        feature_count = 0
        if quotation.oc_holes: feature_count += quotation.oc_holes
        if quotation.cq_holes: feature_count += quotation.cq_holes
        if quotation.oc_curved_surfaces: feature_count += quotation.oc_curved_surfaces
        if quotation.cq_fillets: feature_count += quotation.cq_fillets
        
        dmf_feature_factor = 1 + (feature_count / 20.0)  # 每20个特征增加10%成本
        quotation.dmf_feature_factor = dmf_feature_factor

    # 保存DMF因子到数据库
    quotation.save()
    
    # 计算细分报价
    # 1. 材料费用
    material_quantity_factor = max(1.0, quotation.quantity / 10.0)  # 数量对材料成本的影响较小
    # 如果有DFM分析的材料成本，则优先使用
    if hasattr(quotation, 'estimated_material_cost') and quotation.estimated_material_cost is not None:
        material_cost = quotation.estimated_material_cost * material_quantity_factor
    else:
        material_cost = base_material_cost * dmf_volume_factor * material_quantity_factor * dmf_feature_factor
    if not quotation.material_cost:
        quotation.material_cost = float(material_cost)

    # 2. 加工费用（基于加工类型、复杂度和精度）
    processing_quantity_factor = max(0.8, 100 / (quotation.quantity + 99))  # 数量折扣因子
    # 如果有DFM分析的加工成本，则优先使用
    if hasattr(quotation, 'estimated_machining_cost') and quotation.estimated_machining_cost is not None:
        processing_cost = quotation.estimated_machining_cost * processing_quantity_factor
    else:
        processing_cost = base_processing_price * dmf_complexity_factor * dmf_precision_factor * processing_quantity_factor
    if not quotation.processing_cost:
        quotation.processing_cost = float(processing_cost)

    # 3. 编程费用（复杂模型需要更多编程时间）
    # 如果有DFM分析的工具成本，则参考使用
    if hasattr(quotation, 'estimated_tool_cost') and quotation.estimated_tool_cost is not None:
        programming_cost = quotation.estimated_tool_cost
    else:
        programming_cost = 20 * dmf_complexity_factor * dmf_feature_factor  # 基础编程费
    if not quotation.programming_cost:
        quotation.programming_cost = float(programming_cost)

    # 4. 表面处理费用
    surface_treatment_quantity_factor = max(0.9, 20 / (quotation.quantity + 19))  # 表面处理的数量折扣
    surface_treatment_cost = base_surface_treatment_cost * dmf_surface_area_factor * surface_treatment_quantity_factor
    if not quotation.surface_treatment_cost:
        quotation.surface_treatment_cost = float(surface_treatment_cost)

    # 5. 包装物流费用（固定费用，基于数量调整）
    packaging_shipping_cost = quotation.packaging_shipping_cost or (5 + 0.5 * quotation.quantity)
    quotation.packaging_shipping_cost = float(packaging_shipping_cost)

    # 6. 税费（默认为0，可根据需要调整）
    tax_cost = quotation.tax_cost or 0
    quotation.tax_cost = float(tax_cost)

    # 7. 其他费用（如特殊要求等）
    other_cost = quotation.other_cost or 0
    quotation.other_cost = float(other_cost)

    # 计算直接成本 - 确保所有成本项都是float类型 to avoid type errors
    direct_cost = (float(material_cost) + float(processing_cost) + float(programming_cost) + 
                  float(surface_treatment_cost) + float(packaging_shipping_cost) + float(tax_cost) + float(other_cost))
                 
    # 应用数量折扣到直接成本
    direct_cost *= processing_quantity_factor

    # 根据DFM分析结果调整价格
    # 使用DFM分析中更精确的成本估算（如果可用）
    if hasattr(quotation, 'estimated_material_cost') and quotation.estimated_material_cost is not None:
        # 使用DFM分析的材料成本
        dfm_direct_cost = (float(quotation.estimated_material_cost or 0) + 
                          float(quotation.estimated_machining_cost or 0) + 
                          float(quotation.estimated_tool_cost or 0) + 
                          float(quotation.estimated_fixture_cost or 0) + 
                          float(quotation.estimated_qc_cost or 0) + 
                          float(quotation.estimated_waste_cost or 0) + 
                          float(packaging_shipping_cost) + float(tax_cost) + float(other_cost))
        # 使用DFM分析结果，但仍应用数量折扣
        direct_cost = dfm_direct_cost * processing_quantity_factor

    # 计算最终价格（包含利润）
    if quotation.profit_margin is not None:
        # 如果已设置利润率，使用该利润率
        profit_amount = direct_cost * float(quotation.profit_margin) / 100.0
        total_cost = direct_cost + profit_amount
    else:
        # 默认20%利润率
        profit_amount = direct_cost * 0.20
        total_cost = direct_cost + profit_amount

    # 更新数据库中的价格信息
    if not quotation.estimated_price:
        quotation.estimated_price = float(total_cost)
    if not quotation.final_price:
        quotation.final_price = float(total_cost)
    # 保存利润率和利润金额
    if not quotation.profit_margin:
        quotation.profit_margin = 20.00  # 默认20%
    if not quotation.profit_amount:
        quotation.profit_amount = float(profit_amount)
    quotation.save()
    
    # 计算价格区间
    price_min = total_cost * 0.9
    price_max = total_cost * 1.1
    
    # 准备价格因子详情
    factor_details = {
        'dmf_volume_factor': dmf_volume_factor,
        'dmf_surface_area_factor': dmf_surface_area_factor,
        'dmf_complexity_factor': dmf_complexity_factor,
        'dmf_precision_factor': dmf_precision_factor,
        'dmf_feature_factor': dmf_feature_factor,
        'quantity_factor': processing_quantity_factor,
        'quantity': quotation.quantity,
        'cost_breakdown': {
            'material_cost': material_cost,
            'processing_cost': processing_cost,
            'programming_cost': programming_cost,
            'surface_treatment_cost': surface_treatment_cost,
            'packaging_shipping_cost': packaging_shipping_cost,
            'tax_cost': tax_cost,
            'other_cost': other_cost
        }
    }

    context = {
        'quotation': quotation,
        'estimated_price': total_cost,
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


def dfm_analysis_home(request):
    """DFM分析首页"""
    return render(request, 'quotation/dfm_analysis_home.html')


def dfm_analysis_request(request):
    """DFM分析请求表单"""
    if request.method == 'POST':
        # 获取表单数据
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        company = request.POST.get('company', '')
        model_file = request.FILES.get('model_file')
        
        if not model_file:
            messages.error(request, '请上传3D模型文件。')
            return render(request, 'quotation/dfm_analysis_request.html')
            
        # 验证文件类型
        valid_extensions = ['.step', '.stp', '.stl', '.igs', '.iges', '.obj']
        ext = '.' + str(model_file.name).split('.')[-1].lower()
        if ext not in valid_extensions:
            messages.error(request, f'不支持的文件格式。只允许上传: {", ".join(valid_extensions)}')
            return render(request, 'quotation/dfm_analysis_request.html')
            
        # 验证文件大小（限制为50MB）
        if model_file.size > 50 * 1024 * 1024:
            messages.error(request, '文件大小不能超过50MB')
            return render(request, 'quotation/dfm_analysis_request.html')
        
        # 创建DFM分析记录
        dfm_analysis = DFMAnalysis.objects.create(
            name=name,
            email=email,
            company=company,
            model_file=model_file,
            user=request.user if request.user.is_authenticated else None
        )
        
        # 执行DFM分析
        try:
            dfm_analyzer = TrimeshDFMAnalyzer()
            dfm_results = dfm_analyzer.analyze(dfm_analysis.model_file.path)
            
            # 更新DFM分析记录
            # 更新几何分析结果
            geometry_analysis = dfm_results.get('geometry_analysis', {})
            if geometry_analysis:
                for field, value in geometry_analysis.items():
                    if field == 'dimensions_mm':
                        # 处理维度信息
                        dims = value
                        setattr(dfm_analysis, 'bounding_box_length', dims.get('length'))
                        setattr(dfm_analysis, 'bounding_box_width', dims.get('width'))
                        setattr(dfm_analysis, 'bounding_box_height', dims.get('height'))
                    elif field in ['volume_cm3', 'surface_area_cm2', 'aspect_ratio', 'mean_curvature', 'max_curvature']:
                        setattr(dfm_analysis, field.replace('surface_area_cm2', 'surface_area').replace('_cm2', '_cm2'), value)
            
            # 更新复杂度和时间估算
            if 'complexity_score' in dfm_results:
                setattr(dfm_analysis, 'complexity_score', dfm_results['complexity_score'])
                setattr(dfm_analysis, 'machining_difficulty', dfm_results['complexity_score'])
            
            if 'processing_time_estimate' in dfm_results:
                setattr(dfm_analysis, 'processing_time_estimate', dfm_results['processing_time_estimate'])
            
            # 更新成本信息
            cost_breakdown = dfm_results.get('cost_breakdown', {})
            if 'material' in cost_breakdown:
                setattr(dfm_analysis, 'estimated_material_cost', cost_breakdown['material'])
            if 'machining' in cost_breakdown:
                setattr(dfm_analysis, 'estimated_machining_cost', cost_breakdown['machining'])
            if 'tool' in cost_breakdown:
                setattr(dfm_analysis, 'estimated_tool_cost', cost_breakdown['tool'])
            if 'fixture' in cost_breakdown:
                setattr(dfm_analysis, 'estimated_fixture_cost', cost_breakdown['fixture'])
            if 'quality_control' in cost_breakdown:
                setattr(dfm_analysis, 'estimated_qc_cost', cost_breakdown['quality_control'])
            if 'waste' in cost_breakdown:
                setattr(dfm_analysis, 'estimated_waste_cost', cost_breakdown['waste'])
            
            # 更新总体估算
            if 'total_cost' in dfm_results:
                # 如果还没有预估价格，使用DFM分析的总成本
                if not getattr(dfm_analysis, 'estimated_total_cost', None):
                    setattr(dfm_analysis, 'estimated_total_cost', dfm_results['total_cost'])
            
            # 更新可加工性评估
            if 'machinability_assessment' in dfm_results:
                if not dfm_analysis.recommendations:
                    dfm_analysis.recommendations = dfm_results['machinability_assessment']
                else:
                    dfm_analysis.recommendations += "; " + dfm_results['machinability_assessment']
            
            dfm_analysis.is_processed = True
            dfm_analysis.save()
            
            messages.success(request, 'DFM分析完成！')
            return redirect('quotation:dfm_analysis_result', analysis_id=dfm_analysis.id)
        except Exception as e:
            print(f'DFM分析失败: {str(e)}')  # 记录详细错误信息
            # 即使DFM分析失败，也尝试使用CAD分析器获取基础信息
            try:
                from .cad_analyzer import CADModelAnalyzer
                cad_analyzer = CADModelAnalyzer(dfm_analysis.model_file.path)
                cad_features = cad_analyzer.analyze()
                
                # 将CAD分析结果保存到DFM分析记录中
                for field, value in cad_features.items():
                    if hasattr(dfm_analysis, field) and value is not None:
                        setattr(dfm_analysis, field, value)
                        
                dfm_analysis.recommendations = f"基于CAD分析的基础评估: {str(e)[:200]}..."
                dfm_analysis.is_processed = True  # 标记为已处理，即使不是完整的DFM分析
                dfm_analysis.save()
                
                messages.warning(request, 'DFM分析部分完成（使用CAD分析作为后备）')
                return redirect('quotation:dfm_analysis_result', analysis_id=dfm_analysis.id)
            except Exception as cad_error:
                print(f'CAD分析也失败: {str(cad_error)}')
                messages.error(request, f'DFM分析失败，但系统已记录您的请求: {str(e)[:100]}...')
                # 不删除记录，而是标记为处理失败但保留基本信息
                dfm_analysis.is_processed = False
                dfm_analysis.recommendations = f"分析过程中遇到问题: {str(e)[:500]}"
                dfm_analysis.save()
                return redirect('quotation:dfm_analysis_result', analysis_id=dfm_analysis.id)
    else:
        # 如果用户已登录，预填充邮箱
        initial_data = {}
        if request.user.is_authenticated:
            initial_data['email'] = request.user.email
            initial_data['name'] = request.user.get_full_name() or request.user.username
            
        context = {
            'initial_data': initial_data
        }
        return render(request, 'quotation/dfm_analysis_request.html', context)


def dfm_analysis_result(request, analysis_id):
    """DFM分析结果页面"""
    analysis = get_object_or_404(DFMAnalysis, id=analysis_id)
    
    # 检查用户权限 - 用户可以查看自己的分析结果或管理员可以查看所有分析结果
    has_permission = False
    
    if request.user.is_authenticated:
        # 检查多种权限条件（按优先级排序）：
        # 1. 用户字段匹配（最准确的关联）
        if analysis.user and analysis.user == request.user:
            has_permission = True
        # 2. 邮箱匹配
        elif analysis.email == request.user.email:
            has_permission = True
        # 3. 用户是管理员或超级用户
        elif request.user.is_staff or request.user.is_superuser:
            has_permission = True
        # 4. 如果模型中有name字段与用户名匹配
        elif analysis.name and (analysis.name == request.user.get_full_name() or analysis.name == request.user.username):
            has_permission = True
    else:
        # 未登录用户如果邮箱匹配也可以查看
        if analysis.email:
            has_permission = True
    
    if not has_permission:
        messages.error(request, '您没有权限查看此DFM分析结果。')
        return redirect('quotation:dfm_analysis_home')
    
    context = {
        'analysis': analysis
    }
    return render(request, 'quotation/dfm_analysis_result.html', context)


@login_required
def user_dfm_analysis_list(request):
    """用户DFM分析列表"""
    # 获取当前用户的所有DFM分析 - 优先使用用户关联字段，然后是邮箱或用户名匹配
    analyses = DFMAnalysis.objects.filter(
        Q(user=request.user) | Q(email=request.user.email) | Q(name=request.user.get_full_name()) | Q(name=request.user.username)
    ).order_by('-created_at')
    
    # 分页
    paginator = Paginator(analyses, 10)  # 每页显示10个
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'quotation/user_dfm_analysis_list.html', context)