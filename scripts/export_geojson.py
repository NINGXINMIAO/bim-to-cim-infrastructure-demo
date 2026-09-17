import ifcopenshell
import ifcopenshell.geom
import numpy as np
import json
import os

settings = ifcopenshell.geom.settings()
settings.set(settings.USE_WORLD_COORDS, True)

ifc_file = ifcopenshell.open("D:/bim2cim_project/data/sample.ifc")
elements = ifc_file.by_type("IfcBuildingElement")

features = []

for elem in elements:
    try:
        shape = ifcopenshell.geom.create_shape(settings, elem)
        verts = np.array(shape.geometry.verts).reshape(-1, 3)
        
        # 计算包围盒的最小、最大坐标
        min_xyz = verts.min(axis=0).tolist()
        max_xyz = verts.max(axis=0).tolist()
        center = ((verts.min(axis=0) + verts.max(axis=0)) / 2).tolist()

        # 构造GeoJSON要素
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                # 用包围盒底面矩形简化表示
                "coordinates": [[
                    [min_xyz[0], min_xyz[1]],
                    [max_xyz[0], min_xyz[1]],
                    [max_xyz[0], max_xyz[1]],
                    [min_xyz[0], max_xyz[1]],
                    [min_xyz[0], min_xyz[1]]
                ]]
            },
            "properties": {
                "id": elem.id(),
                "type": elem.is_a(),
                "name": elem.Name if hasattr(elem, "Name") else "",
                "bbox_3d": [min_xyz, max_xyz],
                "center": center
            }
        }
        features.append(feature)
    except:
        continue

# 构造完整GeoJSON
geojson = {
    "type": "FeatureCollection",
    "features": features
}

# 保存
os.makedirs("D:/bim2cim_project/output", exist_ok=True)
with open("D:/bim2cim_project/output/result.geojson", "w") as f:
    json.dump(geojson, f, indent=2)

print(f"✅ GeoJSON导出完成，共 {len(features)} 个要素")
print("文件路径：output/result.geojson")
