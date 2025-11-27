import numpy as np
import trimesh
from typing import List, Dict, Any, Optional
from enum import Enum
import json
import os

# 导入各种特征识别Agent
from mold_feature_agent import MoldFeatureAgent, MoldFeature
from plate_feature_agent import PlateFeatureAgent, PlateFeature
from rotational_feature_agent import RotationalFeatureAgent, RotationalFeature


class PartType(Enum):
    MOLD = "mold"                           # 模具
    PLATE = "plate"                         # 板类零件
    ROTATIONAL = "rotational"               # 回转体零件（盘类、套类、轴类）
    UNKNOWN = "unknown"                     # 未知类型


class FeatureManagerAgent:
    """模型特征管理Agent，用于根据零件类型分发到对应的特征识别Agent"""
    
    def __init__(self):
        self.mesh = None
        self.part_type = PartType.UNKNOWN
        self.current_agent = None
        self.features = []
        
    def load_mesh(self, file_path: str) -> bool:
        """加载3D模型文件"""
        try:
            loaded_mesh = trimesh.load(file_path)
            
            # 处理可能包含多个网格的场景（如3MF文件）
            if isinstance(loaded_mesh, trimesh.Scene):
                # 如果是场景，合并所有几何体
                if len(loaded_mesh.geometry) > 0:
                    # 获取所有网格
                    meshes = list(loaded_mesh.geometry.values())
                    # 合并为单个网格
                    self.mesh = trimesh.util.concatenate(meshes)
                    print(f"场景模型加载成功: 合并了{len(meshes)}个网格, {len(self.mesh.vertices)} 顶点, {len(self.mesh.faces)} 面")
                else:
                    print("场景中没有几何体")
                    return False
            else:
                # 单个网格
                self.mesh = loaded_mesh
                print(f"模型加载成功: {len(self.mesh.vertices)} 顶点, {len(self.mesh.faces)} 面")
            return True
        except Exception as e:
            print(f"模型加载失败: {e}")
            return False
    
    def classify_part_type(self, user_specified_type: Optional[str] = None) -> PartType:
        """分类零件类型"""
        if user_specified_type:
            # 如果用户指定了类型，则使用用户指定的类型
            try:
                self.part_type = PartType(user_specified_type.lower())
                print(f"使用用户指定的零件类型: {self.part_type.value}")
                return self.part_type
            except ValueError:
                print(f"无效的用户指定类型: {user_specified_type}，将自动识别零件类型")
        
        # 自动识别零件类型
        self.part_type = self._auto_classify_part()
        print(f"自动识别的零件类型: {self.part_type.value}")
        return self.part_type
    
    def _auto_classify_part(self) -> PartType:
        """自动分类零件类型"""
        if self.mesh is None:
            raise ValueError("请先加载3D模型")
        
        # 基于几何特征进行分类
        
        # 1. 计算模型的边界框
        bounds = self.mesh.bounds
        extents = bounds[1] - bounds[0]
        
        # 2. 分析长宽高比例
        ratios = [extents[0]/extents[1], extents[0]/extents[2], extents[1]/extents[2]]
        max_ratio = max(ratios)
        min_ratio = min(ratios)
        
        # 3. 计算模型的球形度（体积与表面积的关系）
        volume = self.mesh.volume
        surface_area = self.mesh.area
        sphericity = (36 * np.pi * volume**2)**(1/3) / surface_area if surface_area > 0 else 0
        
        # 4. 估计特征
        # 简单分类规则：
        # - 如果一个维度远大于其他两个维度，可能是轴类零件
        # - 如果所有维度相近，可能是模具或块状零件
        # - 如果有明显的空心结构，可能是套类零件
        
        # 检查是否为回转体（一个维度远小于其他两个，且其他两个相近）
        if max_ratio > 3 and abs(ratios[0] - ratios[1]) < 0.5 and min_ratio < 0.3:
            return PartType.ROTATIONAL
        # 检查是否为板类（一个维度远小于其他两个）
        elif max_ratio > 3:
            return PartType.PLATE
        # 其他情况暂时归为模具类
        else:
            return PartType.MOLD
    
    def select_agent(self) -> Any:
        """根据零件类型选择对应的特征识别Agent"""
        if self.part_type == PartType.MOLD:
            self.current_agent = MoldFeatureAgent()
            print("已选择模具特征识别Agent")
        elif self.part_type == PartType.PLATE:
            self.current_agent = PlateFeatureAgent()
            print("已选择板类零件特征识别Agent")
        elif self.part_type == PartType.ROTATIONAL:
            self.current_agent = RotationalFeatureAgent()
            print("已选择回转体零件特征识别Agent")
        else:
            # 默认使用模具特征识别Agent
            self.current_agent = MoldFeatureAgent()
            print("使用默认模具特征识别Agent")
            
        # 将网格数据传递给选中的Agent
        self.current_agent.mesh = self.mesh
        return self.current_agent
    
    def recognize_features(self) -> List[Any]:
        """识别特征"""
        if self.current_agent is None:
            raise ValueError("请先选择特征识别Agent")
            
        # 预处理网格
        if hasattr(self.current_agent, 'preprocess_mesh'):
            self.current_agent.preprocess_mesh()
        
        # 识别所有特征
        self.features = self.current_agent.recognize_all_features()
        return self.features
    
    def get_feature_statistics(self) -> Dict[str, Any]:
        """获取特征统计信息"""
        if self.current_agent is None:
            raise ValueError("请先选择特征识别Agent")
            
        if hasattr(self.current_agent, 'get_feature_statistics'):
            return self.current_agent.get_feature_statistics()
        else:
            return {
                'total_features': len(self.features),
                'message': '选定的Agent不支持统计信息功能'
            }
    
    def visualize_features(self):
        """可视化识别的特征"""
        if self.current_agent is None:
            raise ValueError("请先选择特征识别Agent")
            
        if hasattr(self.current_agent, 'visualize_features'):
            try:
                self.current_agent.visualize_features()
            except Exception as e:
                print(f"可视化失败: {e}")
        else:
            print("选定的Agent不支持可视化功能")
    
    def export_features_to_json(self, file_path: str):
        """将识别的特征导出为JSON文件"""
        if self.current_agent is None:
            raise ValueError("请先选择特征识别Agent")
            
        if hasattr(self.current_agent, 'export_features_to_json'):
            self.current_agent.export_features_to_json(file_path)
        else:
            # 手动导出
            stats = self.get_feature_statistics()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            print(f"特征信息已导出到 {file_path}")
    
    def process_model(self, file_path: str, part_type: Optional[str] = None) -> Dict[str, Any]:
        """
        完整处理流程：加载模型 -> 分类 -> 选择Agent -> 识别特征 -> 返回统计信息
        
        Args:
            file_path: 模型文件路径
            part_type: 用户指定的零件类型（可选）
            
        Returns:
            Dict: 处理结果和统计信息
        """
        print(f"开始处理模型: {file_path}")
        
        # 1. 加载模型
        if not self.load_mesh(file_path):
            return {"error": "模型加载失败"}
        
        # 2. 分类零件类型
        self.classify_part_type(part_type)
        
        # 3. 选择对应的Agent
        self.select_agent()
        
        # 4. 识别特征
        print("开始识别特征...")
        features = self.recognize_features()
        
        # 5. 获取统计信息
        stats = self.get_feature_statistics()
        
        # 6. 返回结果
        result = {
            "file_path": file_path,
            "part_type": self.part_type.value,
            "total_features": len(features),
            "statistics": stats,
            "status": "success"
        }
        
        print(f"处理完成: 识别到 {len(features)} 个特征")
        return result


# 使用示例
def main():
    # 创建特征管理Agent
    manager = FeatureManagerAgent()
    
    # 处理不同类型的零件模型
    
    # 示例1: 处理模具模型（用户指定类型）
    print("=== 处理模具模型 ===")
    # 注意：这里需要真实的模具模型文件
    # result1 = manager.process_model("mold_model.stl", "mold")
    
    # 示例2: 处理板类零件模型（自动识别类型）
    print("=== 处理板类零件模型 ===")
    # 注意：这里需要真实的板类零件模型文件
    # result2 = manager.process_model("plate_model.stl")
    
    # 示例3: 处理回转体零件模型（用户指定类型）
    print("=== 处理回转体零件模型 ===")
    # 注意：这里需要真实的回转体零件模型文件
    # result3 = manager.process_model("rotational_model.stl", "rotational")
    
    # 创建一个测试模型来演示功能
    print("=== 创建测试模型演示 ===")
    
    # 创建一个简单的板类测试模型
    test_mesh = trimesh.creation.box(extents=[100, 50, 10])
    
    # 添加一些孔
    hole1 = trimesh.creation.cylinder(radius=5, height=10)
    hole1.apply_translation([20, 0, 0])
    
    hole2 = trimesh.creation.cylinder(radius=8, height=10)
    hole2.apply_translation([-20, 0, 0])
    
    # 执行布尔差集操作创建带孔的板
    plate_with_holes = test_mesh.copy()
    plate_with_holes = plate_with_holes.difference(hole1, engine='scad')
    if plate_with_holes is not None:
        plate_with_holes = plate_with_holes.difference(hole2, engine='scad')
    
    # 如果OpenSCAD不可用，使用原始立方体
    if plate_with_holes is None:
        plate_with_holes = test_mesh
        print("警告: 无法创建带孔的板，使用基本板")
    
    # 保存测试模型
    test_file = "test_plate_model.stl"
    plate_with_holes.export(test_file)
    print(f"测试模型已保存为: {test_file}")
    
    # 直接在内存中处理测试模型
    manager.mesh = plate_with_holes
    manager.classify_part_type()  # 自动识别
    manager.select_agent()
    
    if hasattr(manager.current_agent, 'preprocess_mesh'):
        manager.current_agent.preprocess_mesh()
        
    features = manager.recognize_features()
    stats = manager.get_feature_statistics()
    
    print(f"\n测试模型处理结果:")
    print(f"识别到 {len(features)} 个特征")
    print("特征类型分布:")
    if 'feature_types' in stats:
        for feature_type, count in stats['feature_types'].items():
            print(f"  {feature_type}: {count}")
    
    # 导出结果
    manager.export_features_to_json("test_model_features.json")
    print(f"测试结果已导出到 test_model_features.json")


if __name__ == "__main__":
    main()