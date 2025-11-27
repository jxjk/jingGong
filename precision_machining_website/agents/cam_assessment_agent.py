import numpy as np
import trimesh
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
import sys
import os

# 添加当前目录到模块搜索路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 尝试导入依赖，如果失败则提供错误信息
try:
    from model_feature_manager import FeatureManagerAgent
    from mold_feature_agent import MoldFeatureType
    from plate_feature_agent import PlateFeatureType
    from rotational_feature_agent import RotationalFeatureType
except ImportError as e:
    print(f"导入依赖模块失败: {e}")
    print("请确保已安装必要的依赖包:")
    print("pip install trimesh numpy scikit-learn")
    sys.exit(1)


class ManufacturingDifficulty(Enum):
    """加工难度等级"""
    EASY = "easy"           # 容易
    MODERATE = "moderate"   # 中等
    DIFFICULT = "difficult" # 困难
    VERY_DIFFICULT = "very_difficult"  # 很困难


class CostComponent(Enum):
    """成本组成"""
    MATERIAL = "material"           # 材料成本
    MACHINING_TIME = "machining_time"  # 加工时间
    TOOL_COST = "tool_cost"         # 刀具成本
    FIXTURE_COST = "fixture_cost"   # 夹具成本
    QUALITY_CONTROL = "quality_control"  # 质量控制
    WASTE = "waste"                 # 废品率


@dataclass
class MachinabilityAssessment:
    """可加工性评估结果"""
    difficulty_level: ManufacturingDifficulty
    overall_score: float  # 0-100分
    feature_scores: Dict[str, float]  # 各特征评分
    critical_areas: List[str]  # 关键难点区域
    recommendations: List[str]  # 改进建议
    processing_time_estimate: float  # 预估加工时间(小时)
    cost_estimate: Dict[CostComponent, float]  # 成本估算


class CAMAssessmentAgent:
    """3D CAM评估智能体"""
    
    def __init__(self):
        self.mesh = None
        self.features = []
        self.material_density = 7.85  # 默认钢密度 g/cm³
        self.material_cost_per_kg = 10.0  # 默认材料成本 元/kg
        self.machining_rate_per_hour = 100.0  # 默认加工费率 元/小时
        self.tool_cost_factor = 0.1  # 刀具成本系数
    
    def load_mesh(self, file_path: str) -> bool:
        """加载3D模型"""
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
    
    def analyze_geometry(self) -> Dict[str, Any]:
        """几何特征分析"""
        if self.mesh is None:
            raise ValueError("请先加载3D模型")
        
        analysis = {}
        
        # 基本几何属性
        extents = self.mesh.extents
        volume = self.mesh.volume
        surface_area = self.mesh.area
        
        analysis.update({
            'volume_mm3': volume,
            'volume_cm3': volume / 1000,
            'surface_area_mm2': surface_area,
            'dimensions_mm': {
                'length': extents[0],
                'width': extents[1], 
                'height': extents[2]
            },
            'aspect_ratio': max(extents) / min(extents) if min(extents) > 0 else float('inf')
        })
        
        # 壁厚分析 (简单估算)
        if hasattr(self.mesh, 'face_adjacency'):
            # 估算最小壁厚
            analysis['estimated_min_wall_thickness'] = self._estimate_wall_thickness()
        
        # 曲率分析
        try:
            # 计算离散高斯曲率
            gaussian_curvatures = trimesh.curvature.discrete_gaussian_curvature_measure(
                self.mesh, self.mesh.vertices, 0.1)
            analysis['mean_curvature'] = float(np.mean(np.abs(gaussian_curvatures)))
            analysis['max_curvature'] = float(np.max(np.abs(gaussian_curvatures)))
        except:
            analysis['mean_curvature'] = 0.0
            analysis['max_curvature'] = 0.0
        
        return analysis
    
    def _estimate_wall_thickness(self) -> float:
        """估算最小壁厚"""
        # 简单方法：使用边界框尺寸的一定比例作为估算
        extents = self.mesh.extents
        min_dim = min(extents)
        # 假设最小壁厚为最小尺寸的1%到10%
        return min_dim * 0.05  # 简化估算
    
    def analyze_features(self, features: List[Any]) -> Dict[str, Any]:
        """分析识别出的特征"""
        feature_analysis = {
            'feature_count': len(features),
            'feature_types': {},
            'complexity_factors': {}
        }
        
        for feature in features:
            # 计算特征类型分布
            if hasattr(feature, 'feature_type'):
                ftype = str(feature.feature_type)
                feature_analysis['feature_types'][ftype] = \
                    feature_analysis['feature_types'].get(ftype, 0) + 1
            
            # 分析复杂度因子
            if hasattr(feature, 'bounding_box'):
                bbox = feature.bounding_box
                if 'min_size' not in feature_analysis['complexity_factors']:
                    feature_analysis['complexity_factors']['min_size'] = float('inf')
                if 'max_size' not in feature_analysis['complexity_factors']:
                    feature_analysis['complexity_factors']['max_size'] = 0
                    
                size = max(bbox.get('length', 0), bbox.get('width', 0), bbox.get('height', 0))
                if size > 0:
                    feature_analysis['complexity_factors']['min_size'] = min(
                        feature_analysis['complexity_factors']['min_size'], size)
                    feature_analysis['complexity_factors']['max_size'] = max(
                        feature_analysis['complexity_factors']['max_size'], size)
        
        # 计算特征复杂度指标
        feature_analysis['complexity_factors']['size_variation'] = (
            feature_analysis['complexity_factors']['max_size'] / 
            feature_analysis['complexity_factors']['min_size']
            if feature_analysis['complexity_factors']['min_size'] > 0 else 1
        )
        
        return feature_analysis
    
    def assess_machinability(self, geometry_analysis: Dict, feature_analysis: Dict) -> MachinabilityAssessment:
        """评估可加工性"""
        # 计算各项评分因子
        scores = {}
        
        # 1. 尺寸复杂度评分 (基于长宽高比例)
        aspect_ratio = geometry_analysis.get('aspect_ratio', 1)
        if aspect_ratio < 5:
            scores['dimension_complexity'] = 90
        elif aspect_ratio < 10:
            scores['dimension_complexity'] = 70
        else:
            scores['dimension_complexity'] = 40
        
        # 2. 曲率复杂度评分
        max_curvature = geometry_analysis.get('max_curvature', 0)
        if max_curvature < 0.1:
            scores['curvature_complexity'] = 90
        elif max_curvature < 1.0:
            scores['curvature_complexity'] = 70
        else:
            scores['curvature_complexity'] = 40
        
        # 3. 特征复杂度评分
        feature_count = feature_analysis.get('feature_count', 0)
        if feature_count < 10:
            scores['feature_complexity'] = 85
        elif feature_count < 30:
            scores['feature_complexity'] = 70
        elif feature_count < 50:
            scores['feature_complexity'] = 50
        else:
            scores['feature_complexity'] = 30
        
        # 4. 壁厚评分
        min_wall = geometry_analysis.get('estimated_min_wall_thickness', 10)
        if min_wall > 5:
            scores['wall_thickness'] = 90
        elif min_wall > 2:
            scores['wall_thickness'] = 70
        elif min_wall > 1:
            scores['wall_thickness'] = 50
        else:
            scores['wall_thickness'] = 20
        
        # 计算总体评分
        overall_score = np.mean(list(scores.values()))
        
        # 确定难度等级
        if overall_score >= 80:
            difficulty_level = ManufacturingDifficulty.EASY
        elif overall_score >= 60:
            difficulty_level = ManufacturingDifficulty.MODERATE
        elif overall_score >= 40:
            difficulty_level = ManufacturingDifficulty.DIFFICULT
        else:
            difficulty_level = ManufacturingDifficulty.VERY_DIFFICULT
        
        # 识别关键难点区域
        critical_areas = []
        if aspect_ratio > 10:
            critical_areas.append("长宽高比例过大，可能导致装夹困难")
        if max_curvature > 1.0:
            critical_areas.append("存在高曲率区域，加工难度大")
        if min_wall <= 1:
            critical_areas.append("壁厚过薄，加工时易变形")
        
        # 生成改进建议
        recommendations = []
        if aspect_ratio > 10:
            recommendations.append("建议优化设计，减少长宽高比例")
        if max_curvature > 1.0:
            recommendations.append("高曲率区域建议使用小直径刀具，降低进给速度")
        if min_wall <= 1:
            recommendations.append("薄壁区域建议采用分层加工，减少切削力")
        if feature_count > 50:
            recommendations.append("特征过多，建议优化加工路径，减少换刀次数")
        
        # 预估加工时间 (小时)
        base_time = feature_count * 0.1  # 每个特征平均0.1小时
        complexity_factor = (110 - overall_score) / 100  # 复杂度越高时间越长
        processing_time = base_time * (1 + complexity_factor)
        
        # 成本估算
        volume_cm3 = geometry_analysis.get('volume_cm3', 0)
        material_weight_kg = volume_cm3 * self.material_density / 1000
        material_cost = material_weight_kg * self.material_cost_per_kg
        
        machining_cost = processing_time * self.machining_rate_per_hour
        tool_cost = machining_cost * self.tool_cost_factor
        fixture_cost = 50.0  # 假设夹具成本
        qc_cost = machining_cost * 0.1  # 质量控制成本为加工成本的10%
        waste_cost = material_cost * 0.05  # 废品成本为材料成本的5%
        
        cost_estimate = {
            CostComponent.MATERIAL: material_cost,
            CostComponent.MACHINING_TIME: machining_cost,
            CostComponent.TOOL_COST: tool_cost,
            CostComponent.FIXTURE_COST: fixture_cost,
            CostComponent.QUALITY_CONTROL: qc_cost,
            CostComponent.WASTE: waste_cost
        }
        
        return MachinabilityAssessment(
            difficulty_level=difficulty_level,
            overall_score=round(overall_score, 2),
            feature_scores=scores,
            critical_areas=critical_areas,
            recommendations=recommendations,
            processing_time_estimate=round(processing_time, 2),
            cost_estimate=cost_estimate
        )
    
    def evaluate_model(self, file_path: str) -> MachinabilityAssessment:
        """完整评估模型的可加工性"""
        # 加载模型
        if not self.load_mesh(file_path):
            raise ValueError("无法加载模型文件")
        
        # 使用特征管理器识别特征
        feature_manager = FeatureManagerAgent()
        feature_manager.mesh = self.mesh
        
        # 根据模型类型选择相应的特征识别代理
        part_type = feature_manager._auto_classify_part()
        feature_manager.part_type = part_type
        feature_agent = feature_manager.select_agent()
        
        if hasattr(feature_agent, 'preprocess_mesh'):
            feature_agent.preprocess_mesh()
        
        # 识别特征
        features = feature_agent.recognize_all_features()
        self.features = features
        
        # 几何分析
        geometry_analysis = self.analyze_geometry()
        
        # 特征分析
        feature_analysis = self.analyze_features(features)
        
        # 可加工性评估
        assessment = self.assess_machinability(geometry_analysis, feature_analysis)
        
        return assessment
    
    def generate_assessment_report(self, assessment: MachinabilityAssessment, 
                                   file_path: str, geometry_analysis: Dict = None) -> Dict[str, Any]:
        """生成评估报告"""
        total_cost = sum(assessment.cost_estimate.values())
        
        report = {
            'file_path': file_path,
            'assessment_date': __import__('datetime').datetime.now().isoformat(),
            'machinability': {
                'difficulty_level': assessment.difficulty_level.value,
                'overall_score': assessment.overall_score,
                'feature_scores': assessment.feature_scores
            },
            'geometry_analysis': geometry_analysis,
            'processing_estimate': {
                'time_hours': assessment.processing_time_estimate,
                'cost_breakdown': {k.value: v for k, v in assessment.cost_estimate.items()},
                'total_cost': total_cost
            },
            'critical_areas': assessment.critical_areas,
            'recommendations': assessment.recommendations
        }
        
        return report
    
    def save_assessment_report(self, assessment: MachinabilityAssessment, 
                               file_path: str, report_path: str):
        """保存评估报告到文件"""
        geometry_analysis = self.analyze_geometry()
        report = self.generate_assessment_report(assessment, file_path, geometry_analysis)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"评估报告已保存到: {report_path}")


def main():
    """示例用法"""
    # 创建CAM评估智能体
    cam_agent = CAMAssessmentAgent()
    
    # 设置材料属性 (例如：铝合金)
    cam_agent.set_material_properties(density=2.7, cost_per_kg=30.0)  # 铝合金
    cam_agent.set_machining_properties(rate_per_hour=150.0, tool_factor=0.15)
    
    # 注意：这里需要一个实际的模型文件进行测试
    # 假设我们创建一个测试模型
    print("创建测试模型...")
    
    # 创建一个包含多种特征的测试模型
    base_box = trimesh.creation.box(extents=[50, 50, 20])
    
    # 添加一个孔
    hole_cylinder = trimesh.creation.cylinder(radius=5, height=25)
    hole_cylinder.apply_translation([0, 0, -5])
    
    # 添加一个槽
    slot_box = trimesh.creation.box(extents=[20, 5, 25])
    slot_box.apply_translation([15, 0, -5])
    
    # 布尔操作 - 减去孔和槽
    try:
        test_model = base_box.difference([hole_cylinder, slot_box], engine='scad')
        if test_model is None:
            test_model = base_box  # 如果布尔操作失败，使用原始模型
    except:
        test_model = base_box  # 如果OpenSCAD不可用，使用原始模型
    
    # 保存测试模型
    test_file = "test_model_for_assessment.stl"
    test_model.export(test_file)
    print(f"测试模型已保存: {test_file}")
    
    # 评估模型
    try:
        assessment = cam_agent.evaluate_model(test_file)
        
        print(f"\n=== 3D模型可加工性评估报告 ===")
        print(f"难度等级: {assessment.difficulty_level.value}")
        print(f"总体评分: {assessment.overall_score}/100")
        print(f"预估加工时间: {assessment.processing_time_estimate} 小时")
        print(f"预估总成本: {sum(assessment.cost_estimate.values()):.2f} 元")
        
        print(f"\n各维度评分:")
        for feature, score in assessment.feature_scores.items():
            print(f"  {feature}: {score}")
        
        print(f"\n关键难点区域:")
        for area in assessment.critical_areas:
            print(f"  - {area}")
        
        print(f"\n改进建议:")
        for rec in assessment.recommendations:
            print(f"  - {rec}")
        
        print(f"\n成本明细:")
        for component, cost in assessment.cost_estimate.items():
            print(f"  {component.value}: {cost:.2f} 元")
        
        # 保存完整报告
        cam_agent.save_assessment_report(assessment, test_file, "cam_assessment_report.json")
        
    except Exception as e:
        print(f"评估过程中出现错误: {e}")


if __name__ == "__main__":
    main()