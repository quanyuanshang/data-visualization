"""
使用新参数（eps=0.10, min_samples=15）重新生成聚类散点图
输出到新文件夹
"""
import os
import sys
import csv
import json
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN

try:
    import umap
    HAS_UMAP = True
except ImportError:
    HAS_UMAP = False
    print("错误: 未安装 umap-learn")
    exit(1)

# 设置输出编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

INPUT_CSV = 'person_genre_matrix.csv'
OUT_DIR = 'clustering_plots_new_params'  # 新文件夹
RANDOM_STATE = 42
POINT_SIZE = 4
ALPHA = 0.7

# 新参数
REDUCTION_METHOD = 'umap'
DBSCAN_EPS = 0.10
DBSCAN_MIN_SAMPLES = 15


def load_matrix(path):
    """加载人员×流派矩阵"""
    print(f"正在加载 {path}...")
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    
    ids = [r[0] for r in rows]
    names = [r[1] for r in rows]
    genres = header[2:]
    X = np.array([[float(x) for x in r[2:]] for r in rows], dtype=float)
    
    print(f"  加载完成: {len(ids)} 个音乐人, {len(genres)} 个流派")
    return ids, names, genres, X


def reduce_dimension(X, method='umap', n_components=2):
    """降维到2D"""
    if method == 'umap':
        if not HAS_UMAP:
            raise ValueError("UMAP 未安装")
        print(f"  运行 UMAP (样本数: {len(X)})...")
        reducer = umap.UMAP(n_components=n_components, random_state=RANDOM_STATE, 
                           n_neighbors=15, min_dist=0.1, metric='euclidean')
        coords = reducer.fit_transform(X)
        return coords, {'method': 'umap', 'n_neighbors': 15, 'min_dist': 0.1}
    else:
        raise ValueError(f"未知的降维方法: {method}")


def apply_dbscan(X, eps, min_samples):
    """应用DBSCAN聚类"""
    print(f"  运行 DBSCAN (eps={eps}, min_samples={min_samples})...")
    model = DBSCAN(eps=eps, min_samples=min_samples)
    labels = model.fit_predict(X)
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    return labels, {'algo': 'dbscan', 'eps': eps, 'min_samples': min_samples, 
                   'n_clusters': n_clusters, 'n_noise': n_noise}


def plot_clustering(coords, labels, title, save_path):
    """绘制聚类结果散点图（紧凑版，不重叠）"""
    # 使用合适的图形尺寸，让图更紧凑
    plt.figure(figsize=(14, 12))
    
    # 获取唯一标签
    unique_labels = sorted(set(labels))
    n_clusters = len([l for l in unique_labels if l != -1])
    
    # 为每个簇分配颜色
    if n_clusters > 0:
        # 使用tab20颜色映射，噪声点用灰色
        if -1 in unique_labels:
            colors_list = plt.cm.tab20(np.linspace(0, 1, n_clusters))
            color_map = {label: colors_list[i] for i, label in enumerate([l for l in unique_labels if l != -1])}
            color_map[-1] = (0.5, 0.5, 0.5, 0.3)  # 灰色表示噪声
        else:
            colors_list = plt.cm.tab20(np.linspace(0, 1, n_clusters))
            color_map = {label: colors_list[i] for i, label in enumerate(unique_labels)}
        
        colors = [color_map[label] for label in labels]
    else:
        colors = ['gray'] * len(labels)
    
    # 分离聚类点和噪声点，使用不同的点大小
    cluster_mask = np.array([l != -1 for l in labels])
    noise_mask = np.array([l == -1 for l in labels])
    
    # 绘制聚类点（使用小点避免重叠，但保持可见）
    if np.any(cluster_mask):
        cluster_coords = coords[cluster_mask]
        cluster_colors = [colors[i] for i in range(len(colors)) if cluster_mask[i]]
        # 使用小点避免重叠，alpha值稍高保持可见
        plt.scatter(cluster_coords[:, 0], cluster_coords[:, 1], 
                   c=cluster_colors, s=2.5, alpha=0.85, edgecolors='none', linewidths=0)
    
    # 绘制噪声点（更小更透明，放在底层）
    if np.any(noise_mask):
        noise_coords = coords[noise_mask]
        plt.scatter(noise_coords[:, 0], noise_coords[:, 1], 
                   c='gray', s=1, alpha=0.25, edgecolors='none', linewidths=0, zorder=0)
    
    plt.title(title, fontsize=16, fontweight='bold', pad=20)
    # 去掉坐标轴标签
    plt.xlabel('', fontsize=0)
    plt.ylabel('', fontsize=0)
    # 去掉坐标轴刻度
    plt.xticks([])
    plt.yticks([])
    # 去掉边框
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    plt.gca().spines['bottom'].set_visible(False)
    plt.gca().spines['left'].set_visible(False)
    plt.grid(False)
    
    # 添加图例（只显示前20个聚类，避免图例过长）
    if n_clusters > 0:
        legend_elements = []
        displayed_labels = [l for l in unique_labels if l != -1][:20]
        for label in displayed_labels:
            legend_elements.append(plt.Line2D([0], [0], marker='o', color='w', 
                                               markerfacecolor=color_map[label], 
                                               markersize=10, label=f'Cluster {label}'))
        if -1 in unique_labels:
            legend_elements.append(plt.Line2D([0], [0], marker='o', color='w', 
                                               markerfacecolor=color_map[-1], 
                                               markersize=10, label='Noise'))
        if len([l for l in unique_labels if l != -1]) > 20:
            legend_elements.append(plt.Line2D([0], [0], marker='o', color='w', 
                                               markerfacecolor='white', 
                                               markersize=0, 
                                               label=f'... and {len([l for l in unique_labels if l != -1]) - 20} more clusters'))
        plt.legend(handles=legend_elements, loc='upper right', fontsize=9, ncol=2, 
                  bbox_to_anchor=(1.0, 1.0))
    
    # 调整边距，让图更紧凑
    plt.tight_layout(pad=0.5)
    plt.savefig(save_path, dpi=200, bbox_inches='tight', pad_inches=0.1)
    plt.close()
    print(f"    ✓ 已保存: {save_path}")


def main():
    """主函数"""
    print("="*80)
    print("使用新参数生成聚类散点图")
    print(f"参数: eps={DBSCAN_EPS}, min_samples={DBSCAN_MIN_SAMPLES}")
    print("="*80)
    
    # 创建输出目录
    os.makedirs(OUT_DIR, exist_ok=True)
    
    # 加载数据
    try:
        ids, names, genres, X = load_matrix(INPUT_CSV)
    except FileNotFoundError:
        print(f"错误: 未找到 {INPUT_CSV}")
        return
    
    # 标准化数据
    print("\n标准化数据...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 降维
    print(f"\n降维方法: {REDUCTION_METHOD.upper()}")
    coords, red_meta = reduce_dimension(X_scaled, method=REDUCTION_METHOD)
    print(f"  降维完成: {coords.shape}")
    
    # DBSCAN聚类
    labels, cluster_meta = apply_dbscan(X_scaled, DBSCAN_EPS, DBSCAN_MIN_SAMPLES)
    n_clusters = cluster_meta.get('n_clusters', 0)
    n_noise = cluster_meta.get('n_noise', 0)
    print(f"  聚类完成: {n_clusters} 个聚类, {n_noise} 个噪声点")
    
    # 统计聚类大小
    cluster_sizes = {}
    for label in labels:
        if label != -1:
            cluster_sizes[label] = cluster_sizes.get(label, 0) + 1
    
    min_size = min(cluster_sizes.values()) if cluster_sizes else 0
    max_size = max(cluster_sizes.values()) if cluster_sizes else 0
    avg_size = np.mean(list(cluster_sizes.values())) if cluster_sizes else 0
    
    print(f"  聚类大小: 最小={min_size}, 最大={max_size}, 平均={avg_size:.1f}")
    
    # 绘制散点图
    title = f"{REDUCTION_METHOD.upper()} + DBSCAN (eps={DBSCAN_EPS}, min_samples={DBSCAN_MIN_SAMPLES})"
    title += f"\nClusters: {n_clusters}, Noise: {n_noise}"
    title += f"\nCluster Size: {min_size}-{max_size} (avg: {avg_size:.1f})"
    
    # 使用不同的文件名，避免与原来的图冲突
    filename = f"{REDUCTION_METHOD}_dbscan_eps{DBSCAN_EPS}_ms{DBSCAN_MIN_SAMPLES}_compact.png"
    save_path = os.path.join(OUT_DIR, filename)
    plot_clustering(coords, labels, title, save_path)
    
    # 保存聚类标签和元数据
    labels_path = os.path.join(OUT_DIR, 'cluster_labels.json')
    with open(labels_path, 'w', encoding='utf-8') as f:
        json.dump({
            'ids': ids,
            'names': names,
            'labels': labels.tolist(),
            'params': {
                'reduction': REDUCTION_METHOD,
                'dbscan_eps': DBSCAN_EPS,
                'dbscan_min_samples': DBSCAN_MIN_SAMPLES
            },
            'stats': {
                'n_clusters': n_clusters,
                'n_noise': n_noise,
                'min_cluster_size': int(min_size),
                'max_cluster_size': int(max_size),
                'avg_cluster_size': float(avg_size)
            }
        }, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 聚类标签已保存到: {labels_path}")
    
    # 保存聚类信息摘要
    summary_path = os.path.join(OUT_DIR, 'clustering_summary.txt')
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("聚类结果摘要\n")
        f.write("="*80 + "\n\n")
        f.write(f"参数:\n")
        f.write(f"  降维方法: {REDUCTION_METHOD}\n")
        f.write(f"  DBSCAN eps: {DBSCAN_EPS}\n")
        f.write(f"  DBSCAN min_samples: {DBSCAN_MIN_SAMPLES}\n\n")
        f.write(f"结果:\n")
        f.write(f"  总聚类数: {n_clusters}\n")
        f.write(f"  噪声点: {n_noise}\n")
        f.write(f"  聚类大小范围: {min_size}-{max_size}\n")
        f.write(f"  平均聚类大小: {avg_size:.1f}\n\n")
        f.write("各聚类大小（按大小排序）:\n")
        f.write("-" * 40 + "\n")
        f.write(f"{'聚类ID':<10} {'大小':<10}\n")
        f.write("-" * 40 + "\n")
        for label, size in sorted(cluster_sizes.items(), key=lambda x: x[1], reverse=True):
            f.write(f"Cluster {label:<6} {size:<10}\n")
    print(f"✓ 摘要已保存到: {summary_path}")
    
    print(f"\n{'='*80}")
    print(f"所有结果已保存到: {OUT_DIR}/")
    print(f"{'='*80}")


if __name__ == '__main__':
    main()

