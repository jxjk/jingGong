import numpy as np
import trimesh
from sklearn.cluster import DBSCAN
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import json


class MoldFeatureType(Enum):
    CORE = "core"                     # 凸模/型芯
    CAVITY = "cavity"                 # 凹模/型腔
    PARTING_LINE = "parting_line"     # 分型线
    PARTING_SURFACE = "parting_surface" # 分型面
    RUNNER = "runner"                 # 流道
    GATE = "gate"                     # 浇口
    COOLING_CHANNEL = "cooling_channel" # 冷却水道
    EJECTOR_PIN = "ejector_pin"       # 顶针
    VENT = "vent"                     # 排气槽


@dataclass
class MoldFeature:
    """模具特征数据类"""
    feature_type: MoldFeatureType
    faces: List[int]                  # 特征包含的面
    vertices: np.ndarray              # 特征包含的顶点
    centroid: np.ndarray              # 特征中心点
    bounding_box: Dict[str, float]    # 边界框尺寸
    normal: np.ndarray = None         # 主要法向量
    depth: float = 0.0                # 深度
    radius: float = None              # 半径
    length: float = None              # 长度
    width: float = None               # 宽度
    volume: float = None              # 体积
    
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
            "radius": self.radius,
            "length": self.length,
            "width": self.width,
            "volume": self.volume
        }


class MoldFeatureAgent:
    """模具CAM特征识别Agent"""
    
    def __init__(self):
        self.mesh = None
        self.features = []
        self.parting_plane = None
        
    def load_mesh(self, file_path: str) -> bool:
        """加载3D模型文件"""
        try:
            self.mesh = trimesh.load(file_path)
            print(f"模具模型加载成功: {len(self.mesh.vertices)} 顶点, {len(self.mesh.faces)} 面")
            return True
        except Exception as e:
            print(f"模具模型加载失败: {e}")
            return False
    
    def preprocess_mesh(self):
        """预处理网格数据"""
        if self.mesh is None:
            raise ValueError("请先加载3D模型")
        
        # 确保网格是水密的
        if not self.mesh.is_watertight:
            print("警告: 网格不是水密的，可能影响特征识别准确性")
            
        # 计算法向量
        if not hasattr(self.mesh, 'face_normals') or self.mesh.face_normals.shape[0] == 0:
            self.mesh.compute_face_normals()
            
        if not hasattr(self.mesh, 'vertex_normals') or self.mesh.vertex_normals.shape[0] == 0:
            self.mesh.compute_vertex_normals()
            
        print("网格预处理完成")
    
    def identify_parting_line_and_surface(self) -> List[MoldFeature]:
        """识别分型线和分型面"""
        features = []
        
        # 计算模型的最佳分型方向（通常是Z轴方向）
        # 在实际应用中，这可能需要更复杂的算法来确定最佳分型方向
        best_parting_direction = np.array([0, 0, 1])
        
        # 根据法向量与分型方向的角度来识别分型面
        # 分型面通常是接近水平的面
        parting_surface_faces = []
        parting_line_faces = []
        
        angle_threshold = np.cos(np.radians(30))  # 30度阈值
        
        for i, normal in enumerate(self.mesh.face_normals):
            # 计算法向量与分型方向的夹角余弦值
            cos_angle = np.abs(np.dot(normal, best_parting_direction))
            
            # 如果接近平行，则可能是分型面
            if cos_angle > angle_threshold:
                parting_surface_faces.append(i)
            # 如果接近垂直，则可能是分型线附近的面
            elif cos_angle < np.cos(np.radians(80)):
                parting_line_faces.append(i)
                
        # 聚类分型面
        if parting_surface_faces:
            parting_surface_features = self._cluster_faces(parting_surface_faces, MoldFeatureType.PARTING_SURFACE)
            features.extend(parting_surface_features)
            
        # 聚类分型线附近面
        if parting_line_faces:
            parting_line_features = self._cluster_faces(parting_line_faces, MoldFeatureType.PARTING_LINE)
            features.extend(parting_line_features)
            
        print(f"识别到 {len(features)} 个分型相关特征")
        return features
    
    def identify_core_and_cavity(self) -> List[MoldFeature]:
        """识别凸模(core)和凹模(cavity)"""
        features = []
        
        if not self.parting_plane:
            # 简单地以模型的中点作为分型面
            z_mid = (self.mesh.bounds[0][2] + self.mesh.bounds[1][2]) / 2
            
            # 上部为凸模，下部为凹模
            upper_faces = []  # 凸模面
            lower_faces = []  # 凹模面
            
            face_centers = np.mean(self.mesh.vertices[self.mesh.faces], axis=1)
            
            for i, center in enumerate(face_centers):
                if center[2] >= z_mid:
                    upper_faces.append(i)
                else:
                    lower_faces.append(i)
                    
            # 聚类并创建特征
            if upper_faces:
                core_features = self._cluster_faces(upper_faces, MoldFeatureType.CORE)
                features.extend(core_features)
                
            if lower_faces:
                cavity_features = self._cluster_faces(lower_faces, MoldFeatureType.CAVITY)
                features.extend(cavity_features)
                
        print(f"识别到 {len(features)} 个型芯/型腔特征")
        return features
    
    def identify_runners_and_gates(self) -> List[MoldFeature]:
        """识别流道和浇口"""
        features = []
        
        # 流道和浇口通常具有特定的几何特征：
        # 1. 相对较小的横截面
        # 2. 连接到型腔或其它流道
        # 3. 有一定长度
        
        # 计算每个面的面积
        face_areas = self.mesh.area_faces
        
        # 寻找相对较小的面
        median_area = np.median(face_areas)
        small_faces = np.where(face_areas < median_area * 0.1)[0]
        
        if len(small_faces) > 0:
            # 聚类小面形成流道特征
            runner_features = self._cluster_faces(small_faces.tolist(), MoldFeatureType.RUNNER)
            
            # 进一步分析可能的浇口（非常小的面）
            tiny_faces = np.where(face_areas < median_area * 0.01)[0]
            if len(tiny_faces) > 0:
                gate_features = self._cluster_faces(tiny_faces.tolist(), MoldFeatureType.GATE)
                features.extend(gate_features)
                
            features.extend(runner_features)
            
        print(f"识别到 {len(features)} 个流道/浇口特征")
        return features
    
    def identify_cooling_channels(self) -> List[MoldFeature]:
        """识别冷却水道"""
        features = []
        
        # 冷却水道的特点：
        # 1. 管状结构
        # 2. 贯穿模型
        # 3. 相对较大的内径
        
        # 使用曲率分析寻找管状特征
        try:
            # 计算顶点曲率
            vertex_curvature = trimesh.curvature.discrete_mean_curvature_measure(
                self.mesh, self.mesh.vertices, 0.05)
            
            # 寻找曲率适中的区域（管壁）
            curvature_threshold_low = np.percentile(vertex_curvature, 30)
            curvature_threshold_high = np.percentile(vertex_curvature, 70)
            
            medium_curvature_vertices = np.where(
                (vertex_curvature >= curvature_threshold_low) & 
                (vertex_curvature <= curvature_threshold_high)
            )[0]
            
            if len(medium_curvature_vertices) > 0:
                # 获取相关的面
                channel_faces = []
                for face_idx, face in enumerate(self.mesh.faces):
                    if any(vertex in medium_curvature_vertices for vertex in face):
                        channel_faces.append(face_idx)
                        
                if channel_faces:
                    channel_features = self._cluster_faces(channel_faces, MoldFeatureType.COOLING_CHANNEL)
                    features.extend(channel_features)
                    
        except Exception as e:
            print(f"冷却水道识别过程中出现错误: {e}")
            
        print(f"识别到 {len(features)} 个冷却水道特征")
        return features
    
    def identify_ejector_pins_and_vents(self) -> List[MoldFeature]:
        """识别顶针和排气槽"""
        features = []
        
        # 顶针特点：小而深的孔
        # 排气槽特点：浅而窄的沟槽
        
        # 计算面的法向量变化来识别这些特征
        face_normals = self.mesh.face_normals
        
        # 寻找法向量变化剧烈的区域
        boundary_edges = self.mesh.edges_unique
        edge_angles = []
        
        for edge in boundary_edges:
            # 获取共享此边的面
            faces_shared = []
            for i, face in enumerate(self.mesh.faces):
                if edge[0] in face and edge[1] in face:
                    faces_shared.append(i)
                    
            if len(faces_shared) == 2:
                # 计算两面间的角度
                normal1 = face_normals[faces_shared[0]]
                normal2 = face_normals[faces_shared[1]]
                angle = np.arccos(np.clip(np.dot(normal1, normal2), -1.0, 1.0))
                edge_angles.append(angle)
            else:
                edge_angles.append(0)
                
        # 寻找锐角边缘（可能是排气槽或顶针痕迹）
        sharp_edges = np.where(np.array(edge_angles) > np.radians(60))[0]
        
        if len(sharp_edges) > 0:
            # 获取相关的面
            ejector_vent_faces = []
            for edge_idx in sharp_edges[:50]:  # 限制处理数量
                edge = boundary_edges[edge_idx]
                for i, face in enumerate(self.mesh.faces):
                    if edge[0] in face and edge[1] in face:
                        ejector_vent_faces.append(i)
                        
            if ejector_vent_faces:
                # 简单区分顶针和排气槽（基于面积）
                face_areas = self.mesh.area_faces
                small_faces = [f for f in ejector_vent_faces if face_areas[f] < np.median(face_areas) * 0.05]
                large_faces = [f for f in ejector_vent_faces if face_areas[f] >= np.median(face_areas) * 0.05]
                
                if small_faces:
                    pin_features = self._cluster_faces(small_faces, MoldFeatureType.EJECTOR_PIN)
                    features.extend(pin_features)
                    
                if large_faces:
                    vent_features = self._cluster_faces(large_faces, MoldFeatureType.VENT)
                    features.extend(vent_features)
                    
        print(f"识别到 {len(features)} 个顶针/排气槽特征")
        return features
    
    def _cluster_faces(self, face_indices: List[int], feature_type: MoldFeatureType) -> List[MoldFeature]:
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
        for i in range(min(len(points), 100)):  # 限制样本数量以提高性能
            for j in range(i+1, min(len(points), 100)):
                distances.append(np.linalg.norm(points[i] - points[j]))
                
        if distances:
            return np.median(distances) * 0.5
        else:
            return 1.0
    
    def _create_feature_from_faces(self, face_indices: List[int], feature_type: MoldFeatureType) -> MoldFeature:
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
        radius = None
        length = None
        width = None
        volume = None
        
        # 根据特征类型计算特定属性
        if feature_type in [MoldFeatureType.COOLING_CHANNEL]:
            # 对于管状特征，估算半径
            radius = min(bounding_box.get('length', 0), 
                         bounding_box.get('width', 0),
                         bounding_box.get('height', 0)) / 2
            
        if feature_type in [MoldFeatureType.RUNNER, MoldFeatureType.GATE]:
            # 对于流道特征，计算长度
            length = max(bounding_box.get('length', 0), 
                         bounding_box.get('width', 0),
                         bounding_box.get('height', 0))
                         
        return MoldFeature(
            feature_type=feature_type,
            faces=face_indices,
            vertices=unique_vertices,
            centroid=centroid,
            bounding_box=bounding_box,
            normal=normal,
            depth=depth,
            radius=radius,
            length=length,
            width=width,
            volume=volume
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
    
    def recognize_all_features(self) -> List[MoldFeature]:
        """识别所有模具特征"""
        if self.mesh is None:
            raise ValueError("请先加载3D模型")
            
        print("开始识别模具特征...")
        self.features = []
        
        # 1. 识别分型线和分型面
        parting_features = self.identify_parting_line_and_surface()
        self.features.extend(parting_features)
        
        # 2. 识别凸模和凹模
        core_cavity_features = self.identify_core_and_cavity()
        self.features.extend(core_cavity_features)
        
        # 3. 识别流道和浇口
        runner_gate_features = self.identify_runners_and_gates()
        self.features.extend(runner_gate_features)
        
        # 4. 识别冷却水道
        cooling_features = self.identify_cooling_channels()
        self.features.extend(cooling_features)
        
        # 5. 识别顶针和排气槽
        ejector_vent_features = self.identify_ejector_pins_and_vents()
        self.features.extend(ejector_vent_features)
        
        print(f"总共识别到 {len(self.features)} 个模具特征")
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
        print(f"模具特征信息已导出到 {file_path}")
    
    def visualize_features(self):
        """可视化识别的特征"""
        if not self.features:
            print("没有特征可可视化")
            return
            
        # 为每种特征类型分配颜色
        feature_colors = {
            MoldFeatureType.CORE: [1, 0, 0, 0.7],           # 红色 - 凸模
            MoldFeatureType.CAVITY: [0, 1, 0, 0.7],         # 绿色 - 凹模
            MoldFeatureType.PARTING_LINE: [0, 0, 1, 0.7],   # 蓝色 - 分型线
            MoldFeatureType.PARTING_SURFACE: [1, 1, 0, 0.7], # 黄色 - 分型面
            MoldFeatureType.RUNNER: [1, 0, 1, 0.7],         # 紫色 - 流道
            MoldFeatureType.GATE: [0, 1, 1, 0.7],           # 青色 - 浇口
            MoldFeatureType.COOLING_CHANNEL: [0.5, 0, 0.5, 0.7], # 紫红色 - 冷却水道
            MoldFeatureType.EJECTOR_PIN: [1, 0.5, 0, 0.7],  # 橙色 - 顶针
            MoldFeatureType.VENT: [0.5, 0.5, 0.5, 0.7]      # 灰色 - 排气槽
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
    # 创建模具特征识别Agent
    agent = MoldFeatureAgent()
    
    # 加载测试模型（实际使用时替换为真实模具模型路径）
    # 这里我们创建一个简单的测试模型
    print("创建测试模具模型...")
    
    # 创建基本立方体作为模具主体
    mold_base = trimesh.creation.box(extents=[100, 100, 50])
    
    # 添加一个简单的型腔
    cavity = trimesh.creation.box(extents=[30, 30, 20])
    cavity.apply_translation([0, 0, 25])  # 移动到上半部分
    
    # 执行布尔差集操作创建带型腔的模具
    mold_mesh = mold_base.difference(cavity, engine='scad')
    
    # 如果OpenSCAD不可用，使用原始立方体
    if mold_mesh is None:
        mold_mesh = mold_base
        print("警告: 无法创建带型腔的模具，使用基本立方体")
    
    agent.mesh = mold_mesh
    
    # 预处理网格
    agent.preprocess_mesh()
    
    # 识别所有特征
    features = agent.recognize_all_features()
    
    # 获取统计信息
    stats = agent.get_feature_statistics()
    print("\n=== 模具特征识别结果 ===")
    print(f"总特征数: {stats['total_features']}")
    print("特征类型分布:")
    for feature_type, count in stats['feature_types'].items():
        print(f"  {feature_type}: {count}")
    
    # 导出特征信息
    agent.export_features_to_json("mold_features.json")
    
    # 可视化结果（如果环境支持）
    try:
        agent.visualize_features()
    except Exception as e:
        print(f"可视化失败: {e}")


if __name__ == "__main__":
    main()