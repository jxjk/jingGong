import numpy as np
import trimesh
from sklearn.cluster import DBSCAN
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import json


class PlateFeatureType(Enum):
    FLAT_SURFACE = "flat_surface"           # 平面
    HOLE = "hole"                           # 孔
    THREAD_HOLE = "thread_hole"             # 螺纹孔
    STEP_HOLE = "step_hole"                 # 台阶孔
    KEYWAY = "keyway"                       # 键槽
    SLOT = "slot"                           # 槽
    SIDE_FACE = "side_face"                 # 侧边
    SHOULDER_MILLING = "shoulder_milling"   # 方肩铣削
    POCKET = "pocket"                       # 型腔


@dataclass
class PlateFeature:
    """板类零件特征数据类"""
    feature_type: PlateFeatureType
    faces: List[int]                        # 特征包含的面
    vertices: np.ndarray                    # 特征包含的顶点
    centroid: np.ndarray                    # 特征中心点
    bounding_box: Dict[str, float]          # 边界框尺寸
    normal: np.ndarray = None               # 主要法向量
    depth: float = 0.0                      # 深度
    diameter: float = None                  # 直径
    length: float = None                    # 长度
    width: float = None                     # 宽度
    radius: float = None                    # 半径
    
    def to_dict(self) -> Dict[str, Any]:
        """将特征转换为字典格式，用于JSON序列化"""
        return {
            "feature_type": self.feature_type.value,
            "face_count": len(self.faces),
            "vertex_count": len(self.vertices) if self.vertices is not None else 0,
            "centroid": self.centroid.tolist() if self.centroid is not None else None,
            "bounding_box": self.bounding_box,
            "normal": self.normal.tolist() if self.normal is not None else None,
            "depth": self.depth,
            "diameter": self.diameter,
            "length": self.length,
            "width": self.width,
            "radius": self.radius
        }


class PlateFeatureAgent:
    """板类零件特征识别Agent"""
    
    def __init__(self):
        self.mesh = None
        self.features = []
        
    def load_mesh(self, file_path: str) -> bool:
        """加载3D模型文件"""
        try:
            self.mesh = trimesh.load(file_path)
            print(f"板类零件模型加载成功: {len(self.mesh.vertices)} 顶点, {len(self.mesh.faces)} 面")
            return True
        except Exception as e:
            print(f"板类零件模型加载失败: {e}")
            return False
    
    def preprocess_mesh(self):
        """预处理网格数据"""
        if self.mesh is None:
            raise ValueError("请先加载3D模型")
            
        # 计算法向量
        if not hasattr(self.mesh, 'face_normals') or self.mesh.face_normals.shape[0] == 0:
            self.mesh.compute_face_normals()
            
        if not hasattr(self.mesh, 'vertex_normals') or self.mesh.vertex_normals.shape[0] == 0:
            self.mesh.compute_vertex_normals()
            
        print("网格预处理完成")
    
    def identify_flat_surfaces(self) -> List[PlateFeature]:
        """识别平面特征"""
        features = []
        
        # 找到法向量一致的面（平面）
        face_normals = self.mesh.face_normals
        
        # 聚类相似法向量的面
        normal_clusters = {}
        angle_threshold = np.cos(np.radians(1))  # 5度阈值
        
        for i, normal in enumerate(face_normals):
            # 将法向量归一化
            normal = normal / np.linalg.norm(normal)
            
            # 寻找相似法向量的簇
            found_cluster = False
            for cluster_normal, face_list in normal_clusters.items():
                # 计算夹角余弦值
                cos_angle = np.dot(normal, cluster_normal)
                if cos_angle > angle_threshold or cos_angle < -angle_threshold:
                    normal_clusters[cluster_normal].append(i)
                    found_cluster = True
                    break
            
            # 如果没找到合适的簇，创建新簇
            if not found_cluster:
                normal_clusters[tuple(normal)] = [i]
        
        # 为大的平面簇创建特征
        for normal, face_list in normal_clusters.items():
            if len(face_list) >= 5:  # 至少5个面才认为是平面
                flat_features = self._cluster_faces(face_list, PlateFeatureType.FLAT_SURFACE)
                features.extend(flat_features)
                
        print(f"识别到 {len(features)} 个平面特征")
        return features
    
    def identify_holes(self) -> List[PlateFeature]:
        """识别孔特征（包括普通孔、螺纹孔、台阶孔）"""
        features = []
        
        # 基于曲率和几何特征识别孔
        try:
            # 计算顶点曲率
            vertex_curvature = trimesh.curvature.discrete_mean_curvature_measure(
                self.mesh, self.mesh.vertices, 0.05)
            
            # 寻找高曲率区域（可能为孔边缘）
            high_curvature_threshold = np.percentile(vertex_curvature, 90)
            high_curvature_vertices = np.where(vertex_curvature > high_curvature_threshold)[0]
            
            if len(high_curvature_vertices) > 0:
                # 获取相关的面
                hole_candidate_faces = []
                for face_idx, face in enumerate(self.mesh.faces):
                    if any(vertex in high_curvature_vertices for vertex in face):
                        hole_candidate_faces.append(face_idx)
                
                # 聚类孔候选面
                if hole_candidate_faces:
                    hole_features = self._cluster_faces(hole_candidate_faces, PlateFeatureType.HOLE)
                    
                    # 进一步分类孔类型
                    for feature in hole_features:
                        classified_feature = self._classify_hole_type(feature)
                        features.append(classified_feature)
                        
        except Exception as e:
            print(f"孔特征识别过程中出现错误: {e}")
            
        print(f"识别到 {len(features)} 个孔特征")
        return features
    
    def _classify_hole_type(self, feature: PlateFeature) -> PlateFeature:
        """分类孔类型（普通孔、螺纹孔、台阶孔）"""
        # 基于几何特征分类
        bbox = feature.bounding_box
        diameter = min(bbox['length'], bbox['width'])
        depth = bbox['height']
        
        # 更新特征直径
        feature.diameter = diameter
        
        # 简单分类规则（实际应用中可能需要更复杂的算法）
        if depth > diameter * 2:
            # 深孔，可能是螺纹孔
            feature.feature_type = PlateFeatureType.THREAD_HOLE
        elif depth > diameter * 0.5:
            # 中等深度，可能是台阶孔
            feature.feature_type = PlateFeatureType.STEP_HOLE
        else:
            # 浅孔，普通孔
            feature.feature_type = PlateFeatureType.HOLE
            
        return feature
    
    def identify_slots_and_keyways(self) -> List[PlateFeature]:
        """识别槽和键槽特征"""
        features = []
        
        # 寻找狭长的凹陷区域
        face_areas = self.mesh.area_faces
        small_area_faces = np.where(face_areas < np.percentile(face_areas, 20))[0]
        
        if len(small_area_faces) > 0:
            # 获取面中心
            face_centers = np.mean(self.mesh.vertices[self.mesh.faces[small_area_faces]], axis=1)
            
            # 聚类相近的面
            clustering = DBSCAN(eps=self._estimate_cluster_eps(face_centers), 
                               min_samples=3).fit(face_centers)
            
            for cluster_id in np.unique(clustering.labels_):
                if cluster_id == -1:  # 噪声点
                    continue
                    
                # 获取属于该聚类的面
                cluster_faces = [small_area_faces[i] for i, label in enumerate(clustering.labels_) if label == cluster_id]
                
                if len(cluster_faces) >= 3:
                    # 创建特征对象
                    feature = self._create_feature_from_faces(cluster_faces, PlateFeatureType.SLOT)
                    
                    if feature:
                        # 根据长宽比区分槽和键槽
                        bbox = feature.bounding_box
                        length_width_ratio = max(bbox['length'], bbox['width']) / min(bbox['length'], bbox['width'])
                        
                        if length_width_ratio > 3.0:  # 长宽比大于3认为是槽
                            feature.feature_type = PlateFeatureType.SLOT
                        elif length_width_ratio > 1.5:  # 长宽比在1.5-3之间认为是键槽
                            feature.feature_type = PlateFeatureType.KEYWAY
                            
                        # 设置尺寸属性
                        feature.length = max(bbox['length'], bbox['width'])
                        feature.width = min(bbox['length'], bbox['width'])
                        
                        features.append(feature)
        
        print(f"识别到 {len(features)} 个槽/键槽特征")
        return features
    
    def identify_side_faces(self) -> List[PlateFeature]:
        """识别侧边特征"""
        features = []
        
        # 侧边通常是垂直于主要平面的面
        face_normals = self.mesh.face_normals
        
        # 寻找接近垂直的面（与Z轴夹角接近90度）
        vertical_faces = []
        angle_threshold = np.cos(np.radians(30))  # 30度阈值
        
        for i, normal in enumerate(face_normals):
            # 计算与Z轴的夹角余弦值
            cos_angle = np.abs(normal[2])  # Z分量
            if cos_angle < angle_threshold:
                vertical_faces.append(i)
                
        if vertical_faces:
            side_features = self._cluster_faces(vertical_faces, PlateFeatureType.SIDE_FACE)
            features.extend(side_features)
            
        print(f"识别到 {len(features)} 个侧边特征")
        return features
    
    def identify_shoulder_milling(self) -> List[PlateFeature]:
        """识别方肩铣削特征"""
        features = []
        
        # 方肩铣削是具有直角过渡的台阶结构
        face_normals = self.mesh.face_normals
        face_centers = np.mean(self.mesh.vertices[self.mesh.faces], axis=1)
        
        # 寻找法向量差异较大的相邻面
        shoulder_candidates = []
        
        for i, face in enumerate(self.mesh.faces):
            # 获取相邻面
            adjacent_faces = self._get_adjacent_faces(i)
            
            for adj_face_idx in adjacent_faces:
                # 计算法向量夹角
                normal1 = face_normals[i]
                normal2 = face_normals[adj_face_idx]
                cos_angle = np.abs(np.dot(normal1, normal2))
                
                # 如果接近直角（90度），则可能是方肩
                if cos_angle < np.cos(np.radians(60)):  # 夹角大于60度
                    shoulder_candidates.extend([i, adj_face_idx])
                    
        if shoulder_candidates:
            # 去重
            shoulder_candidates = list(set(shoulder_candidates))
            shoulder_features = self._cluster_faces(shoulder_candidates, PlateFeatureType.SHOULDER_MILLING)
            features.extend(shoulder_features)
            
        print(f"识别到 {len(features)} 个方肩铣削特征")
        return features
    
    def identify_pockets(self) -> List[PlateFeature]:
        """识别型腔特征"""
        features = []
        
        # 型腔是凹陷的区域
        # 寻找朝向内部的面
        face_normals = self.mesh.face_normals
        face_centers = np.mean(self.mesh.vertices[self.mesh.faces], axis=1)
        
        # 计算模型整体中心
        mesh_centroid = np.mean(self.mesh.vertices, axis=0)
        
        # 寻找法向量指向模型内部的面
        inward_faces = []
        for i, (normal, center) in enumerate(zip(face_normals, face_centers)):
            # 向量从面中心指向模型中心
            to_center = mesh_centroid - center
            # 如果法向量与to_center向量同向，则面朝向内部
            if np.dot(normal, to_center) > 0:
                inward_faces.append(i)
                
        if inward_faces:
            pocket_features = self._cluster_faces(inward_faces, PlateFeatureType.POCKET)
            features.extend(pocket_features)
            
        print(f"识别到 {len(features)} 个型腔特征")
        return features
    
    def _get_adjacent_faces(self, face_idx: int) -> List[int]:
        """获取相邻面"""
        adjacent_faces = []
        target_face = self.mesh.faces[face_idx]
        
        for i, face in enumerate(self.mesh.faces):
            if i == face_idx:
                continue
                
            # 如果两个面共享一条边（两个顶点），则为相邻面
            shared_vertices = len(set(target_face) & set(face))
            if shared_vertices >= 2:
                adjacent_faces.append(i)
                
        return adjacent_faces
    
    def _cluster_faces(self, face_indices: List[int], feature_type: PlateFeatureType) -> List[PlateFeature]:
        """对面进行聚类以形成连续特征"""
        if not face_indices:
            return []
            
        # 获取面的中心点
        face_centers = np.mean(self.mesh.vertices[self.mesh.faces[face_indices]], axis=1)
        
        # 使用DBSCAN聚类算法
        clustering = DBSCAN(eps=self._estimate_cluster_eps(face_centers), 
                           min_samples=3).fit(face_centers)
        
        features = []
        for cluster_id in np.unique(clustering.labels_):
            if cluster_id == -1:  # 噪声点
                continue
                
            # 获取属于该聚类的面
            cluster_face_indices = [face_indices[i] for i, label in enumerate(clustering.labels_) if label == cluster_id]
            
            # 创建特征对象
            feature = self._create_feature_from_faces(cluster_face_indices, feature_type)
            if feature:
                features.append(feature)
                
        return features
    
    def _estimate_cluster_eps(self, points: np.ndarray) -> float:
        """估算聚类的eps参数"""
        if len(points) < 2:
            return 1.0
            
        # 计算点之间距离的中位数
        distances = []
        sample_size = min(len(points), 50)  # 限制样本数量以提高性能
        for i in range(sample_size):
            for j in range(i+1, sample_size):
                distances.append(np.linalg.norm(points[i] - points[j]))
                
        if distances:
            return np.median(distances) * 0.5
        else:
            return 1.0
    
    def _create_feature_from_faces(self, face_indices: List[int], feature_type: PlateFeatureType) -> PlateFeature:
        """根据面创建特征对象"""
        if not face_indices:
            return None
            
        # 收集所有顶点
        vertices = []
        for face_idx in face_indices:
            face = self.mesh.faces[face_idx]
            for vertex_idx in face:
                vertices.append(self.mesh.vertices[vertex_idx])
                
        vertices = np.array(vertices)
        unique_vertices = np.unique(vertices, axis=0)
        
        if len(unique_vertices) == 0:
            return None
            
        # 计算中心点
        centroid = np.mean(unique_vertices, axis=0)
        
        # 计算边界框
        bounding_box = self._calculate_bounding_box(unique_vertices)
        
        # 计算法向量（使用第一个面的法向量作为代表）
        normal = self.mesh.face_normals[face_indices[0]] if len(self.mesh.face_normals) > face_indices[0] else None
        
        # 计算其他属性
        depth = bounding_box.get('height', 0)
        
        return PlateFeature(
            feature_type=feature_type,
            faces=face_indices,
            vertices=unique_vertices,
            centroid=centroid,
            bounding_box=bounding_box,
            normal=normal,
            depth=depth
        )
    
    def _calculate_bounding_box(self, vertices: np.ndarray) -> Dict[str, float]:
        """计算边界框"""
        if len(vertices) == 0:
            return {}
            
        min_coords = np.min(vertices, axis=0)
        max_coords = np.max(vertices, axis=0)
        dimensions = max_coords - min_coords
        
        return {
            'length': dimensions[0],
            'width': dimensions[1],
            'height': dimensions[2],
            'volume': dimensions[0] * dimensions[1] * dimensions[2],
            'min_point': min_coords.tolist(),
            'max_point': max_coords.tolist()
        }
    
    def recognize_all_features(self) -> List[PlateFeature]:
        """识别所有板类零件特征"""
        if self.mesh is None:
            raise ValueError("请先加载3D模型")
            
        print("开始识别板类零件特征...")
        self.features = []
        
        # 1. 识别平面特征
        flat_surface_features = self.identify_flat_surfaces()
        self.features.extend(flat_surface_features)
        
        # 2. 识别孔特征
        hole_features = self.identify_holes()
        self.features.extend(hole_features)
        
        # 3. 识别槽和键槽特征
        slot_keyway_features = self.identify_slots_and_keyways()
        self.features.extend(slot_keyway_features)
        
        # 4. 识别侧边特征
        side_face_features = self.identify_side_faces()
        self.features.extend(side_face_features)
        
        # 5. 识别方肩铣削特征
        shoulder_features = self.identify_shoulder_milling()
        self.features.extend(shoulder_features)
        
        # 6. 识别型腔特征
        pocket_features = self.identify_pockets()
        self.features.extend(pocket_features)
        
        print(f"总共识别到 {len(self.features)} 个板类零件特征")
        return self.features
    
    def get_feature_statistics(self) -> Dict[str, Any]:
        """获取特征统计信息，包含详细的尺寸信息"""
        stats = {
            'total_features': len(self.features),
            'feature_types': {},
            'feature_details': []
        }
        
        # 统计各特征类型数量和详细信息
        for feature in self.features:
            feature_type = feature.feature_type.value
            stats['feature_types'][feature_type] = stats['feature_types'].get(feature_type, 0) + 1
            
            # 添加特征详细信息
            feature_detail = feature.to_dict()
            stats['feature_details'].append(feature_detail)
        
        return stats
    
    def export_features_to_json(self, file_path: str):
        """将识别的特征导出为JSON文件"""
        stats = self.get_feature_statistics()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"板类零件特征信息已导出到 {file_path}")
    
    def visualize_features(self):
        """可视化识别的特征"""
        if not self.features:
            print("没有特征可可视化")
            return
            
        # 为每种特征类型分配颜色
        feature_colors = {
            PlateFeatureType.FLAT_SURFACE: [1, 0, 0, 0.7],       # 红色 - 平面
            PlateFeatureType.HOLE: [0, 1, 0, 0.7],               # 绿色 - 孔
            PlateFeatureType.THREAD_HOLE: [0, 0, 1, 0.7],        # 蓝色 - 螺纹孔
            PlateFeatureType.STEP_HOLE: [1, 1, 0, 0.7],          # 黄色 - 台阶孔
            PlateFeatureType.KEYWAY: [1, 0, 1, 0.7],             # 紫色 - 键槽
            PlateFeatureType.SLOT: [0, 1, 1, 0.7],               # 青色 - 槽
            PlateFeatureType.SIDE_FACE: [0.5, 0, 0.5, 0.7],      # 紫红色 - 侧边
            PlateFeatureType.SHOULDER_MILLING: [1, 0.5, 0, 0.7], # 橙色 - 方肩铣削
            PlateFeatureType.POCKET: [0.5, 0.5, 0.5, 0.7]        # 灰色 - 型腔
        }
        
        # 创建颜色数组
        face_colors = np.ones((len(self.mesh.faces), 4)) * [0.8, 0.8, 0.8, 0.3]  # 默认灰色半透明
        
        # 为每个特征分配颜色
        for feature in self.features:
            color = feature_colors.get(feature.feature_type, [0.5, 0.5, 0.5, 0.7])
            for face_idx in feature.faces:
                if face_idx < len(face_colors):
                    face_colors[face_idx] = color
                    
        # 应用颜色并显示
        self.mesh.visual.face_colors = face_colors
        scene = trimesh.Scene(self.mesh)
        scene.show()


# 使用示例
def main():
    # 创建板类零件特征识别Agent
    agent = PlateFeatureAgent()
    
    # 加载测试模型（实际使用时替换为真实板类零件模型路径）
    # 这里我们创建一个简单的测试模型
    print("创建测试板类零件模型...")
    
    # 创建基本板作为主体
    plate_base = trimesh.creation.box(extents=[100, 50, 10])
    
    # 添加一些孔
    hole1 = trimesh.creation.cylinder(radius=5, height=10)
    hole1.apply_translation([20, 0, 0])
    
    hole2 = trimesh.creation.cylinder(radius=8, height=10)
    hole2.apply_translation([-20, 0, 0])
    
    # 执行布尔差集操作创建带孔的板
    plate_with_holes = plate_base.copy()
    plate_with_holes = plate_with_holes.difference(hole1, engine='scad')
    if plate_with_holes is not None:
        plate_with_holes = plate_with_holes.difference(hole2, engine='scad')
    
    # 如果OpenSCAD不可用，使用原始立方体
    if plate_with_holes is None:
        plate_with_holes = plate_base
        print("警告: 无法创建带孔的板，使用基本板")
    
    agent.mesh = plate_with_holes
    
    # 预处理网格
    agent.preprocess_mesh()
    
    # 识别所有特征
    features = agent.recognize_all_features()
    
    # 获取统计信息
    stats = agent.get_feature_statistics()
    print("\n=== 板类零件特征识别结果 ===")
    print(f"总特征数: {stats['total_features']}")
    print("特征类型分布:")
    for feature_type, count in stats['feature_types'].items():
        print(f"  {feature_type}: {count}")
    
    # 导出特征信息
    agent.export_features_to_json("plate_features.json")
    
    # 可视化结果（如果环境支持）
    try:
        agent.visualize_features()
    except Exception as e:
        print(f"可视化失败: {e}")


if __name__ == "__main__":
    main()
