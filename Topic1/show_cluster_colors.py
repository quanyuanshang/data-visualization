"""
显示聚类ID和颜色的对应关系
帮助用户找到蓝色的聚类
"""
import json
import numpy as np
import matplotlib.pyplot as plt

CLUSTER_LABELS_JSON = 'cluster_analysis/cluster_labels.json'

def main():
    """显示聚类颜色映射"""
    with open(CLUSTER_LABELS_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    labels = data['labels']
    
    # 获取所有唯一标签（排除噪声-1）
    unique_labels = sorted([l for l in set(labels) if l != -1])
    n_clusters = len(unique_labels)
    
    # 计算颜色映射（与可视化代码一致）
    colors_list = plt.cm.tab20(np.linspace(0, 1, n_clusters))
    
    # 统计每个聚类的大小
    cluster_sizes = {}
    for label in labels:
        if label != -1:
            cluster_sizes[label] = cluster_sizes.get(label, 0) + 1
    
    print("="*80)
    print("聚类ID与颜色对应关系（前20个，对应tab20颜色）")
    print("="*80)
    print(f"{'聚类ID':<10} {'大小':<10} {'颜色索引':<10} {'颜色RGB'}")
    print("-" * 80)
    
    for i, label in enumerate(unique_labels[:20]):
        color = colors_list[i]
        rgb = f"({color[0]:.2f}, {color[1]:.2f}, {color[2]:.2f})"
        size = cluster_sizes[label]
        color_idx = i % 20
        print(f"Cluster {label:<6} {size:<10} {color_idx:<10} {rgb}")
    
    print("\n注意:")
    print("- 颜色索引0对应tab20的第一个颜色（通常是蓝色）")
    print("- 如果聚类数>20，颜色会循环使用")
    print("- 要分析特定聚类，运行: python analyze_specific_cluster.py <cluster_id>")
    
    # 找出颜色索引0对应的聚类（蓝色）
    if len(unique_labels) > 0:
        blue_cluster = unique_labels[0]
        print(f"\n蓝色聚类（颜色索引0）: Cluster {blue_cluster} (包含 {cluster_sizes[blue_cluster]} 个音乐人)")

if __name__ == '__main__':
    main()








