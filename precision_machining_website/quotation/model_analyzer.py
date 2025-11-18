"""
3D模型分析服务
用于从STL等格式的3D模型中提取几何特征
"""

import os
import numpy as np
from django.conf import settings
try:
    from stl import mesh
    STL_AVAILABLE = True
except ImportError:
    STL_AVAILABLE = False
    print("警告: numpy-stl库未安装，3D模型分析功能将不可用")


class ModelAnalyzer:
    """
    3D模型分析器
    支持从STL文件中提取几何特征
    """
    
    def __init__(self, file_path):
        """
        初始化分析器
        :param file_path: 3D模型文件路径
        """
        self.file_path = file_path
        self.mesh = None
        if STL_AVAILABLE and os.path.exists(file_path):
            try:
                self.mesh = mesh.Mesh.from_file(file_path)
            except Exception as e:
                print(f"加载模型文件时出错: {e}")
    
    def analyze(self):
        """
        分析3D模型并提取特征
        :return: 包含所有特征的字典
        """
        if not self.mesh:
            return {}
        
        features = {}
        
        # 计算体积
        features['volume'] = self.calculate_volume()
        
        # 计算表面积
        features['surface_area'] = self.calculate_surface_area()
        
        # 计算包围盒尺寸
        bbox_dims = self.calculate_bounding_box()
        features['bounding_box_length'] = bbox_dims[0] if bbox_dims else None
        features['bounding_box_width'] = bbox_dims[1] if bbox_dims else None
        features['bounding_box_height'] = bbox_dims[2] if bbox_dims else None
        
        # 计算最大径长比
        features['max_aspect_ratio'] = self.calculate_aspect_ratio(bbox_dims) if bbox_dims else None
        
        # 估算复杂度评分
        features['complexity_score'] = self.estimate_complexity()
        
        # 估算最小拐角半径（简化实现）
        features['min_radius'] = self.estimate_min_radius()
        
        return features
    
    def calculate_volume(self):
        """
        计算模型体积（cm³）
        """
        if not self.mesh:
            return None
        
        try:
            # STL库返回的体积单位需要根据实际情况调整
            volume = self.mesh.get_volume()
            # 假设模型单位是毫米，转换为立方厘米
            return volume / 1000.0
        except Exception as e:
            print(f"计算体积时出错: {e}")
            return None
    
    def calculate_surface_area(self):
        """
        计算模型表面积（cm²）
        """
        if not self.mesh:
            return None
        
        try:
            # 计算每个三角形的面积并求和
            total_area = 0.0
            for i in range(len(self.mesh.vectors)):
                # 获取三角形的三个顶点
                v1, v2, v3 = self.mesh.vectors[i]
                # 计算两个边向量
                edge1 = v2 - v1
                edge2 = v3 - v1
                # 计算叉积的一半模长（三角形面积）
                cross = np.cross(edge1, edge2)
                area = np.linalg.norm(cross) / 2.0
                total_area += area
            
            # 假设模型单位是毫米，转换为平方厘米
            return total_area / 100.0
        except Exception as e:
            print(f"计算表面积时出错: {e}")
            return None
    
    def calculate_bounding_box(self):
        """
        计算包围盒尺寸（mm）
        """
        if not self.mesh:
            return None
        
        try:
            # 获取所有顶点
            vertices = self.mesh.vectors.reshape(-1, 3)
            
            # 计算包围盒
            min_coords = np.min(vertices, axis=0)
            max_coords = np.max(vertices, axis=0)
            dimensions = max_coords - min_coords
            
            # 返回长、宽、高（mm）
            return dimensions[0], dimensions[1], dimensions[2]
        except Exception as e:
            print(f"计算包围盒时出错: {e}")
            return None
    
    def calculate_aspect_ratio(self, bbox_dims):
        """
        计算最大径长比
        """
        if not bbox_dims:
            return None
        
        try:
            # 计算长宽比、长高比、宽高比
            length, width, height = bbox_dims
            ratios = [length/width if width > 0 else float('inf'),
                     length/height if height > 0 else float('inf'),
                     width/height if height > 0 else float('inf')]
            
            # 返回最大比值
            return max(r for r in ratios if r != float('inf'))
        except Exception as e:
            print(f"计算径长比时出错: {e}")
            return None
    
    def estimate_complexity(self):
        """
        估算模型复杂度（基于三角面数量）
        """
        if not self.mesh:
            return None
        
        try:
            # 基于三角面数量估算复杂度
            triangle_count = len(self.mesh.vectors)
            
            # 简单的复杂度评分算法（可根据实际需求调整）
            if triangle_count < 1000:
                return 1.0  # 简单
            elif triangle_count < 10000:
                return 2.0  # 中等
            elif triangle_count < 100000:
                return 3.0  # 复杂
            else:
                return 4.0  # 非常复杂
        except Exception as e:
            print(f"估算复杂度时出错: {e}")
            return None
    
    def estimate_min_radius(self):
        """
        估算最小拐角半径（简化实现）
        """
        # 这是一个简化的实现，实际应用中需要更复杂的算法
        # 基于经验估算，可根据加工类型调整
        return 0.5  # 默认最小半径为0.5mm