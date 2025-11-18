"""
高级3D模型分析服务
支持更多格式和更复杂的特征分析
"""

import os
import numpy as np
from django.conf import settings

try:
    from stl import mesh
    STL_AVAILABLE = True
except ImportError:
    STL_AVAILABLE = False
    print("警告: numpy-stl库未安装，STL分析功能将不可用")

# 尝试导入其他可能的3D库
try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    print("提示: trimesh库未安装，将使用基础分析功能")

class AdvancedModelAnalyzer:
    """
    高级3D模型分析器
    支持多种格式和复杂特征分析
    """
    
    def __init__(self, file_path):
        """
        初始化分析器
        :param file_path: 3D模型文件路径
        """
        self.file_path = file_path
        self.mesh_data = None
        self.file_extension = os.path.splitext(file_path)[1].lower()
        
        # 尝试加载模型
        self._load_mesh()
    
    def _load_mesh(self):
        """
        根据文件格式加载网格数据
        """
        if not os.path.exists(self.file_path):
            return
        
        try:
            # 优先使用trimesh（如果可用）
            if TRIMESH_AVAILABLE:
                self.mesh_data = trimesh.load(self.file_path)
                return
            
            # 如果trimesh不可用，尝试使用numpy-stl处理STL文件
            if STL_AVAILABLE and self.file_extension in ['.stl']:
                self.mesh_data = mesh.Mesh.from_file(self.file_path)
                return
                
        except Exception as e:
            print(f"加载模型文件时出错: {e}")
    
    def analyze(self):
        """
        分析3D模型并提取特征
        :return: 包含所有特征的字典
        """
        if not self.mesh_data:
            return {}
        
        features = {}
        
        # 计算基本几何特征
        features.update(self._calculate_basic_features())
        
        # 计算加工相关特征
        features.update(self._calculate_manufacturing_features())
        
        return features
    
    def _calculate_basic_features(self):
        """
        计算基本几何特征
        """
        features = {}
        
        try:
            if TRIMESH_AVAILABLE and hasattr(self.mesh_data, 'volume'):
                # 使用trimesh计算
                features['volume'] = max(0, self.mesh_data.volume) / 1000.0  # 转换为cm³
                
                if hasattr(self.mesh_data, 'area'):
                    features['surface_area'] = self.mesh_data.area / 100.0  # 转换为cm²
                
                # 包围盒
                if hasattr(self.mesh_data, 'bounds'):
                    bbox = self.mesh_data.bounds
                    if bbox is not None:
                        dimensions = bbox[1] - bbox[0]
                        features['bounding_box_length'] = dimensions[0]
                        features['bounding_box_width'] = dimensions[1]
                        features['bounding_box_height'] = dimensions[2]
                        
                        # 计算径长比
                        features['max_aspect_ratio'] = self._calculate_aspect_ratio(dimensions)
                
                # 复杂度（基于面数）
                if hasattr(self.mesh_data, 'faces'):
                    face_count = len(self.mesh_data.faces)
                    features['complexity_score'] = self._estimate_complexity(face_count)
                    
            elif STL_AVAILABLE and isinstance(self.mesh_data, mesh.Mesh):
                # 使用numpy-stl计算
                features['volume'] = max(0, self.mesh_data.get_volume()) / 1000.0
                
                # 计算表面积
                total_area = 0.0
                for i in range(len(self.mesh_data.vectors)):
                    v1, v2, v3 = self.mesh_data.vectors[i]
                    edge1 = v2 - v1
                    edge2 = v3 - v1
                    cross = np.cross(edge1, edge2)
                    area = np.linalg.norm(cross) / 2.0
                    total_area += area
                features['surface_area'] = total_area / 100.0
                
                # 包围盒
                vertices = self.mesh_data.vectors.reshape(-1, 3)
                min_coords = np.min(vertices, axis=0)
                max_coords = np.max(vertices, axis=0)
                dimensions = max_coords - min_coords
                features['bounding_box_length'] = dimensions[0]
                features['bounding_box_width'] = dimensions[1]
                features['bounding_box_height'] = dimensions[2]
                
                # 计算径长比
                features['max_aspect_ratio'] = self._calculate_aspect_ratio(dimensions)
                
                # 复杂度（基于三角面数）
                face_count = len(self.mesh_data.vectors)
                features['complexity_score'] = self._estimate_complexity(face_count)
                
        except Exception as e:
            print(f"计算基本特征时出错: {e}")
        
        return features
    
    def _calculate_manufacturing_features(self):
        """
        计算与制造相关的特征
        """
        features = {}
        
        try:
            # 估算最小拐角半径
            features['min_radius'] = self._estimate_min_radius()
            
            # 估算最小刀具要求
            features['min_tool_diameter'] = self._estimate_min_tool_diameter(
                features.get('min_radius', 0.5)
            )
            
            # 估算加工难度
            features['machining_difficulty'] = self._estimate_machining_difficulty(features)
            
        except Exception as e:
            print(f"计算制造特征时出错: {e}")
        
        return features
    
    def _calculate_aspect_ratio(self, dimensions):
        """
        计算径长比
        """
        try:
            length, width, height = dimensions
            ratios = [length/width if width > 0 else float('inf'),
                     length/height if height > 0 else float('inf'),
                     width/height if height > 0 else float('inf')]
            
            return max(r for r in ratios if r != float('inf'))
        except:
            return None
    
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
    
    def _estimate_min_radius(self):
        """
        估算最小拐角半径 (mm)
        """
        # 简化实现，实际应用中需要更复杂的算法
        return 0.5
    
    def _estimate_min_tool_diameter(self, min_radius):
        """
        根据最小拐角半径估算所需最小刀具直径 (mm)
        """
        # 通常刀具直径应至少是拐角半径的2倍
        return min_radius * 2.0
    
    def _estimate_machining_difficulty(self, features):
        """
        综合评估加工难度 (1-5分)
        """
        difficulty = 1.0
        
        # 基于径长比的难度调整
        aspect_ratio = features.get('max_aspect_ratio')
        if aspect_ratio and aspect_ratio > 10:
            difficulty += 1.0
        elif aspect_ratio and aspect_ratio > 5:
            difficulty += 0.5
        
        # 基于复杂度的难度调整
        complexity = features.get('complexity_score', 1.0)
        difficulty += (complexity - 1.0) * 0.5
        
        # 基于最小拐角半径的难度调整
        min_radius = features.get('min_radius', 0.5)
        if min_radius < 0.2:
            difficulty += 1.0
        elif min_radius < 0.5:
            difficulty += 0.5
        
        return min(difficulty, 5.0)  # 最大难度为5分