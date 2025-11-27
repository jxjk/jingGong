import numpy as np
import trimesh
from sklearn.cluster import DBSCAN
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import json


class RotationalFeatureType(Enum):
    KEYWAY = "keyway"                           # 键槽
    THREAD = "thread"                           # 螺纹
    HOLE = "hole"                               # 孔
    END_FACE = "end_face"                       # 端面
    OUTER_CYLINDER = "outer_cylinder"           # 外圆
    BORED_HOLE = "bored_hole"                   # 镗孔
    OUTER_GROOVE = "outer_groove"               # 外圆切槽
    END_FACE_GROOVE = "end_face_groove"         # 端面切槽
    INNER_HOLE_GROOVE = "inner_hole_groove"     # 内孔切槽
    INNER_HOLE_END_GROOVE = "inner_hole_end_groove"  # 内孔端面切槽


@dataclass
class RotationalFeature:
    """回转体零件特征数据类"""
    feature_type: RotationalFeatureType
    faces: List[int]                            # 特征包含的面
    vertices: np.ndarray                        # 特征包含的顶点
    centroid: np.ndarray                        # 特征中心点
    bounding_box: Dict[str, float]              # 边界框尺寸
    normal: np.ndarray = None                   # 主要法向量
    depth: float = 0.0                          # 深度
    diameter: float = None                      # 直径
    length: float = None                        # 长度
    radius: float = None                        # 半径
    width: float = None                         # 宽度
    is_inner: bool = False                      # 是否为内特征（孔、内槽等）
    
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
            "radius": self.radius,
            "width": self.width,
            "is_inner": self.is_inner
        }


class RotationalFeatureAgent:
    """盘类、套类、轴类零件特征识别Agent"""
    
    def __init__(self):
        self.mesh = None
        self.features = []
        self.axis_direction = np.array([0, 0, 1])  # 默认旋转轴为Z轴
        
    def load_mesh(self, file_path: str) -> bool:
        """加载3D模型文件"""
        try:
            self.mesh = trimesh.load(file_path)
            print(f"回转体零件模型加载成功: {len(self.mesh.vertices)} 顶点, {len(self.mesh.faces)} 面")
            return True
        except Exception as e:
            print(f"回转体零件模型加载失败: {e}")
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
            
        # 估计旋转轴方向
        self._estimate_rotation_axis()
            
        print("网格预处理完成")
    
    def _estimate_rotation_axis(self):
        """估计零件的旋转轴方向"""
        # 通过主成分分析估计旋转轴
        try:
            # 计算点云的协方差矩阵
            covariance_matrix = np.cov(self.mesh.vertices.T)
            
            # 计算特征值和特征向量
            eigenvalues, eigenvectors = np.linalg.eigh(covariance_matrix)
            
            # 最小特征值对应的特征向量是旋转轴方向
            self.axis_direction = eigenvectors[:, np.argmin(eigenvalues)]
            self.axis_direction = self.axis_direction / np.linalg.norm(self.axis_direction)
            
            print(f"估计的旋转轴方向: {self.axis_direction}")
        except Exception as e:
            print(f"估计旋转轴时出错: {e}")
            # 默认使用Z轴
            self.axis_direction = np.array([0, 0, 1])
    
    def identify_end_faces(self) -> List[RotationalFeature]:
        """识别端面特征"""
        features = []
        
        # 端面是垂直于旋转轴的面
        face_normals = self.mesh.face_normals
        
        # 寻找与旋转轴垂直的面
        perpendicular_faces = []
        angle_threshold = np.cos(np.radians(10))  # 10度阈值
        
        for i, normal in enumerate(face_normals):
            # 计算法向量与旋转轴的夹角余弦值
            cos_angle = np.abs(np.dot(normal, self.axis_direction))
            # 如果接近垂直（夹角接近90度），则为端面候选
            if cos_angle < angle_threshold:
                perpendicular_faces.append(i)
                
        if perpendicular_faces:
            end_face_features = self._cluster_faces(perpendicular_faces, RotationalFeatureType.END_FACE)
            features.extend(end_face_features)
            
        print(f"识别到 {len(features)} 个端面特征")
        return features
    
    def identify_outer_cylinders(self) -> List[RotationalFeature]:
        """识别外圆特征"""
        features = []
        
        # 外圆面是与旋转轴平行且向外凸出的面
        face_normals = self.mesh.face_normals
        face_centers = np.mean(self.mesh.vertices[self.mesh.faces], axis=1)
        
        # 计算模型中心
        mesh_centroid = np.mean(self.mesh.vertices, axis=0)
        
        cylindrical_faces = []
        angle_threshold = np.cos(np.radians(10))  # 10度阈值
        
        for i, (normal, center) in enumerate(zip(face_normals, face_centers)):
            # 计算法向量与旋转轴的夹角余弦值
            cos_angle = np.abs(np.dot(normal, self.axis_direction))
            # 如果接近平行（夹角接近0或180度），则为圆柱面候选
            if cos_angle > angle_threshold:
                # 判断是否为外圆（法向量指向远离中心的方向）
                to_center = center - mesh_centroid
                if np.dot(normal, to_center) > 0:
                    cylindrical_faces.append(i)
                
        if cylindrical_faces:
            outer_cylinder_features = self._cluster_faces(cylindrical_faces, RotationalFeatureType.OUTER_CYLINDER)
            features.extend(outer_cylinder_features)
            
        print(f"识别到 {len(features)} 个外圆特征")
        return features
    
    def identify_holes_and_bored_holes(self) -> List[RotationalFeature]:
        """识别孔和镗孔特征"""
        features = []
        
        # 孔是与旋转轴平行且向内凹陷的面
        face_normals = self.mesh.face_normals
        face_centers = np.mean(self.mesh.vertices[self.mesh.faces], axis=1)
        
        # 计算模型中心
        mesh_centroid = np.mean(self.mesh.vertices, axis=0)
        
        hole_faces = []
        angle_threshold = np.cos(np.radians(10))  # 10度阈值
        
        for i, (normal, center) in enumerate(zip(face_normals, face_centers)):
            # 计算法向量与旋转轴的夹角余弦值
            cos_angle = np.abs(np.dot(normal, self.axis_direction))
            # 如果接近平行（夹角接近0或180度），则为孔面候选
            if cos_angle > angle_threshold:
                # 判断是否为孔（法向量指向中心的方向）
                to_center = center - mesh_centroid
                if np.dot(normal, to_center) < 0:
                    hole_faces.append(i)
                
        if hole_faces:
            hole_features = self._cluster_faces(hole_faces, RotationalFeatureType.HOLE)
            
            # 根据深度区分孔和镗孔
            for feature in hole_features:
                # 计算特征深度
                bbox = feature.bounding_box
                depth = bbox.get('height', 0) if np.argmax(np.abs(self.axis_direction)) == 2 else \
                       bbox.get('width', 0) if np.argmax(np.abs(self.axis_direction)) == 1 else \
                       bbox.get('length', 0)
                
                feature.depth = depth
                feature.is_inner = True
                
                # 简单区分：深孔为镗孔
                if depth > 10:  # 阈值可根据实际情况调整
                    feature.feature_type = RotationalFeatureType.BORED_HOLE
                else:
                    feature.feature_type = RotationalFeatureType.HOLE
                    
                # 计算直径
                feature.diameter = min(bbox.get('length', 0), bbox.get('width', 0), bbox.get('height', 0))
                
                features.append(feature)
            
        print(f"识别到 {len(features)} 个孔/镗孔特征")
        return features
    
    def identify_keyways(self) -> List[RotationalFeature]:
        """识别键槽特征"""
        features = []
        
        # 键槽是狭长的凹槽，通常位于外圆表面
        # 寻找具有特定长宽比的凹陷区域
        
        # 计算每个面的面积
        face_areas = self.mesh.area_faces
        small_area_faces = np.where(face_areas < np.percentile(face_areas, 30))[0]
        
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
                    feature = self._create_feature_from_faces(cluster_faces, RotationalFeatureType.KEYWAY)
                    
                    if feature:
                        # 根据长宽比判断是否为键槽
                        bbox = feature.bounding_box
                        dimensions = [bbox['length'], bbox['width'], bbox['height']]
                        dimensions.sort()
                        
                        # 长宽比大于3:1认为是键槽
                        if dimensions[2] / dimensions[1] > 3.0:
                            # 设置尺寸属性
                            feature.length = dimensions[2]
                            feature.width = dimensions[1]
                            feature.depth = dimensions[0]
                            features.append(feature)
        
        print(f"识别到 {len(features)} 个键槽特征")
        return features
    
    def identify_threads(self) -> List[RotationalFeature]:
        """识别螺纹特征"""
        features = []
        
        # 螺纹具有周期性的螺旋结构，可以通过曲率变化识别
        try:
            # 计算顶点曲率
            vertex_curvature = trimesh.curvature.discrete_mean_curvature_measure(
                self.mesh, self.mesh.vertices, 0.1)
            
            # 寻找曲率变化较大的区域
            curvature_std = np.std(vertex_curvature)
            high_variation_vertices = np.where(np.abs(vertex_curvature) > curvature_std)[0]
            
            if len(high_variation_vertices) > 0:
                # 获取相关的面
                thread_candidate_faces = []
                for face_idx, face in enumerate(self.mesh.faces):
                    if any(vertex in high_variation_vertices for vertex in face):
                        thread_candidate_faces.append(face_idx)
                
                # 聚类螺纹候选面
                if thread_candidate_faces:
                    thread_features = self._cluster_faces(thread_candidate_faces, RotationalFeatureType.THREAD)
                    features.extend(thread_features)
                        
        except Exception as e:
            print(f"螺纹特征识别过程中出现错误: {e}")
            
        print(f"识别到 {len(features)} 个螺纹特征")
        return features
    
    def identify_grooves(self) -> List[RotationalFeature]:
        """识别各种切槽特征（外圆切槽、端面切槽、内孔切槽、内孔端面切槽）"""
        features = []
        
        # 切槽是狭小的凹陷区域
        # 计算每个面的面积
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
                    feature = self._create_feature_from_faces(cluster_faces, RotationalFeatureType.OUTER_GROOVE)
                    
                    if feature:
                        # 根据位置和方向分类切槽类型
                        classified_feature = self._classify_groove_type(feature)
                        features.append(classified_feature)
        
        print(f"识别到 {len(features)} 个切槽特征")
        return features
    
    def _classify_groove_type(self, feature: RotationalFeature) -> RotationalFeature:
        """分类切槽类型"""
        # 根据特征位置和几何关系分类
        centroid = feature.centroid
        bbox = feature.bounding_box
        
        # 计算到旋转轴的距离
        distance_to_axis = np.linalg.norm(
            centroid - np.dot(centroid, self.axis_direction) * self.axis_direction)
        
        # 判断是外圆切槽还是内孔切槽
        # 简化处理：通过特征是否在模型内部判断
        mesh_centroid = np.mean(self.mesh.vertices, axis=0)
        distance_to_mesh_center = np.linalg.norm(centroid - mesh_centroid)
        
        # 获取模型的平均半径
        avg_radius = np.mean([np.linalg.norm(v - (np.dot(v, self.axis_direction) * self.axis_direction)) 
                             for v in self.mesh.vertices])
        
        if distance_to_mesh_center < avg_radius * 0.8:
            # 在内部，可能是内孔切槽
            feature.is_inner = True
            # 判断是否在端面附近
            axis_position = np.dot(centroid, self.axis_direction)
            mesh_bounds_on_axis = [
                np.dot(np.mean(self.mesh.vertices[self.mesh.faces], axis=1), self.axis_direction).min(),
                np.dot(np.mean(self.mesh.vertices[self.mesh.faces], axis=1), self.axis_direction).max()
            ]
            
            if abs(axis_position - mesh_bounds_on_axis[0]) < 2.0 or \
               abs(axis_position - mesh_bounds_on_axis[1]) < 2.0:
                feature.feature_type = RotationalFeatureType.INNER_HOLE_END_GROOVE
            else:
                feature.feature_type = RotationalFeatureType.INNER_HOLE_GROOVE
        else:
            # 在外部，可能是外圆切槽
            # 判断是否在端面附近
            face_normals = [self.mesh.face_normals[f] for f in feature.faces[:min(5, len(feature.faces))]]
            avg_normal = np.mean(face_normals, axis=0)
            
            # 如果法向量与轴向接近垂直，则为端面切槽
            if np.abs(np.dot(avg_normal, self.axis_direction)) < 0.5:
                feature.feature_type = RotationalFeatureType.END_FACE_GROOVE
            else:
                feature.feature_type = RotationalFeatureType.OUTER_GROOVE
                
        # 设置尺寸属性
        feature.length = max(bbox['length'], bbox['width'], bbox['height'])
        feature.depth = min(bbox['length'], bbox['width'], bbox['height'])
        
        return feature
    
    def _cluster_faces(self, face_indices: List[int], feature_type: RotationalFeatureType) -> List[RotationalFeature]:
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
    
    def _create_feature_from_faces(self, face_indices: List[int], feature_type: RotationalFeatureType) -> RotationalFeature:
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
        
        # 计算法向量（使用前几个面的法向量平均值作为代表）
        normals = [self.mesh.face_normals[idx] for idx in face_indices[:min(5, len(face_indices))]]
        normal = np.mean(normals, axis=0) if normals else None
        if normal is not None:
            normal = normal / np.linalg.norm(normal)
        
        return RotationalFeature(
            feature_type=feature_type,
            faces=face_indices,
            vertices=unique_vertices,
            centroid=centroid,
            bounding_box=bounding_box,
            normal=normal
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
    
    def recognize_all_features(self) -> List[RotationalFeature]:
        """识别所有回转体零件特征"""
        if self.mesh is None:
            raise ValueError("请先加载3D模型")
            
        print("开始识别回转体零件特征...")
        self.features = []
        
        # 1. 识别端面特征
        end_face_features = self.identify_end_faces()
        self.features.extend(end_face_features)
        
        # 2. 识别外圆特征
        outer_cylinder_features = self.identify_outer_cylinders()
        self.features.extend(outer_cylinder_features)
        
        # 3. 识别孔和镗孔特征
        hole_features = self.identify_holes_and_bored_holes()
        self.features.extend(hole_features)
        
        # 4. 识别键槽特征
        keyway_features = self.identify_keyways()
        self.features.extend(keyway_features)
        
        # 5. 识别螺纹特征
        thread_features = self.identify_threads()
        self.features.extend(thread_features)
        
        # 6. 识别切槽特征
        groove_features = self.identify_grooves()
        self.features.extend(groove_features)
        
        print(f"总共识别到 {len(self.features)} 个回转体零件特征")
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
        print(f"回转体零件特征信息已导出到 {file_path}")
    
    def visualize_features(self):
        """可视化识别的特征"""
        if not self.features:
            print("没有特征可可视化")
            return
            
        # 为每种特征类型分配颜色
        feature_colors = {
            RotationalFeatureType.KEYWAY: [1, 0, 0, 0.7],              # 红色 - 键槽
            RotationalFeatureType.THREAD: [0, 1, 0, 0.7],              # 绿色 - 螺纹
            RotationalFeatureType.HOLE: [0, 0, 1, 0.7],                # 蓝色 - 孔
            RotationalFeatureType.END_FACE: [1, 1, 0, 0.7],            # 黄色 - 端面
            RotationalFeatureType.OUTER_CYLINDER: [1, 0, 1, 0.7],      # 紫色 - 外圆
            RotationalFeatureType.BORED_HOLE: [0, 1, 1, 0.7],          # 青色 - 镗孔
            RotationalFeatureType.OUTER_GROOVE: [0.5, 0, 0.5, 0.7],    # 紫红色 - 外圆切槽
            RotationalFeatureType.END_FACE_GROOVE: [1, 0.5, 0, 0.7],   # 橙色 - 端面切槽
            RotationalFeatureType.INNER_HOLE_GROOVE: [0, 0.5, 0, 0.7], # 深绿色 - 内孔切槽
            RotationalFeatureType.INNER_HOLE_END_GROOVE: [0.5, 0.5, 0.5, 0.7]  # 灰色 - 内孔端面切槽
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
    # 创建回转体零件特征识别Agent
    agent = RotationalFeatureAgent()
    
    # 加载测试模型（实际使用时替换为真实回转体零件模型路径）
    # 这里我们创建一个简单的测试模型
    print("创建测试回转体零件模型...")
    
    # 创建基本圆柱作为主体
    cylinder = trimesh.creation.cylinder(radius=25, height=80)
    
    # 添加一个孔
    hole = trimesh.creation.cylinder(radius=10, height=85)
    result_mesh = cylinder.difference(hole, engine='scad')
    
    # 如果OpenSCAD不可用，使用原始圆柱体
    if result_mesh is None:
        result_mesh = cylinder
        print("警告: 无法创建带孔的圆柱，使用基本圆柱")
    
    agent.mesh = result_mesh
    
    # 预处理网格
    agent.preprocess_mesh()
    
    # 识别所有特征
    features = agent.recognize_all_features()
    
    # 获取统计信息
    stats = agent.get_feature_statistics()
    print("\n=== 回转体零件特征识别结果 ===")
    print(f"总特征数: {stats['total_features']}")
    print("特征类型分布:")
    for feature_type, count in stats['feature_types'].items():
        print(f"  {feature_type}: {count}")
    
    # 导出特征信息
    agent.export_features_to_json("rotational_features.json")
    
    # 可视化结果（如果环境支持）
    try:
        agent.visualize_features()
    except Exception as e:
        print(f"可视化失败: {e}")


if __name__ == "__main__":
    main()