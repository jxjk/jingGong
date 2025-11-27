import os
import sys
import json
from decimal import Decimal

# 现在导入agents模块中的类
try:
    # 尝试直接从agents包导入
    from agents.cam_assessment_agent import CAMAssessmentAgent, CostComponent, ManufacturingDifficulty
    from agents.model_feature_manager import FeatureManagerAgent, PartType
    from agents.cam_assessment_agent import MachinabilityAssessment
except ImportError as e:
    print(f"警告: 无法导入CAM评估智能体: {e}")
    # 定义模拟类以避免崩溃，但仍提供基本功能
    class ManufacturingDifficulty:
        EASY = "easy"
        MODERATE = "moderate"
        DIFFICULT = "difficult"
        VERY_DIFFICULT = "very_difficult"
    
    class CostComponent:
        MATERIAL = "material"
        MACHINING_TIME = "machining_time"
        TOOL_COST = "tool_cost"
        FIXTURE_COST = "fixture_cost"
        QUALITY_CONTROL = "quality_control"
        WASTE = "waste"
    
    class MachinabilityAssessment:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    class CAMAssessmentAgent:
        def __init__(self):
            self.mesh = None
            self.features = []
            self.material_density = 7.85
            self.material_cost_per_kg = 10.0
            self.machining_rate_per_hour = 100.0
            self.tool_cost_factor = 0.1

        def load_mesh(self, file_path):
            """尝试加载3D模型，使用trimesh或其他库"""
            try:
                import trimesh
                self.mesh = trimesh.load(file_path)
                print(f"使用trimesh加载模型成功: {len(self.mesh.vertices)} 顶点, {len(self.mesh.faces)} 面")
                return True
            except ImportError:
                print("trimesh库未安装，无法加载3D模型")
                return False
            except Exception as e:
                print(f"加载模型失败: {e}")
                return False

        def analyze_geometry(self):
            """分析几何特征"""
            if self.mesh is None:
                return {}
            try:
                import numpy as np
                analysis = {}
                extents = self.mesh.extents
                volume = getattr(self.mesh, 'volume', 0)
                surface_area = getattr(self.mesh, 'area', 0)
                
                analysis.update({
                    'volume_mm3': volume,
                    'volume_cm3': volume / 1000 if volume else 0,
                    'surface_area_mm2': surface_area,
                    'dimensions_mm': {
                        'length': extents[0] if len(extents) > 0 else 0,
                        'width': extents[1] if len(extents) > 1 else 0, 
                        'height': extents[2] if len(extents) > 2 else 0
                    },
                    'aspect_ratio': max(extents) / min(extents) if min(extents) > 0 else float('inf')
                })
                return analysis
            except Exception as e:
                print(f"几何分析失败: {e}")
                return {}

        def evaluate_model(self, file_path):
            """评估模型（返回基础评估）"""
            if not self.load_mesh(file_path):
                # 如果加载失败，创建一个基础评估
                from .cad_analyzer import CADModelAnalyzer
                analyzer = CADModelAnalyzer(file_path)
                features = analyzer.analyze()
                # 基于CAD分析器的结果创建评估
                score = features.get('complexity_score', 3.0) * 20  # 转换为100分制
                volume = features.get('volume', 0) or 0
                
                cost_estimate = {
                    CostComponent.MATERIAL: volume * self.material_density * self.material_cost_per_kg / 1000,
                    CostComponent.MACHINING_TIME: 50.0,  # 默认加工费
                    CostComponent.TOOL_COST: 5.0,
                    CostComponent.FIXTURE_COST: 10.0,
                    CostComponent.QUALITY_CONTROL: 5.0,
                    CostComponent.WASTE: 2.0
                }
                
                return MachinabilityAssessment(
                    difficulty_level=ManufacturingDifficulty.MODERATE,
                    overall_score=score,
                    feature_scores={'geometry_analysis': score},
                    critical_areas=[],
                    recommendations=['需要进一步分析'],
                    processing_time_estimate=1.0,
                    cost_estimate=cost_estimate
                )
            else:
                # 模型加载成功，进行基本分析
                geometry_analysis = self.analyze_geometry()
                score = 60.0  # 默认中等分数
                if geometry_analysis:
                    volume = geometry_analysis.get('volume_cm3', 0)
                    if volume > 100:  # 大体积模型可能更复杂
                        score = 70.0
                    elif volume > 10:
                        score = 60.0
                    else:
                        score = 50.0
                
                cost_estimate = {
                    CostComponent.MATERIAL: geometry_analysis.get('volume_cm3', 0) * self.material_density * self.material_cost_per_kg / 1000,
                    CostComponent.MACHINING_TIME: 50.0,
                    CostComponent.TOOL_COST: 5.0,
                    CostComponent.FIXTURE_COST: 10.0,
                    CostComponent.QUALITY_CONTROL: 5.0,
                    CostComponent.WASTE: 2.0
                }
                
                return MachinabilityAssessment(
                    difficulty_level=ManufacturingDifficulty.MODERATE,
                    overall_score=score,
                    feature_scores={'geometry_analysis': score},
                    critical_areas=[],
                    recommendations=['需要进一步分析'],
                    processing_time_estimate=1.0,
                    cost_estimate=cost_estimate
                )

        def generate_assessment_report(self, assessment, file_path, geometry_analysis=None):
            """生成评估报告"""
            total_cost = sum(assessment.cost_estimate.values()) if hasattr(assessment, 'cost_estimate') else 0.0
            
            report = {
                'file_path': file_path,
                'assessment_date': __import__('datetime').datetime.now().isoformat(),
                'machinability': {
                    'difficulty_level': assessment.difficulty_level.value if hasattr(assessment.difficulty_level, 'value') else 'moderate',
                    'overall_score': assessment.overall_score,
                    'feature_scores': assessment.feature_scores
                },
                'geometry_analysis': geometry_analysis or {},
                'processing_estimate': {
                    'time_hours': assessment.processing_time_estimate if hasattr(assessment, 'processing_time_estimate') else 1.0,
                    'cost_breakdown': {k.value: v for k, v in assessment.cost_estimate.items()} if hasattr(assessment, 'cost_estimate') else {},
                    'total_cost': total_cost
                },
                'critical_areas': assessment.critical_areas if hasattr(assessment, 'critical_areas') else [],
                'recommendations': assessment.recommendations if hasattr(assessment, 'recommendations') else []
            }
            
            return report

    class FeatureManagerAgent:
        def __init__(self): pass
    class PartType:
        MOLD = "mold"
        PLATE = "plate"
        ROTATIONAL = "rotational"
        UNKNOWN = "unknown"


class DFMAnalyzer:
    """
    DFM分析器，集成agents中的CAM评估智能体
    """
    
    def __init__(self, file_path=None):
        """
        初始化DFM分析器
        :param file_path: 3D模型文件路径
        """
        self.file_path = file_path
        self.cam_agent = CAMAssessmentAgent()
        self.feature_manager = FeatureManagerAgent()
        self.assessment = None
        self.report = None
        
    def set_material_properties(self, density: float, cost_per_kg: float):
        """设置材料属性"""
        self.cam_agent.set_material_properties(density, cost_per_kg)
    
    def set_machining_properties(self, rate_per_hour: float, tool_factor: float):
        """设置加工属性"""
        self.cam_agent.set_machining_properties(rate_per_hour, tool_factor)
    
    def analyze(self, file_path=None):
        """
        执行完整的DFM分析
        :param file_path: 3D模型文件路径（可选，如果初始化时已提供则可不传）
        :return: 分析结果字典
        """
        if file_path:
            self.file_path = file_path
            
        if not self.file_path or not os.path.exists(self.file_path):
            raise FileNotFoundError(f"3D模型文件不存在: {self.file_path}")
        
        try:
            # 使用CAM评估智能体进行分析
            self.assessment = self.cam_agent.evaluate_model(self.file_path)
            geometry_analysis = self.cam_agent.analyze_geometry()
            self.report = self.cam_agent.generate_assessment_report(
                self.assessment, self.file_path, geometry_analysis
            )
        except Exception as e:
            print(f"CAM评估智能体分析失败: {e}")
            # 创建一个基础的评估对象，以防主要分析失败
            from cam_assessment_agent import ManufacturingDifficulty, MachinabilityAssessment, CostComponent
            try:
                # 首先尝试加载模型
                if not self.cam_agent.load_mesh(self.file_path):
                    # 如果模型加载失败，直接返回基本结果
                    self.assessment = None
                    self.report = {
                        'file_path': self.file_path,
                        'geometry_analysis': {},
                        'processing_estimate': {
                            'time_hours': 0.0,
                            'total_cost': 0.0
                        }
                    }
                    return self._generate_dfm_results()
                    
                # 尝试使用基本几何分析
                geometry_analysis = self.cam_agent.analyze_geometry()
                # 创建基础评估
                self.assessment = MachinabilityAssessment(
                    difficulty_level=ManufacturingDifficulty.MODERATE,
                    overall_score=60.0,
                    feature_scores={'basic_geometry': 60.0},
                    critical_areas=[],
                    recommendations=['需要进一步分析'],
                    processing_time_estimate=1.0,
                    cost_estimate={
                        CostComponent.MATERIAL: 10.0,
                        CostComponent.MACHINING_TIME: 50.0,
                        CostComponent.TOOL_COST: 5.0,
                        CostComponent.FIXTURE_COST: 10.0,
                        CostComponent.QUALITY_CONTROL: 5.0,
                        CostComponent.WASTE: 2.0
                    }
                )
                self.report = self.cam_agent.generate_assessment_report(
                    self.assessment, self.file_path, geometry_analysis
                )
            except Exception as basic_error:
                print(f"基础分析也失败: {basic_error}")
                # 如果所有分析都失败，返回基本结果
                self.assessment = None
                self.report = {
                    'file_path': self.file_path,
                    'geometry_analysis': {},
                    'processing_estimate': {
                        'time_hours': 0.0,
                        'total_cost': 0.0
                    }
                }
        
        # 生成DFM分析结果
        dfm_results = self._generate_dfm_results()
        return dfm_results
    
    def _generate_dfm_results(self):
        """
        生成DFM分析结果，适配QuotationRequest模型字段
        """
        if not self.assessment:
            return {}
            
        # 计算成本组成
        cost_breakdown = self.assessment.cost_estimate
        total_cost = sum(cost_breakdown.values())
        
        # 提取评估结果
        results = {
            # 基础几何特征
            'volume': self.report['geometry_analysis']['volume_cm3'] if self.report.get('geometry_analysis') else None,
            'surface_area': self.report['geometry_analysis']['surface_area_mm2'] / 100.0 if self.report.get('geometry_analysis') else None,  # 转换为cm²
            'bounding_box_length': self.report['geometry_analysis']['dimensions_mm']['length'] if self.report.get('geometry_analysis') else None,
            'bounding_box_width': self.report['geometry_analysis']['dimensions_mm']['width'] if self.report.get('geometry_analysis') else None,
            'bounding_box_height': self.report['geometry_analysis']['dimensions_mm']['height'] if self.report.get('geometry_analysis') else None,
            'max_aspect_ratio': self.report['geometry_analysis']['aspect_ratio'] if self.report.get('geometry_analysis') else None,
            
            # DFM相关字段
            'dmf_volume_factor': self._calculate_volume_factor(),
            'dmf_surface_area_factor': self._calculate_surface_area_factor(),
            'dmf_complexity_factor': self._calculate_complexity_factor(),
            'dmf_precision_factor': 1.0,  # 精度因子需要根据用户输入确定
            'dmf_feature_factor': self._calculate_feature_factor(),
            
            # 评估结果
            'complexity_score': self.assessment.overall_score / 20.0,  # 将100分制转为5分制
            'machining_difficulty': self.assessment.overall_score / 20.0,  # 将100分制转为5分制
            'processing_time_estimate': self.assessment.processing_time_estimate,
            'machining_difficulty_level': self.assessment.difficulty_level.value,
            
            # 成本分析
            'estimated_material_cost': cost_breakdown.get(CostComponent.MATERIAL, 0.0),
            'estimated_machining_cost': cost_breakdown.get(CostComponent.MACHINING_TIME, 0.0),
            'estimated_tool_cost': cost_breakdown.get(CostComponent.TOOL_COST, 0.0),
            'estimated_fixture_cost': cost_breakdown.get(CostComponent.FIXTURE_COST, 0.0),
            'estimated_qc_cost': cost_breakdown.get(CostComponent.QUALITY_CONTROL, 0.0),
            'estimated_waste_cost': cost_breakdown.get(CostComponent.WASTE, 0.0),
            'estimated_total_cost': total_cost,
            'processing_time_hours': self.assessment.processing_time_estimate,
            'min_radius': self._estimate_min_radius(),
            'min_tool_diameter': self._estimate_min_tool_diameter(),
            
            # DFM建议
            'dfm_recommendations': self.assessment.recommendations,
            'critical_areas': self.assessment.critical_areas,
        }
        
        return results
    
    def _calculate_volume_factor(self):
        """计算体积因子"""
        volume = self.report['geometry_analysis']['volume_cm3'] if self.report.get('geometry_analysis') else 0
        if volume:
            # 使用对数函数限制因子增长，避免大模型导致价格过高
            return 1 + (max(0, volume) ** 0.5) / 10.0
        return 1.0
    
    def _calculate_surface_area_factor(self):
        """计算表面积因子"""
        surface_area = self.report['geometry_analysis']['surface_area_mm2'] if self.report.get('geometry_analysis') else 0
        if surface_area:
            return 1 + (surface_area / 10000.0)  # 转换为cm²后计算
        return 1.0
    
    def _calculate_complexity_factor(self):
        """计算复杂度因子"""
        score = self.assessment.overall_score if self.assessment else 0
        if score:
            # 复杂度评分越高，加工难度越大，价格越高
            return 1 + (max(0, 100 - score) / 100.0)
        return 1.0
    
    def _calculate_feature_factor(self):
        """计算特征因子"""
        # 基于识别的特征数量
        feature_count = len(self.cam_agent.features) if hasattr(self.cam_agent, 'features') else 0
        return 1 + (feature_count / 20.0)  # 每20个特征增加10%成本
    
    def _estimate_min_radius(self):
        """估算最小拐角半径"""
        # 从曲率分析结果估算
        if self.report.get('geometry_analysis') and self.report['geometry_analysis'].get('mean_curvature'):
            mean_curvature = self.report['geometry_analysis']['mean_curvature']
            if mean_curvature > 0:
                # 曲率的倒数可以作为最小半径的估算
                return 1.0 / max(mean_curvature, 0.1)  # 避免除以0
        return 0.5  # 默认值
    
    def _estimate_min_tool_diameter(self):
        """估算最小刀具直径"""
        min_radius = self._estimate_min_radius()
        return min_radius * 2.0 if min_radius else 1.0
    
    def get_dfm_report(self):
        """获取完整的DFM分析报告"""
        return self.report if self.report else {}


def integrate_dfm_analysis_with_quotation(quotation_request, file_path=None):
    """
    将DFM分析集成到报价请求中
    :param quotation_request: QuotationRequest实例
    :param file_path: 3D模型文件路径
    :return: 更新后的报价请求
    """
    if not file_path and quotation_request.model_file:
        file_path = quotation_request.model_file.path
    elif not file_path:
        raise ValueError("必须提供文件路径或报价请求中的模型文件")
    
    # 创建DFM分析器
    dfm_analyzer = DFMAnalyzer()
    
    # 设置材料和加工属性（可以根据材料类型调整）
    material_properties = {
        'aluminum': {'density': 2.7, 'cost_per_kg': 30.0},
        'steel': {'density': 7.85, 'cost_per_kg': 10.0},
        'stainless_steel': {'density': 7.93, 'cost_per_kg': 15.0},
        'plastic': {'density': 1.2, 'cost_per_kg': 5.0},
        'other': {'density': 5.0, 'cost_per_kg': 20.0},
    }
    
    material = quotation_request.material
    if material in material_properties:
        props = material_properties[material]
        dfm_analyzer.set_material_properties(props['density'], props['cost_per_kg'])
    
    # 设置加工属性
    dfm_analyzer.set_machining_properties(rate_per_hour=100.0, tool_factor=0.1)
    
    # 执行DFM分析
    dfm_results = dfm_analyzer.analyze(file_path)
    
    # 更新报价请求的DFM相关字段
    for field, value in dfm_results.items():
        if hasattr(quotation_request, field) and value is not None:
            setattr(quotation_request, field, value)
    
    # 保存更新
    quotation_request.save()
    return quotation_request