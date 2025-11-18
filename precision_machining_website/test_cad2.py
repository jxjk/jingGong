import os
import sys
sys.path.append('.')  # 添加当前目录到路径中
from quotation.cad_analyzer import CADModelAnalyzer

# 测试CAD模型分析器
if __name__ == "__main__":
    # 使用一个实际的STP文件进行测试
    test_file = "media/quotation_models/TDJ-1_1_NDmr6F1.stp"
    
    if os.path.exists(test_file):
        print(f"测试文件: {test_file}")
        print(f"文件大小: {os.path.getsize(test_file)} 字节")
        analyzer = CADModelAnalyzer(test_file)
        print("Analyzer创建成功")
        features = analyzer.analyze()
        print(f"提取的特征: {features}")
    else:
        print(f"测试文件 {test_file} 不存在")