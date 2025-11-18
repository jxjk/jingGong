"""
CAD文件分析服务
使用CadQuery处理STEP等CAD文件格式
"""

import os
import numpy as np
from django.conf import settings

# 尝试导入CadQuery
try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False
    print("提示: cadquery库未安装，CAD文件分析功能将不可用")

# 尝试导入其他3D库作为备选
try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    print("提示: trimesh库未安装")

try:
    from stl import mesh
    STL_AVAILABLE = True
except ImportError:
    STL_AVAILABLE = False
    print("提示: numpy-stl库未安装")

class CADModelAnalyzer:
    """
    CAD模型分析器
    支持STEP、STL等多种格式的3D模型分析
    """
    
    def __init__(self, file_path):
        """
        初始化分析器
        :param file_path: 3D模型文件路径
        """
        self.file_path = file_path
        self.model = None
        self.file_extension = os.path.splitext(file_path)[1].lower()
        
        # 尝试加载模型
        self._load_model()
    
    def _load_model(self):
        """
        根据文件格式加载模型数据
        """
        if not os.path.exists(self.file_path):
            return
        
        try:
            # 优先使用CadQuery处理STEP文件
            if CADQUERY_AVAILABLE and self.file_extension in ['.step', '.stp']:
                # 注意：CadQuery在某些环境下可能需要额外配置
                self.model = cq.importers.importStep(self.file_path)
                return
            
            # 使用trimesh处理通用3D格式
            if TRIMESH_AVAILABLE:
                self.model = trimesh.load(self.file_path)
                return
                
            # 使用numpy-stl处理STL文件
            if STL_AVAILABLE and self.file_extension in ['.stl']:
                self.model = mesh.Mesh.from_file(self.file_path)
                return
                
        except Exception as e:
            print(f"加载模型文件时出错: {e}")
            # 即使加载失败也继续，后续会处理None值
    
    def analyze(self):
        """
        分析3D模型并提取特征
        :return: 包含所有特征的字典
        """
        features = {}
        
        # 尝试使用不同方法分析模型
        if CADQUERY_AVAILABLE and hasattr(self.model, 'val') and self.file_extension in ['.step', '.stp']:
            features.update(self._analyze_with_cadquery())
        elif TRIMESH_AVAILABLE and hasattr(self.model, 'volume'):
            features.update(self._analyze_with_trimesh())
        elif STL_AVAILABLE and isinstance(self.model, mesh.Mesh):
            features.update(self._analyze_with_stl())
        else:
            # 如果没有合适的分析器，返回空特征
            print("警告: 没有合适的分析器处理此文件格式")
            return {}
        
        # 添加制造相关特征
        features.update(self._calculate_manufacturing_features(features))
        
        return features
    
    def _analyze_with_cadquery(self):
        """
        使用CadQuery分析CAD模型
        """
        features = {}
        
        try:
            # 获取模型实体
            shape = self.model.val()
            
            # 计算体积 (转换为立方厘米)
            features['volume'] = shape.Volume / 1000.0
            
            # 计算表面积 (转换为平方厘米)
            features['surface_area'] = shape.Area / 100.0
            
            # 获取包围盒
            bbox = shape.BoundingBox()
            features['bounding_box_length'] = bbox.xlen
            features['bounding_box_width'] = bbox.ylen
            features['bounding_box_height'] = bbox.zlen
            
            # 计算径长比
            dimensions = [bbox.xlen, bbox.ylen, bbox.zlen]
            ratios = []
            for i in range(len(dimensions)):
                for j in range(i+1, len(dimensions)):
                    if dimensions[j] > 0:
                        ratios.append(dimensions[i] / dimensions[j])
            
            features['max_aspect_ratio'] = max(ratios) if ratios else None
            
            # 复杂度评估（基于边数）
            # 注意：CadQuery的复杂度评估较为复杂，这里简化处理
            features['complexity_score'] = 3.0  # 默认中等复杂度
            
        except Exception as e:
            print(f"使用CadQuery分析模型时出错: {e}")
        
        return features
    
    def _analyze_with_trimesh(self):
        """
        使用Trimesh分析模型
        """
        features = {}
        
        try:
            # 计算体积 (转换为立方厘米)
            features['volume'] = max(0, self.model.volume) / 1000.0
            
            # 计算表面积 (转换为平方厘米)
            features['surface_area'] = self.model.area / 100.0
            
            # 获取包围盒
            bbox = self.model.bounds
            if bbox is not None:
                dimensions = bbox[1] - bbox[0]
                features['bounding_box_length'] = dimensions[0]
                features['bounding_box_width'] = dimensions[1]
                features['bounding_box_height'] = dimensions[2]
                
                # 计算径长比
                ratios = []
                for i in range(len(dimensions)):
                    for j in range(i+1, len(dimensions)):
                        if dimensions[j] > 0:
                            ratios.append(dimensions[i] / dimensions[j])
                
                features['max_aspect_ratio'] = max(ratios) if ratios else None
            
            # 复杂度评估（基于面数）
            face_count = len(self.model.faces)
            features['complexity_score'] = self._estimate_complexity(face_count)
            
        except Exception as e:
            print(f"使用Trimesh分析模型时出错: {e}")
        
        return features
    
    def _analyze_with_stl(self):
        """
        使用numpy-stl分析STL模型
        """
        features = {}
        
        try:
            # 计算体积 (转换为立方厘米)
            features['volume'] = max(0, self.model.get_volume()) / 1000.0
            
            # 计算表面积 (转换为平方厘米)
            total_area = 0.0
            for i in range(len(self.model.vectors)):
                v1, v2, v3 = self.model.vectors[i]
                edge1 = v2 - v1
                edge2 = v3 - v1
                cross = np.cross(edge1, edge2)
                area = np.linalg.norm(cross) / 2.0
                total_area += area
            features['surface_area'] = total_area / 100.0
            
            # 获取包围盒
            vertices = self.model.vectors.reshape(-1, 3)
            min_coords = np.min(vertices, axis=0)
            max_coords = np.max(vertices, axis=0)
            dimensions = max_coords - min_coords
            features['bounding_box_length'] = dimensions[0]
            features['bounding_box_width'] = dimensions[1]
            features['bounding_box_height'] = dimensions[2]
            
            # 计算径长比
            ratios = []
            for i in range(len(dimensions)):
                for j in range(i+1, len(dimensions)):
                    if dimensions[j] > 0:
                        ratios.append(dimensions[i] / dimensions[j])
            
            features['max_aspect_ratio'] = max(ratios) if ratios else None
            
            # 复杂度评估（基于三角面数）
            face_count = len(self.model.vectors)
            features['complexity_score'] = self._estimate_complexity(face_count)
            
        except Exception as e:
            print(f"使用numpy-stl分析模型时出错: {e}")
        
        return features
    
    def _calculate_manufacturing_features(self, base_features):
        """
        计算与制造相关的特征
        """
        features = {}
        
        try:
            # 估算最小拐角半径 (简化实现)
            features['min_radius'] = 0.5  # 默认值
            
            # 估算最小刀具直径
            features['min_tool_diameter'] = features['min_radius'] * 2.0
            
            # 估算加工难度 (1-5分)
            difficulty = 1.0
            
            # 基于径长比的难度调整
            aspect_ratio = base_features.get('max_aspect_ratio')
            if aspect_ratio and aspect_ratio > 10:
                difficulty += 1.0
            elif aspect_ratio and aspect_ratio > 5:
                difficulty += 0.5
            
            # 基于复杂度的难度调整
            complexity = base_features.get('complexity_score', 1.0)
            difficulty += (complexity - 1.0) * 0.5
            
            # 基于最小拐角半径的难度调整
            min_radius = features['min_radius']
            if min_radius < 0.2:
                difficulty += 1.0
            elif min_radius < 0.5:
                difficulty += 0.5
            
            features['machining_difficulty'] = min(difficulty, 5.0)
            
        except Exception as e:
            print(f"计算制造特征时出错: {e}")
        
        return features
    
    def _estimate_complexity(self, face_count):
        """
        根据面数估算复杂度 (1-5分)
        """
        if face_count < 1000:
            return 1.0
        elif face_count < 5000:
            return 2.0
        elif face_count < 20000:
            return 3.0
        elif face_count < 100000:
            return 4.0
        else:
            return 5.0