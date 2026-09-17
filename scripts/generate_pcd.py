import ifcopenshell
import ifcopenshell.geom
import numpy as np
import open3d as o3d
import json
import os

# ========== 1. 几何提取设置 ==========
settings = ifcopenshell.geom.settings()
# 使用世界坐标，保证位置正确
settings.set(settings.USE_WORLD_COORDS, True)

ifc_path = "D:/bim2cim_project/data/sample.ifc"
ifc_file = ifcopenshell.open(ifc_path)

# ========== 2. 指定我们要处理的构件类型 ==========
target_types = ["IfcBeam", "IfcColumn", "IfcSlab", "IfcWall"]

# 筛选出目标构件
elements = [e for e in ifc_file.by_type("IfcBuildingElement") 
            if e.is_a() in target_types]

# ========== 3. 准备容器存点和标签 ==========
all_points = []      # 存所有点的坐标
all_labels = []      # 存每个点对应的类别编号
class_map = {}       # 类别名 → 编号 的映射
current_label = 0    # 当前类别编号

# ========== 4. 逐个构件处理 ==========
for elem in elements:
    try:
        # 提取构件的几何形状
        shape = ifcopenshell.geom.create_shape(settings, elem)
        # 提取顶点坐标
        verts = np.array(shape.geometry.verts).reshape(-1, 3)
        # 提取三角面
        faces = np.array(shape.geometry.faces).reshape(-1, 3)

        # 用Open3D创建网格模型
        mesh = o3d.geometry.TriangleMesh()
        mesh.vertices = o3d.utility.Vector3dVector(verts)
        mesh.triangles = o3d.utility.Vector3iVector(faces)
        mesh.compute_vertex_normals()

        # 均匀采样2000个点，生成点云
        pcd = mesh.sample_points_uniformly(number_of_points=2000)
        pts = np.asarray(pcd.points)

        # 给构件分配类别编号
        elem_type = elem.is_a()
        if elem_type not in class_map:
            class_map[elem_type] = current_label
            current_label += 1
        label = class_map[elem_type]

        # 存起来
        all_points.append(pts)
        all_labels.append(np.full(len(pts), label))

    except Exception as e:
        print(f"处理失败：{elem.is_a()} (id={elem.id()})，原因：{e}")
        continue

# ========== 5. 合并所有点云并保存 ==========
points = np.vstack(all_points)
labels = np.concatenate(all_labels)

# 确保output文件夹存在
os.makedirs("D:/bim2cim_project/output", exist_ok=True)

# 保存点云和标签
np.save("D:/bim2cim_project/output/points.npy", points)
np.save("D:/bim2cim_project/output/labels.npy", labels)

# 保存类别映射表
with open("D:/bim2cim_project/output/class_map.json", "w") as f:
    json.dump({v: k for k, v in class_map.items()}, f, indent=2)

print(f"\n✅ 生成完成！")
print(f"点云形状：{points.shape}")
print(f"标签形状：{labels.shape}")
print("类别映射：", class_map)
