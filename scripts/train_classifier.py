import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import json
import os
import open3d as o3d

# ========== 1. 定义数据集 ==========
class PointCloudDataset(Dataset):
    def __init__(self, points_list, labels_list, num_points=1024):
        self.points_list = points_list
        self.labels_list = labels_list
        self.num_points = num_points

    def __len__(self):
        return len(self.points_list)

    def __getitem__(self, idx):
        pts = self.points_list[idx]
        # 随机采样到固定点数，保证每个样本大小一样
        if len(pts) > self.num_points:
            choice = np.random.choice(len(pts), self.num_points, replace=False)
            pts = pts[choice]
        else:
            choice = np.random.choice(len(pts), self.num_points, replace=True)
            pts = pts[choice]
        # 转成PyTorch张量
        return torch.tensor(pts, dtype=torch.float32), self.labels_list[idx]

# ========== 2. 定义简易PointNet模型 ==========
class SimplePointNet(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        # 逐点特征提取（MLP）
        self.mlp1 = nn.Sequential(
            nn.Linear(3, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Linear(64, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Linear(128, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
        )
        # 分类头
        self.fc = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, num_classes)
        )

    def forward(self, x):
        # x形状：(批次, 点数, 3)
        b, n, _ = x.shape
        x = x.reshape(b*n, 3)
        x = self.mlp1(x)               # 提取每个点的特征
        x = x.reshape(b, n, 256)
        x = torch.max(x, dim=1)[0]     # 全局最大池化，得到整体特征
        x = self.fc(x)                 # 分类
        return x

# ========== 3. 加载数据并划分训练/测试集 ==========
points = np.load("D:/bim2cim_project/output/points.npy", allow_pickle=True)
labels = np.load("D:/bim2cim_project/output/labels.npy", allow_pickle=True)

# 重新整理成「每个构件一个样本」的格式
# （因为之前是所有点堆在一起，现在要按构件分开）
# 简单做法：按标签分段，这里简化处理，直接用每个构件采样
# 如果你数据是按构件存的列表更简单，这里我们重新从IFC提取构件级数据

# --- 重新加载构件级数据 ---
import ifcopenshell
import ifcopenshell.geom
settings = ifcopenshell.geom.settings()
settings.set(settings.USE_WORLD_COORDS, True)
ifc_file = ifcopenshell.open("D:/bim2cim_project/data/sample.ifc")
target_types = ["IfcBeam", "IfcColumn", "IfcSlab", "IfcWall"]
elements = [e for e in ifc_file.by_type("IfcBuildingElement") if e.is_a() in target_types]

obj_points = []
obj_labels = []
class_map = {}
cur = 0

for elem in elements:
    try:
        shape = ifcopenshell.geom.create_shape(settings, elem)
        verts = np.array(shape.geometry.verts).reshape(-1, 3)
        mesh = o3d.geometry.TriangleMesh()
        mesh.vertices = o3d.utility.Vector3dVector(verts)
        mesh.triangles = o3d.utility.Vector3iVector(np.array(shape.geometry.faces).reshape(-1,3))
        pcd = mesh.sample_points_uniformly(number_of_points=2000)
        pts = np.asarray(pcd.points)
        
        t = elem.is_a()
        if t not in class_map:
            class_map[t] = cur
            cur += 1
        obj_points.append(pts)
        obj_labels.append(class_map[t])
    except:
        continue

# 划分训练集80%、测试集20%
num = len(obj_points)
indices = np.random.permutation(num)
split = int(0.8 * num)
train_idx = indices[:split]
test_idx = indices[split:]

train_pts = [obj_points[i] for i in train_idx]
train_lbl = [obj_labels[i] for i in train_idx]
test_pts = [obj_points[i] for i in test_idx]
test_lbl = [obj_labels[i] for i in test_idx]

# 创建数据加载器
train_dataset = PointCloudDataset(train_pts, train_lbl)
test_dataset = PointCloudDataset(test_pts, test_lbl)
train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=8)

num_classes = len(class_map)
print(f"类别数：{num_classes}，类别映射：{class_map}")
print(f"训练集：{len(train_pts)} 个构件，测试集：{len(test_pts)} 个构件")

# ========== 4. 训练配置 ==========
model = SimplePointNet(num_classes)
optimizer = optim.Adam(model.parameters(), lr=0.001)
criterion = nn.CrossEntropyLoss()
epochs = 30

# ========== 5. 开始训练 ==========
print("\n开始训练...")
for epoch in range(epochs):
    model.train()
    total_loss = 0
    for pts, lbl in train_loader:
        optimizer.zero_grad()   # 清空梯度
        out = model(pts)        # 前向传播
        loss = criterion(out, lbl)  # 计算损失
        loss.backward()         # 反向传播
        optimizer.step()        # 更新参数
        total_loss += loss.item()
    
    # 每个epoch输出一次损失
    avg_loss = total_loss / len(train_loader)
    print(f"Epoch {epoch+1:2d}/{epochs} | 训练损失：{avg_loss:.4f}")

# ========== 6. 测试评估 ==========
model.eval()
correct = 0
total = 0
with torch.no_grad():
    for pts, lbl in test_loader:
        out = model(pts)
        pred = out.argmax(dim=1)
        correct += (pred == lbl).sum().item()
        total += lbl.size(0)

acc = correct / total
print(f"\n✅ 测试准确率：{acc:.4f} ({correct}/{total})")

# ========== 7. 保存模型 ==========
os.makedirs("D:/bim2cim_project/models", exist_ok=True)
torch.save(model.state_dict(), "D:/bim2cim_project/models/pointnet.pth")
print("模型已保存到 models/pointnet.pth")
