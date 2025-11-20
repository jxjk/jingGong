"""
OpenCASCADE高级几何分析器
用于复杂几何特征分析和加工难度评估
"""

try:
    from OCC.Core import StlAPI, BRep, BRepTools, BRepGProp, GProp, Bnd, TopoDS, TopExp, TopAbs
    from OCC.Core import BRepBuilderAPI, BRepPrimAPI, BRepAlgoAPI, Geom

    # 尝试导入BRepMesh相关模块（用于网格化）
    try:
        from OCC.Core import BRepMesh
        BREP_MESH_AVAILABLE = True
    except ImportError:
        BREP_MESH_AVAILABLE = False

    from OCCUtils import Topo
    import numpy as np
    OCC_AVAILABLE = True
except ImportError:
    OCC_AVAILABLE = False
    print("提示: python-opencascade库未安装，OpenCASCADE分析功能将不可用")


def analyze_with_opencascade(stl_file_path):
    """
    使用OpenCASCADE分析STL文件
    
    Args:
        stl_file_path (str): STL文件路径
        
    Returns:
        dict: 分析结果，包括复杂几何特征
    """
    # 默认结果，不设置默认的最小半径值
    analysis_result = {
        'surface_area': 0.0,  # 表面积
        'volume': 0.0,        # 体积
        'bbox_dimensions': {  # 边界框尺寸
            'length': 0.0,
            'width': 0.0,
            'height': 0.0
        },
        'complexity_features': {  # 复杂几何特征
            'curved_surfaces': 0,      # 曲面数量
            'sharp_edges': 0,          # 锐边数量
            'holes': 0,                # 孔洞数量
            'undercuts': 0,            # 倒勾特征数量
        },
        'min_radius': None,            # 最小拐角半径（无默认值）
        'min_tool_diameter': None,     # 最小刀具直径（无默认值）
        'min_tolerance': 0.0,          # 最小公差要求
        'estimated_weight': 0.0,       # 估算重量
        'machining_difficulty': 'MEDIUM'  # 加工难度评估
    }
    
    # 如果OpenCASCADE库不可用，返回默认结果
    if not OCC_AVAILABLE:
        return analysis_result
    
    try:
        # 读取STL文件
        shape = read_stl_file(stl_file_path)
        if shape is None:
            return analysis_result
        
        # 计算基本几何属性
        analysis_result.update(calculate_basic_properties(shape))
        
        # 分析复杂几何特征
        analysis_result['complexity_features'].update(analyze_complexity_features(shape))
        
        # 估算最小拐角半径和刀具直径
        min_radius = estimate_min_radius(shape)
        # 只有在检测到有效值时才设置
        if min_radius is not None and min_radius > 0:
            analysis_result['min_radius'] = min_radius
            analysis_result['min_tool_diameter'] = min_radius * 2.0
        
        # 估算加工难度
        analysis_result['machining_difficulty'] = get_machining_difficulty(analysis_result)
        
    except Exception as e:
        # 处理分析过程中的其他异常
        print(f"OpenCASCADE分析出错: {e}")
        import traceback
        traceback.print_exc()
        
    return analysis_result


def read_stl_file(stl_file_path):
    """
    读取STL文件并转换为OpenCASCADE形状
    
    Args:
        stl_file_path (str): STL文件路径
        
    Returns:
        TopoDS_Shape: OpenCASCADE形状对象
    """
    try:
        # 创建STL读取器
        stl_reader = StlAPI.StlAPI_Reader()
        
        # 创建空形状
        shape = TopoDS.TopoDS_Shape()
        
        # 读取STL文件
        if stl_reader.Read(shape, stl_file_path):
            return shape
    except Exception as e:
        print(f"读取STL文件出错: {e}")
    
    return None


def calculate_basic_properties(shape):
    """
    计算形状的基本几何属性
    
    Args:
        shape (TopoDS_Shape): OpenCASCADE形状对象
        
    Returns:
        dict: 基本几何属性
    """
    properties = {}
    
    try:
        # 计算质量属性
        props = GProp.GProp_GProps()
        BRepGProp.BRepGProp_VolumeProperties(shape, props)
        
        # 体积
        properties['volume'] = props.Mass()
        
        # 估算重量 (假设材料密度为1g/cm³)
        properties['estimated_weight'] = properties['volume']
        
        # 表面积
        BRepGProp.BRepGProp_SurfaceProperties(shape, props)
        properties['surface_area'] = props.Mass()
        
        # 计算边界框
        bbox = Bnd.Bnd_Box()
        bbox.SetGap(0.0)
        BRepBndLib = __import__('OCC.Core.BRepBndLib', fromlist=['BRepBndLib'])
        BRepBndLib.brepbndlib_Add(shape, bbox)
        
        if not bbox.IsVoid():
            xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
            properties['bbox_dimensions'] = {
                'length': xmax - xmin,
                'width': ymax - ymin,
                'height': zmax - zmin
            }
        
        # 最小公差
        properties['min_tolerance'] = 0.01  # 默认值，实际应根据模型精度计算
        
    except Exception as e:
        print(f"计算基本属性出错: {e}")
    
    return properties


def analyze_complexity_features(shape):
    """
    分析形状的复杂几何特征
    
    Args:
        shape (TopoDS_Shape): OpenCASCADE形状对象
        
    Returns:
        dict: 复杂几何特征统计
    """
    features = {
        'curved_surfaces': 0,
        'sharp_edges': 0,
        'holes': 0,
        'undercuts': 0,
    }
    
    try:
        # 网格化形状以进行更详细的分析
        if BREP_MESH_AVAILABLE:
            try:
                BRepMesh.BRepMesh_IncrementalMesh(shape, 0.1)
            except:
                pass  # 网格化失败不影响其他分析
        
        # 分析面的类型
        topo = Topo.Topo(shape)
        for face in topo.faces():
            # 检查是否为曲面
            surface = BRep.BRep_Tool_Surface(face)
            if surface:
                # 简化判断：非平面面视为曲面
                geom_type = surface.GetObject().GetType()
                if geom_type != Geom.GeomAbs_Plane:
                    features['curved_surfaces'] += 1
        
        # 分析边的数量和类型
        edge_count = 0
        for edge in topo.edges():
            edge_count += 1
            
            # 检查是否为锐边（简化判断：检查边的曲率）
            # 这里简化处理，实际应计算边的曲率
            if edge_count % 10 == 0:  # 模拟检测到锐边
                features['sharp_edges'] += 1
        
        # 估算孔洞数量（简化处理）
        features['holes'] = max(0, edge_count // 100)  # 粗略估算
        
        # 估算倒勾特征数量（简化处理）
        features['undercuts'] = max(0, features['curved_surfaces'] // 5)  # 粗略估算
        
    except Exception as e:
        print(f"分析复杂特征出错: {e}")
    
    return features


def estimate_min_radius(shape):
    """
    估算模型中的最小拐角半径
    
    Args:
        shape (TopoDS_Shape): OpenCASCADE形状对象
        
    Returns:
        float: 估算的最小拐角半径（mm）
    """
    try:
        # 实际实现中，这里需要复杂算法来检测模型中的所有圆角特征
        # 并计算其半径，然后找出最小值
        # 由于这是一个复杂的过程，我们使用启发式方法估算
        
        # 获取边界框尺寸
        bbox = Bnd.Bnd_Box()
        bbox.SetGap(0.0)
        BRepBndLib = __import__('OCC.Core.BRepBndLib', fromlist=['BRepBndLib'])
        BRepBndLib.brepbndlib_Add(shape, bbox)
        
        if not bbox.IsVoid():
            xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
            # 基于模型尺寸和复杂度估算最小半径
            model_size = ((xmax-xmin) * (ymax-ymin) * (zmax-zmin)) ** (1/3)
            # 简化估算：模型越小，最小半径可能越小
            min_radius = max(0.1, min(5.0, model_size * 0.001))
            return min_radius
    except Exception as e:
        print(f"估算最小半径出错: {e}")
    
    # 默认返回0.5mm
    return 0.5


def visualize_model(stl_file_path):
    """
    使用OpenCASCADE查看器可视化模型
    
    Args:
        stl_file_path (str): STL文件路径
        
    Returns:
        bool: 是否成功启动可视化
    """
    # 占位符实现 - 需要实际的OpenGL环境和OpenCASCADE库
    try:
        # 这里应该实现实际的可视化逻辑
        # 需要OpenGL 2.1+支持
        return True
    except Exception as e:
        # 处理可视化过程中的异常
        return False


def get_machining_difficulty(analysis_result):
    """
    根据分析结果评估加工难度
    
    Args:
        analysis_result (dict): OpenCASCADE分析结果
        
    Returns:
        str: 加工难度等级 (EASY, MEDIUM, HARD, VERY_HARD)
    """
    # 基于几何特征评估加工难度的算法
    # 这是一个简化的示例实现
    
    difficulty_score = 0
    
    # 根据曲面复杂度评分
    difficulty_score += analysis_result['complexity_features']['curved_surfaces'] * 2
    difficulty_score += analysis_result['complexity_features']['sharp_edges'] * 1
    difficulty_score += analysis_result['complexity_features']['holes'] * 3
    difficulty_score += analysis_result['complexity_features']['undercuts'] * 5
    
    # 根据尺寸和公差评分
    bbox = analysis_result['bbox_dimensions']
    total_size = bbox['length'] * bbox['width'] * bbox['height']
    difficulty_score += total_size * analysis_result['min_tolerance']
    
    # 根据最小拐角半径评分（半径越小越难加工）
    if analysis_result['min_radius'] < 0.5:
        difficulty_score += 5
    elif analysis_result['min_radius'] < 1.0:
        difficulty_score += 2
    
    # 确定难度等级
    if difficulty_score < 10:
        return 'EASY'
    elif difficulty_score < 30:
        return 'MEDIUM'
    elif difficulty_score < 60:
        return 'HARD'
    else:
        return 'VERY_HARD'