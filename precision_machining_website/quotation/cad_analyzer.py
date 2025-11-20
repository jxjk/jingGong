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

# 尝试导入OpenCASCADE
try:
    from .opencascade_analyzer import analyze_with_opencascade, OCC_AVAILABLE
except ImportError:
    OCC_AVAILABLE = False
    print("提示: OpenCASCADE分析器不可用")

# 尝试导入FreeCAD
try:
    from .freecad_analyzer import analyze_with_freecad, FREECAD_AVAILABLE
except ImportError:
    FREECAD_AVAILABLE = False
    print("提示: FreeCAD分析器不可用")

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
                print(f"使用CadQuery成功加载模型: {self.file_path}")
                return
            
            # 使用trimesh处理通用3D格式
            if TRIMESH_AVAILABLE:
                self.model = trimesh.load(self.file_path)
                print(f"使用Trimesh成功加载模型: {self.file_path}")
                return
                
            # 使用numpy-stl处理STL文件
            if STL_AVAILABLE and self.file_extension in ['.stl']:
                self.model = mesh.Mesh.from_file(self.file_path)
                print(f"使用numpy-stl成功加载模型: {self.file_path}")
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
        
        # 打印调试信息
        print(f"开始分析模型: {self.file_path}")
        print(f"CADQUERY_AVAILABLE: {CADQUERY_AVAILABLE}")
        print(f"TRIMESH_AVAILABLE: {TRIMESH_AVAILABLE}")
        print(f"STL_AVAILABLE: {STL_AVAILABLE}")
        print(f"OCC_AVAILABLE: {OCC_AVAILABLE}")
        print(f"FREECAD_AVAILABLE: {FREECAD_AVAILABLE}")
        print(f"Model type: {type(self.model)}")
        print(f"File extension: {self.file_extension}")
        
        # 尝试使用不同方法分析模型
        try:
            if CADQUERY_AVAILABLE and hasattr(self.model, 'val') and self.file_extension in ['.step', '.stp']:
                print("使用CadQuery分析模型")
                features.update(self._analyze_with_cadquery())
            elif TRIMESH_AVAILABLE and hasattr(self.model, 'volume'):
                print("使用Trimesh分析模型")
                features.update(self._analyze_with_trimesh())
            elif STL_AVAILABLE and isinstance(self.model, mesh.Mesh):
                print("使用numpy-stl分析模型")
                features.update(self._analyze_with_stl())
            else:
                # 如果没有合适的分析器，尝试通用方法
                print("警告: 没有合适的分析器处理此文件格式，尝试通用方法")
                features.update(self._analyze_generic())
        except Exception as e:
            print(f"分析模型时出错: {e}")
            # 即使分析失败，也尝试提取基本特征
            features.update(self._analyze_generic())
        
        # 使用OpenCASCADE进行高级分析（如果可用）
        if OCC_AVAILABLE and self.file_extension in ['.stl']:
            try:
                print("使用OpenCASCADE进行高级分析")
                oc_features = analyze_with_opencascade(self.file_path)
                # 合并OpenCASCADE分析结果
                features.update({
                    'oc_curved_surfaces': oc_features['complexity_features']['curved_surfaces'],
                    'oc_sharp_edges': oc_features['complexity_features']['sharp_edges'],
                    'oc_holes': oc_features['complexity_features']['holes'],
                    'oc_undercuts': oc_features['complexity_features']['undercuts'],
                    'oc_min_tolerance': oc_features['min_tolerance'],
                    'oc_estimated_weight': oc_features['estimated_weight'],
                    'oc_machining_difficulty': oc_features['machining_difficulty'],
                    'min_radius': oc_features['min_radius'],  # 使用OpenCASCADE的结果覆盖默认值
                    'min_tool_diameter': oc_features['min_tool_diameter'],  # 使用OpenCASCADE的结果
                })
            except Exception as e:
                print(f"OpenCASCADE分析出错: {e}")
        
        # 使用FreeCAD进行分析（如果可用）
        if FREECAD_AVAILABLE and self.file_extension in ['.step', '.stp', '.stl', '.iges', '.igs']:
            try:
                print("使用FreeCAD进行分析")
                fc_features = analyze_with_freecad(self.file_path)
                # 合并FreeCAD分析结果（优先级高于默认值，但低于OpenCASCADE）
                if 'min_radius' not in features or features.get('min_radius') == 0.5:
                    features['min_radius'] = fc_features['min_radius']
                    features['min_tool_diameter'] = fc_features['min_tool_diameter']
                
                # 添加FreeCAD特定特征
                features.update({
                    'fc_fillet_count': fc_features['fillet_count'],
                    'fc_sharp_edges': fc_features['sharp_edges'],
                })
            except Exception as e:
                print(f"FreeCAD分析出错: {e}")
        
        # 添加制造相关特征
        try:
            features.update(self._calculate_manufacturing_features(features))
        except Exception as e:
            print(f"计算制造特征时出错: {e}")
        
        print(f"分析完成，提取到的特征: {features}")
        return features
    
    def _analyze_generic(self):
        """
        通用分析方法，尝试从任意模型中提取基本特征
        """
        features = {}
        try:
            # 如果模型存在，尝试获取基本信息
            if self.model is not None:
                # 尝试获取文件大小作为简单特征
                try:
                    file_size = os.path.getsize(self.file_path)
                    # 简单地将文件大小转换为复杂度评分
                    features['complexity_score'] = min(5.0, max(1.0, file_size / 100000.0))
                except:
                    pass
        except Exception as e:
            print(f"通用分析方法出错: {e}")
        return features
    
    def _analyze_with_cadquery(self):
        """
        使用CadQuery分析CAD模型
        """
        features = {}
        
        try:
            # 获取模型实体
            shape = self.model.vals()[0]  # 获取第一个实体
            
            # 计算体积 (转换为立方厘米)
            volume = shape.Volume()
            if volume is not None:
                features['volume'] = volume / 1000.0
            
            # 计算表面积 (转换为平方厘米)
            area = shape.Area()
            if area is not None:
                features['surface_area'] = area / 100.0
            
            # 获取包围盒
            bbox = shape.BoundingBox()
            if bbox is not None:
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
            import traceback
            traceback.print_exc()
        
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
            # 只有在还没有最小拐角半径时才添加占位值
            if 'min_radius' not in base_features:
                features['min_radius'] = None  # 无默认值
            
            # 只有在还没有最小刀具直径且有最小半径时才计算
            if 'min_tool_diameter' not in base_features and base_features.get('min_radius') is not None:
                features['min_tool_diameter'] = base_features['min_radius'] * 2.0
            elif 'min_tool_diameter' not in base_features and features.get('min_radius') is not None:
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
            
            # 基于最小拐角半径的难度调整（只有在有实际值时才调整）
            min_radius = base_features.get('min_radius', features.get('min_radius'))
            if min_radius is not None:
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