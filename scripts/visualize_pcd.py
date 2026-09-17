import open3d as o3d
import numpy as np

# 读取点云
points = np.load("D:/bim2cim_project/output/points.npy")

# 创建Open3D点云对象
pcd = o3d.geometry.PointCloud()
pcd.points = o3d.utility.Vector3dVector(points)

# 可视化
o3d.visualization.draw_geometries([pcd])

