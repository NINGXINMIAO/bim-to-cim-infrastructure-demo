# 导入读取IFC的工具
import ifcopenshell
# 导入统计工具
from collections import Counter

# ========== 1. 打开IFC文件 ==========
# 这里填你的IFC文件路径，注意路径用 / 不用 \
ifc_path = "D:/bim2cim_project/data/sample.ifc"
ifc_file = ifcopenshell.open(ifc_path)

# ========== 2. 提取所有建筑构件 ==========
# IfcBuildingElement 是所有建筑构件的大类
elements = ifc_file.by_type("IfcBuildingElement")

# 如果上面提取为空，就换成这句试试：
# elements = ifc_file.by_type("IfcElement")

print(f"总共找到构件数量：{len(elements)}")

# ========== 3. 统计每种构件的数量 ==========
# e.is_a() 就是获取构件的类型名
type_counts = Counter(e.is_a() for e in elements)

print("\n构件类型统计：")
for type_name, count in type_counts.items():
    print(f"  {type_name}: {count} 个")
