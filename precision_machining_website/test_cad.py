import os
import sys
sys.path.append('.')  # 添加当前目录到路径中
from quotation.cad_analyzer import CADModelAnalyzer

# 测试CAD模型分析器
if __name__ == "__main__":
    # 使用一个存在的文件进行测试
    test_file = "manage.py"  # 使用manage.py作为测试文件（虽然不是3D模型，但可以测试加载过程）
    
    if os.path.exists(test_file):
        print(f"测试文件: {test_file}")
        analyzer = CADModelAnalyzer(test_file)
        print("Analyzer创建成功")
        features = analyzer.analyze()
        print(f"提取的特征: {features}")
    else:
        print(f"测试文件 {test_file} 不存在")