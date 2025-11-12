#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成包含UMAP坐标和聚类信息的CSV文件"""
import csv
import json
import os
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
import umap

# 获取脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))
# 输入输出路径
input_csv = os.path.join(script_dir, 'data', 'person_genre_matrix.csv')
output_csv = os.path.join(script_dir, 'viz-app', 'public', 'data', 'person_genre_matrix.csv')

print("加载数据...")
with open(input_csv, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    # 跳过空行
    header = None
    for line in reader:
        if line and line[0].strip():
            header = line
            break
    rows = [r for r in reader if r and len(r) > 2 and r[0].strip()]

ids = [r[0] for r in rows]
names = [r[1] for r in rows]
X = np.array([[float(x) for x in r[2:]] for r in rows], dtype=float)

print(f"数据: {len(ids)} 个音乐人, {len(header)-2} 个流派")

print("标准化...")
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

print("UMAP降维...")
reducer = umap.UMAP(n_components=2, random_state=42, n_neighbors=15, min_dist=0.1)
coords = reducer.fit_transform(X_scaled)

print("DBSCAN聚类...")
model = DBSCAN(eps=0.1, min_samples=15)
labels = model.fit_predict(X_scaled)
n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
print(f"聚类完成: {n_clusters} 个聚类, {list(labels).count(-1)} 个噪声点")

print("保存CSV...")
import os
os.makedirs(os.path.dirname(output_csv), exist_ok=True)
with open(output_csv, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(header + ['umap_x', 'umap_y', 'cluster'])
    for i, row in enumerate(rows):
        writer.writerow(row + [f'{coords[i,0]:.6f}', f'{coords[i,1]:.6f}', str(int(labels[i]))])

print(f"完成! 已保存到 {output_csv}")

