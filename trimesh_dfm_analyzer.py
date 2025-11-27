"""
基于trimesh的DFM分析器 - 简化版本
使用trimesh库进行3D模型分析，提供可制造性评估
"""

import os
import json
from decimal import Decimal
import numpy as np

try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    print("警告: trimesh库未安装，DFM分析功能将受限")


class TrimeshDFMAnalyzer:
    """
    基于trimesh的DFM分析器
    """
    
    def __init__(self):
        self.mesh = None
        self.material_density = 7.85  # 默认钢密度 g/cm³
        self.material_cost_per_kg = 10.0  # 默认材料成本 元/kg
        self.machining_rate_per_hour = 100.0  # 默认加工费率 元/小时
        self.tool_cost_factor = 0.1  # 刀具成本系数
    
    def load_mesh(self, file_path: str) -> bool:
        """加载3D模型"""
        if not TRIMESH_AVAILABLE:
            print("trimesh库不可用，无法加载模型")
            return False
            
        try:
            self.mesh = trimesh.load(file_path)
            print(f"模型加载成功: {len(self.mesh.vertices)} 顶点, {len(self.mesh.faces)} 面")
            return True
        except Exception as e:
            print(f"模型加载失败: {e}")
            return False
    
    def set_material_properties(self, density: float, cost_per_kg: float):
        """设置材料属性"""
        self.material_density = density
        self.material_cost_per_kg = cost_per_kg
    
    def set_machining_properties(self, rate_per_hour: float, tool_factor: float):
        """设置加工属性"""
        self.machining_rate_per_hour = rate_per_hour
        self.tool_cost_factor = tool_factor
    
    def analyze_geometry(self) -> dict:
        """几何特征分析"""
        if self.mesh is None:
            return {}
        
        analysis = {}
        
        # 基本几何属性
        extents = self.mesh.extents
        volume = self.mesh.volume
        surface_area = self.mesh.area
        
        analysis.update({
            'volume_mm3': volume,
            'volume_cm3': volume / 1000 if volume else 0,
            'surface_area_mm2': surface_area,
            'surface_area_cm2': surface_area / 100.0 if surface_area else 0,
            'dimensions_mm': {
                'length': extents[0] if len(extents) > 0 else 0,
                'width': extents[1] if len(extents) > 1 else 0, 
                'height': extents[2] if len(extents) > 2 else 0
            },
            'aspect_ratio': max(extents) / min(extents) if min(extents) > 0 else float('inf')
        })
        
        # 曲率分析
        try:
            # 计算离散高斯曲率
            if hasattr(trimesh, 'curvature'):
                gaussian_curvatures = trimesh.curvature.discrete_gaussian_curvature_measure(
                    self.mesh, self.mesh.vertices, 0.1)
                analysis['mean_curvature'] = float(np.mean(np.abs(gaussian_curvatures)))
                analysis['max_curvature'] = float(np.max(np.abs(gaussian_curvatures)))
            else:
                # 使用面法向量变化作为曲率近似
                face_normals = self.mesh.face_normals
                analysis['mean_curvature'] = 0.0
                analysis['max_curvature'] = 0.0
        except:
            analysis['mean_curvature'] = 0.0
            analysis['max_curvature'] = 0.0
        
        return analysis
    
    def estimate_complexity(self, geometry_analysis: dict) -> float:
        """估算复杂度评分 (1-5分)"""
        if not geometry_analysis:
            return 3.0  # 默认中等复杂度
            
        score = 3.0  # 基础分数
        
        # 基于体积的复杂度调整
        volume = geometry_analysis.get('volume_cm3', 0)
        if volume > 1000:  # 大体积模型可能更复杂
            score += 0.5
        elif volume < 1:   # 小体积模型可能精度要求高
            score += 0.3
            
        # 基于长宽高比例的复杂度调整
        aspect_ratio = geometry_analysis.get('aspect_ratio', 1)
        if aspect_ratio > 10:
            score += 0.5  # 非常不规则的形状更复杂
        elif aspect_ratio > 5:
            score += 0.2  # 不规则形状较复杂
            
        # 基于曲率的复杂度调整
        max_curvature = geometry_analysis.get('max_curvature', 0)
        if max_curvature > 1.0:
            score += 0.8  # 高曲率区域增加复杂度
        elif max_curvature > 0.1:
            score += 0.3  # 中等曲率区域增加复杂度
            
        # 限制评分在1-5之间
        return max(1.0, min(5.0, score))
    
    def estimate_machinability(self, geometry_analysis: dict) -> dict:
        """估算可加工性"""
        complexity = self.estimate_complexity(geometry_analysis)
        volume = geometry_analysis.get('volume_cm3', 0) if geometry_analysis else 0
        
        # 估算加工时间（小时）
        base_time = 0.1  # 基础时间
        complexity_factor = complexity / 3.0  # 基于复杂度的调整因子
        volume_factor = max(0.5, min(2.0, volume / 100.0))  # 基于体积的调整因子
        processing_time = base_time * complexity_factor * volume_factor * 10  # 调整因子以获得更合理的时间
        
        # 估算成本
        material_weight_kg = volume * self.material_density / 1000
        material_cost = material_weight_kg * self.material_cost_per_kg
        
        machining_cost = processing_time * self.machining_rate_per_hour
        tool_cost = machining_cost * self.tool_cost_factor
        fixture_cost = 10.0  # 假设夹具成本
        qc_cost = machining_cost * 0.1  # 质量控制成本为加工成本的10%
        waste_cost = material_cost * 0.05  # 废品成本为材料成本的5%
        
        return {
            'complexity_score': complexity,
            'processing_time_estimate': processing_time,
            'cost_breakdown': {
                'material': material_cost,
                'machining': machining_cost,
                'tool': tool_cost,
                'fixture': fixture_cost,
                'quality_control': qc_cost,
                'waste': waste_cost
            },
            'total_cost': material_cost + machining_cost + tool_cost + fixture_cost + qc_cost + waste_cost
        }
    
    def analyze(self, file_path: str) -> dict:
        """完整分析模型"""
        if not self.load_mesh(file_path):
            # 即使加载失败，也返回基础结构
            return {
                'geometry_analysis': {},
                'complexity_score': 0.0,
                'processing_time_estimate': 0.0,
                'cost_breakdown': {},
                'total_cost': 0.0,
                'machinability_assessment': '模型加载失败'
            }
            
        # 几何分析
        geometry_analysis = self.analyze_geometry()
        
        # 可加工性评估
        machinability = self.estimate_machinability(geometry_analysis)
        
        # 返回完整的分析结果
        result = {
            'geometry_analysis': geometry_analysis,
            'complexity_score': machinability['complexity_score'],
            'processing_time_estimate': machinability['processing_time_estimate'],
            'cost_breakdown': machinability['cost_breakdown'],
            'total_cost': machinability['total_cost'],
            'machinability_assessment': self._get_machinability_text(machinability['complexity_score'])
        }
        
        return result
    
    def _get_machinability_text(self, complexity_score: float) -> str:
        """获取可加工性文本描述"""
        if complexity_score <= 2.0:
            return "容易加工 - 几何形状简单，加工难度低"
        elif complexity_score <= 3.0:
            return "中等难度 - 需要标准加工工艺"
        elif complexity_score <= 4.0:
            return "较难加工 - 需要特殊工艺或多次装夹"
        else:
            return "非常困难 - 可能需要特殊设备或工艺"


def integrate_trimesh_dfm_analysis_with_quotation(quotation_request, file_path=None):
    """
    将基于trimesh的DFM分析集成到报价请求中
    :param quotation_request: QuotationRequest实例
    :param file_path: 3D模型文件路径
    :return: 更新后的报价请求
    """
    if not file_path:
        if hasattr(quotation_request, 'model_file') and quotation_request.model_file:
            file_path = quotation_request.model_file.path
        else:
            raise ValueError("必须提供文件路径或报价请求中的模型文件")
    
    # 创建DFM分析器
    dfm_analyzer = TrimeshDFMAnalyzer()
    
    # 根据材料类型设置属性
    material_properties = {
        'aluminum': {'density': 2.7, 'cost_per_kg': 30.0},
        'steel': {'density': 7.85, 'cost_per_kg': 10.0},
        'stainless_steel': {'density': 7.93, 'cost_per_kg': 15.0},
        'plastic': {'density': 1.2, 'cost_per_kg': 5.0},
        'other': {'density': 5.0, 'cost_per_kg': 20.0},
    }
    
    material = getattr(quotation_request, 'material', 'other')
    if material in material_properties:
        props = material_properties[material]
        dfm_analyzer.set_material_properties(props['density'], props['cost_per_kg'])
    
    # 设置加工属性
    dfm_analyzer.set_machining_properties(rate_per_hour=100.0, tool_factor=0.1)
    
    # 执行分析
    dfm_results = dfm_analyzer.analyze(file_path)
    
    # 更新报价请求的DFM相关字段
    geometry_analysis = dfm_results.get('geometry_analysis', {})
    if geometry_analysis:
        # 更新几何特征
        for field, value in geometry_analysis.items():
            if field == 'dimensions_mm':
                # 处理维度信息
                dims = value
                setattr(quotation_request, 'bounding_box_length', dims.get('length'))
                setattr(quotation_request, 'bounding_box_width', dims.get('width'))
                setattr(quotation_request, 'bounding_box_height', dims.get('height'))
            elif field in ['volume_cm3', 'surface_area_cm2', 'aspect_ratio', 'mean_curvature', 'max_curvature']:
                if field == 'surface_area_cm2':
                    setattr(quotation_request, 'surface_area', value)
                else:
                    setattr(quotation_request, field, value)
    
    # 更新复杂度和时间估算
    if 'complexity_score' in dfm_results:
        setattr(quotation_request, 'complexity_score', dfm_results['complexity_score'])
        setattr(quotation_request, 'machining_difficulty', dfm_results['complexity_score'])
    
    if 'processing_time_estimate' in dfm_results:
        setattr(quotation_request, 'processing_time_hours', dfm_results['processing_time_estimate'])
    
    # 更新成本信息
    cost_breakdown = dfm_results.get('cost_breakdown', {})
    if 'material' in cost_breakdown:
        setattr(quotation_request, 'estimated_material_cost', cost_breakdown['material'])
    if 'machining' in cost_breakdown:
        setattr(quotation_request, 'estimated_machining_cost', cost_breakdown['machining'])
    if 'tool' in cost_breakdown:
        setattr(quotation_request, 'estimated_tool_cost', cost_breakdown['tool'])
    if 'fixture' in cost_breakdown:
        setattr(quotation_request, 'estimated_fixture_cost', cost_breakdown['fixture'])
    if 'quality_control' in cost_breakdown:
        setattr(quotation_request, 'estimated_qc_cost', cost_breakdown['quality_control'])
    if 'waste' in cost_breakdown:
        setattr(quotation_request, 'estimated_waste_cost', cost_breakdown['waste'])
    
    # 更新总体估算
    if 'total_cost' in dfm_results:
        # 如果还没有预估价格，使用DFM分析的总成本
        if not getattr(quotation_request, 'estimated_price', None):
            setattr(quotation_request, 'estimated_price', dfm_results['total_cost'])
            setattr(quotation_request, 'final_price', dfm_results['total_cost'])
    
    # 保存更新
    quotation_request.save()
    return quotation_request