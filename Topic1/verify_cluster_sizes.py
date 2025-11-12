"""
验证聚类大小，确保所有聚类都至少15人
"""
import json

CLUSTER_LABELS_JSON = 'cluster_analysis/cluster_labels.json'
MIN_SIZE = 15

def main():
    """验证聚类大小"""
    with open(CLUSTER_LABELS_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    labels = data['labels']
    params = data.get('params', {})
    
    print("="*80)
    print("聚类大小验证")
    print("="*80)
    print(f"参数: eps={params.get('dbscan_eps', 'N/A')}, "
          f"min_samples={params.get('dbscan_min_samples', 'N/A')}")
    print(f"最小要求: 每个聚类至少 {MIN_SIZE} 人")
    print("="*80)
    
    # 统计聚类大小
    cluster_sizes = {}
    for label in labels:
        if label != -1:
            cluster_sizes[label] = cluster_sizes.get(label, 0) + 1
    
    n_noise = labels.count(-1)
    n_clusters = len(cluster_sizes)
    
    # 检查小聚类
    small_clusters = {label: size for label, size in cluster_sizes.items() if size < MIN_SIZE}
    
    print(f"\n总聚类数: {n_clusters}")
    print(f"噪声点: {n_noise}")
    print(f"小聚类数(<{MIN_SIZE}人): {len(small_clusters)}")
    
    if small_clusters:
        print(f"\n警告: 发现 {len(small_clusters)} 个小聚类:")
        for label, size in sorted(small_clusters.items(), key=lambda x: x[1]):
            print(f"  Cluster {label}: {size} 人")
    else:
        print(f"\n✓ 所有聚类都满足最小大小要求（≥{MIN_SIZE}人）")
    
    # 显示聚类大小统计
    sizes = list(cluster_sizes.values())
    print(f"\n聚类大小统计:")
    print(f"  最小: {min(sizes)} 人")
    print(f"  最大: {max(sizes)} 人")
    print(f"  平均: {sum(sizes)/len(sizes):.1f} 人")
    print(f"  中位数: {sorted(sizes)[len(sizes)//2]} 人")
    
    # 显示所有聚类（按大小排序）
    print(f"\n所有聚类（按大小排序）:")
    print(f"{'聚类ID':<10} {'大小':<10}")
    print("-" * 20)
    for label, size in sorted(cluster_sizes.items(), key=lambda x: x[1], reverse=True):
        status = "✓" if size >= MIN_SIZE else "✗"
        print(f"Cluster {label:<6} {size:<10} {status}")

if __name__ == '__main__':
    main()








