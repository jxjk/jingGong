"""
FreeCAD模型分析器
用于分析模型中的最小拐角半径和最小刀具直径
"""

import os
import tempfile
import math
import sys

# 显式添加FreeCAD路径
FREECAD_PATH = r"D:\Program Files\FreeCAD 1.0\bin"
if os.path.exists(FREECAD_PATH) and FREECAD_PATH not in sys.path:
    sys.path.insert(0, FREECAD_PATH)
    print(f"已添加FreeCAD路径到系统路径: {FREECAD_PATH}")

# 尝试导入FreeCAD相关模块
FREECAD_AVAILABLE = False
FreeCAD = None
Part = None
Mesh = None
Draft = None

try:
    # 尝试导入FreeCAD模块
    import FreeCAD
    import Part
    import Mesh
    import Draft
    FREECAD_AVAILABLE = True
    print("成功导入FreeCAD模块")
except ImportError as e:
    print(f"导入FreeCAD模块失败: {e}")
    
    # 尝试其他可能的导入方式
    try:
        # 添加可能的子路径
        freecad_lib_path = os.path.join(FREECAD_PATH, "Library", "bin")
        if os.path.exists(freecad_lib_path) and freecad_lib_path not in sys.path:
            sys.path.insert(0, freecad_lib_path)
            
        import FreeCAD
        import Part
        import Mesh
        import Draft
        FREECAD_AVAILABLE = True
        print("通过备用路径成功导入FreeCAD模块")
    except ImportError as e2:
        print(f"通过备用路径导入FreeCAD模块也失败: {e2}")
        
        # 最后尝试通过环境变量
        try:
            if 'FREECAD_LIB' in os.environ:
                freecad_env_path = os.environ['FREECAD_LIB']
                if os.path.exists(freecad_env_path) and freecad_env_path not in sys.path:
                    sys.path.insert(0, freecad_env_path)
                    
                import FreeCAD
                import Part
                import Mesh
                import Draft
                FREECAD_AVAILABLE = True
                print("通过环境变量成功导入FreeCAD模块")
        except ImportError as e3:
            print(f"通过环境变量导入FreeCAD模块也失败: {e3}")

if not FREECAD_AVAILABLE:
    print("提示: 未找到FreeCAD库，FreeCAD分析功能将不可用")
    print("请确保:")
    print("1. 已安装FreeCAD")
    print("2. FreeCAD的bin目录已添加到系统PATH环境变量中")
    print("3. 或者设置FREECAD_LIB环境变量指向FreeCAD的bin目录")


def analyze_with_freecad(file_path):
    """
    使用FreeCAD分析模型文件中的最小拐角半径和最小刀具直径
    
    Args:
        file_path (str): 模型文件路径
        
    Returns:
        dict: 分析结果，包括最小拐角半径和最小刀具直径
    """
    # 默认结果，不设置默认的最小半径值
    analysis_result = {
        'min_radius': None,       # 最小拐角半径（无默认值）
        'min_tool_diameter': None, # 最小刀具直径（无默认值）
        'fillet_count': 0,        # 圆角数量
        'sharp_edges': 0,         # 锐边数量
    }
    
    # 如果FreeCAD库不可用，返回默认结果
    if not FREECAD_AVAILABLE:
        return analysis_result
    
    try:
        # 创建临时FreeCAD文档
        doc = FreeCAD.newDocument("Analysis")
        
        # 根据文件扩展名导入模型
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension in ['.step', '.stp']:
            # 导入STEP文件
            shape = Part.read(file_path)
            Part.show(shape)
        elif file_extension in ['.stl']:
            # 导入STL文件
            mesh = Mesh.Mesh(file_path)
            Mesh.show(mesh)
        elif file_extension in ['.iges', '.igs']:
            # 导入IGES文件
            shape = Part.read(file_path)
            Part.show(shape)
        elif file_extension in ['.brep', '.brp']:
            # 导入BREP文件
            shape = Part.read(file_path)
            Part.show(shape)
        else:
            # 不支持的文件格式
            print(f"不支持的文件格式: {file_extension}")
            FreeCAD.closeDocument("Analysis")
            return analysis_result
        
        # 分析模型中的圆角特征
        analysis_result.update(detect_fillet_features(doc))
        
        # 只有在检测到最小半径时才计算最小刀具直径
        if analysis_result.get('min_radius') is not None:
            analysis_result['min_tool_diameter'] = analysis_result['min_radius'] * 2.0
        
        # 关闭文档
        FreeCAD.closeDocument("Analysis")
        
    except Exception as e:
        # 处理分析过程中的其他异常
        print(f"FreeCAD分析出错: {e}")
        import traceback
        traceback.print_exc()
        
    return analysis_result


def detect_fillet_features(doc):
    """
    检测模型中的圆角特征
    
    Args:
        doc: FreeCAD文档对象
        
    Returns:
        dict: 圆角特征分析结果
    """
    result = {
        'min_radius': None,  # 无默认最小半径
        'fillet_count': 0,
        'sharp_edges': 0,
    }
    
    try:
        # 获取所有对象
        objects = doc.Objects
        
        min_radius = float('inf')
        fillet_count = 0
        sharp_edges = 0
        
        # 遍历所有对象
        for obj in objects:
            if hasattr(obj, 'Shape'):
                shape = obj.Shape
                
                # 检查边（edges）
                for edge in shape.Edges:
                    # 检查是否为圆角边
                    if is_fillet_edge(edge):
                        fillet_count += 1
                        # 获取圆角半径
                        radius = get_edge_radius(edge)
                        if radius and radius > 0:
                            min_radius = min(min_radius, radius)
                    else:
                        # 检查是否为锐边
                        if is_sharp_edge(edge):
                            sharp_edges += 1
                
        # 更新结果，只在检测到有效值时更新
        if min_radius != float('inf'):
            result['min_radius'] = min_radius
        result['fillet_count'] = fillet_count
        result['sharp_edges'] = sharp_edges
        
    except Exception as e:
        print(f"检测圆角特征时出错: {e}")
        import traceback
        traceback.print_exc()
    
    return result


def is_fillet_edge(edge):
    """
    判断边是否为圆角边
    
    Args:
        edge: FreeCAD边对象
        
    Returns:
        bool: 是否为圆角边
    """
    try:
        # 检查边是否为圆形或圆弧
        if hasattr(edge, 'Curve') and hasattr(edge.Curve, 'TypeId'):
            curve_type = edge.Curve.TypeId
            # 圆形或圆弧边可能是圆角
            if curve_type in ['Part::GeomCircle', 'Part::GeomArcOfCircle']:
                return True
    except Exception as e:
        print(f"判断圆角边时出错: {e}")
    
    return False


def is_sharp_edge(edge):
    """
    判断边是否为锐边
    
    Args:
        edge: FreeCAD边对象
        
    Returns:
        bool: 是否为锐边
    """
    try:
        # 检查边是否为直线
        if hasattr(edge, 'Curve') and hasattr(edge.Curve, 'TypeId'):
            curve_type = edge.Curve.TypeId
            if curve_type == 'Part::GeomLine':
                # 获取相邻面的法向量，计算夹角
                if hasattr(edge, 'facess') and len(edge.facess) >= 2:
                    faces = edge.facess
                    # 计算两个面法向量的夹角
                    try:
                        normal1 = faces[0].normalAt(0, 0)
                        normal2 = faces[1].normalAt(0, 0)
                        # 确保法向量是Vector类型
                        if hasattr(normal1, 'getAngle') and hasattr(normal2, 'getAngle'):
                            angle = math.degrees(normal1.getAngle(normal2))
                            # 如果夹角大于某个阈值，则认为是锐边
                            if angle > 80:  # 大于80度认为是锐边
                                return True
                    except Exception as e:
                        pass  # 如果计算失败，跳过此检查
    except Exception as e:
        print(f"判断锐边时出错: {e}")
    
    return False


def get_edge_radius(edge):
    """
    获取边的半径（如果是圆角边）
    
    Args:
        edge: FreeCAD边对象
        
    Returns:
        float: 半径值，如果无法获取则返回None
    """
    try:
        if hasattr(edge, 'Curve'):
            curve = edge.Curve
            if hasattr(curve, 'Radius'):
                return float(curve.Radius)
            elif hasattr(curve, 'Circle') and hasattr(curve.Circle, 'Radius'):
                return float(curve.Circle.Radius)
    except Exception as e:
        print(f"获取边半径时出错: {e}")
    
    return None


def visualize_model_freecad(file_path):
    """
    使用FreeCAD可视化模型
    
    Args:
        file_path (str): 模型文件路径
        
    Returns:
        bool: 是否成功启动可视化
    """
    # 占位符实现 - 需要实际的FreeCAD GUI环境
    try:
        if not FREECAD_AVAILABLE:
            return False
            
        # 这里应该实现实际的可视化逻辑
        return True
    except Exception as e:
        # 处理可视化过程中的异常
        print(f"FreeCAD可视化出错: {e}")
        return False