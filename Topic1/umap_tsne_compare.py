"""
UMAP vs t-SNE 降维对比 + 聚类分析
输出到独立的文件夹
"""
import os
import sys
import csv
import json
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN
from sklearn.metrics import silhouette_score

try:
    import umap
    HAS_UMAP = True
except ImportError:
    HAS_UMAP = False
    print("警告: 未安装 umap-learn，将跳过 UMAP 方法")

INPUT_CSV = 'person_genre_matrix.csv'
OUT_DIR = 'umap_tsne_comparison'
RANDOM_STATE = 42
POINT_SIZE = 4
ALPHA = 0.7

# 聚类参数
K_VALUES = [5, 8, 12, 15]  # KMeans 和 Agglomerative 的 k 值
DBSCAN_PARAMS = [
    (0.08, 5),   # 原始参数
    (0.10, 15),  # 新参数：每个聚类至少15人
]


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


def reduce_dimension(X, method='tsne', n_components=2):
    """降维到2D"""
    if method == 'tsne':
        print(f"  运行 t-SNE (样本数: {len(X)})...")
        # 注意：特征维度仅有26，无需额外PCA到50维；直接使用 init='pca' 更稳妥
        tsne = TSNE(
            n_components=n_components,
            random_state=RANDOM_STATE,
            init='pca',
            learning_rate='auto',
            perplexity=30,
            max_iter=1000
        )
        coords = tsne.fit_transform(X)
        return coords, {'method': 'tsne', 'perplexity': 30, 'init': 'pca'}
    
    elif method == 'umap':
        if not HAS_UMAP:
            raise ValueError("UMAP 未安装")
        print(f"  运行 UMAP (样本数: {len(X)})...")
        reducer = umap.UMAP(n_components=n_components, random_state=RANDOM_STATE, 
                           n_neighbors=15, min_dist=0.1, metric='euclidean')
        coords = reducer.fit_transform(X)
        return coords, {'method': 'umap', 'n_neighbors': 15, 'min_dist': 0.1}
    
    else:
        raise ValueError(f"未知的降维方法: {method}")


def apply_clustering(X, method='kmeans', **kwargs):
    """应用聚类算法"""
    if method == 'kmeans':
        k = kwargs.get('n_clusters', 8)
        model = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init='auto')
        labels = model.fit_predict(X)
        return labels, {'algo': 'kmeans', 'n_clusters': k}
    
    elif method == 'agglomerative':
        k = kwargs.get('n_clusters', 8)
        model = AgglomerativeClustering(n_clusters=k, linkage='ward')
        labels = model.fit_predict(X)
        return labels, {'algo': 'agglomerative', 'n_clusters': k, 'linkage': 'ward'}
    
    elif method == 'dbscan':
        eps = kwargs.get('eps', 0.08)
        min_samples = kwargs.get('min_samples', 5)
        model = DBSCAN(eps=eps, min_samples=min_samples)
        labels = model.fit_predict(X)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = list(labels).count(-1)
        return labels, {'algo': 'dbscan', 'eps': eps, 'min_samples': min_samples, 
                       'n_clusters': n_clusters, 'n_noise': n_noise}
    
    else:
        raise ValueError(f"未知的聚类方法: {method}")


def calculate_silhouette(X, labels):
    """计算轮廓系数"""
    unique_labels = set(labels)
    if len(unique_labels) <= 1:
        return None
    # 排除噪声点（标签为-1）如果太多
    valid_labels = [l for l in labels if l != -1]
    if len(set(valid_labels)) <= 1:
        return None
    try:
        return float(silhouette_score(X, labels))
    except:
        return None


def plot_clustering(coords, labels, title, save_path):
    """绘制聚类结果散点图"""
    plt.figure(figsize=(12, 10))
    
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
    
    # 绘制散点
    plt.scatter(coords[:, 0], coords[:, 1], c=colors, s=POINT_SIZE, alpha=ALPHA, edgecolors='none')
    
    plt.title(title, fontsize=14, fontweight='bold')
    plt.xlabel('Dimension 1', fontsize=12)
    plt.ylabel('Dimension 2', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # 添加图例
    if n_clusters > 0:
        legend_elements = []
        for label in unique_labels:
            if label != -1:
                legend_elements.append(plt.Line2D([0], [0], marker='o', color='w', 
                                                   markerfacecolor=color_map[label], 
                                                   markersize=8, label=f'Cluster {label}'))
        if -1 in unique_labels:
            legend_elements.append(plt.Line2D([0], [0], marker='o', color='w', 
                                               markerfacecolor=color_map[-1], 
                                               markersize=8, label='Noise'))
        plt.legend(handles=legend_elements, loc='upper right', fontsize=8, ncol=2)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"    ✓ 已保存: {save_path}")


def main():
    """主函数"""
    print("="*80)
    print("UMAP vs t-SNE 降维对比 + 聚类分析")
    print("="*80)
    
    # 创建输出目录
    os.makedirs(OUT_DIR, exist_ok=True)
    
    # 加载数据
    try:
        ids, names, genres, X = load_matrix(INPUT_CSV)
    except FileNotFoundError:
        print(f"错误: 未找到 {INPUT_CSV}")
        print("请先运行: python save_results.py")
        return
    
    # 标准化数据
    print("\n标准化数据...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 存储所有结果
    all_results = {}
    
    # 降维方法列表
    reduction_methods = ['tsne']
    if HAS_UMAP:
        reduction_methods.append('umap')
    
    # 对每种降维方法进行对比
    for red_method in reduction_methods:
        print(f"\n{'='*80}")
        print(f"降维方法: {red_method.upper()}")
        print(f"{'='*80}")
        
        try:
            # 降维
            coords, red_meta = reduce_dimension(X_scaled, method=red_method)
            print(f"  降维完成: {coords.shape}")
            
            all_results[red_method] = {
                'reduction_meta': red_meta,
                'clusterings': []
            }
            
            # KMeans 聚类
            print(f"\n  KMeans 聚类...")
            for k in K_VALUES:
                labels, cluster_meta = apply_clustering(X_scaled, 'kmeans', n_clusters=k)
                sil_score = calculate_silhouette(X_scaled, labels)
                
                title = f"{red_method.upper()} + KMeans (k={k})"
                if sil_score:
                    title += f"\nSilhouette Score: {sil_score:.3f}"
                
                filename = f"{red_method}_kmeans_k{k}.png"
                save_path = os.path.join(OUT_DIR, filename)
                plot_clustering(coords, labels, title, save_path)
                
                all_results[red_method]['clusterings'].append({
                    'method': 'kmeans',
                    'params': {'n_clusters': k},
                    'silhouette': sil_score,
                    'n_clusters': k,
                    'plot': filename
                })
            
            # Agglomerative 聚类
            print(f"\n  Agglomerative 聚类...")
            for k in K_VALUES:
                labels, cluster_meta = apply_clustering(X_scaled, 'agglomerative', n_clusters=k)
                sil_score = calculate_silhouette(X_scaled, labels)
                
                title = f"{red_method.upper()} + Agglomerative (k={k})"
                if sil_score:
                    title += f"\nSilhouette Score: {sil_score:.3f}"
                
                filename = f"{red_method}_agg_k{k}.png"
                save_path = os.path.join(OUT_DIR, filename)
                plot_clustering(coords, labels, title, save_path)
                
                all_results[red_method]['clusterings'].append({
                    'method': 'agglomerative',
                    'params': {'n_clusters': k},
                    'silhouette': sil_score,
                    'n_clusters': k,
                    'plot': filename
                })
            
            # DBSCAN 聚类
            print(f"\n  DBSCAN 聚类...")
            for eps, min_samples in DBSCAN_PARAMS:
                labels, cluster_meta = apply_clustering(X_scaled, 'dbscan', eps=eps, min_samples=min_samples)
                sil_score = calculate_silhouette(X_scaled, labels)
                n_clusters = cluster_meta.get('n_clusters', 0)
                n_noise = cluster_meta.get('n_noise', 0)
                
                title = f"{red_method.upper()} + DBSCAN (eps={eps}, min_samples={min_samples})"
                title += f"\nClusters: {n_clusters}, Noise: {n_noise}"
                if sil_score:
                    title += f", Silhouette: {sil_score:.3f}"
                
                filename = f"{red_method}_dbscan_eps{eps}_ms{min_samples}.png"
                save_path = os.path.join(OUT_DIR, filename)
                plot_clustering(coords, labels, title, save_path)
                
                all_results[red_method]['clusterings'].append({
                    'method': 'dbscan',
                    'params': {'eps': eps, 'min_samples': min_samples},
                    'silhouette': sil_score,
                    'n_clusters': n_clusters,
                    'n_noise': n_noise,
                    'plot': filename
                })
            
        except Exception as e:
            print(f"  错误: {red_method.upper()} 处理失败: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # 保存结果摘要
    summary_path = os.path.join(OUT_DIR, 'comparison_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 结果摘要已保存到: {summary_path}")
    
    # 打印最佳结果
    print("\n" + "="*80)
    print("最佳聚类结果（按 Silhouette Score）:")
    print("="*80)
    
    best_results = []
    for red_method, data in all_results.items():
        for cluster in data['clusterings']:
            if cluster.get('silhouette') is not None:
                best_results.append({
                    'reduction': red_method,
                    'clustering': cluster['method'],
                    'params': cluster['params'],
                    'silhouette': cluster['silhouette'],
                    'plot': cluster['plot']
                })
    
    best_results.sort(key=lambda x: x['silhouette'], reverse=True)
    
    for i, result in enumerate(best_results[:10], 1):
        print(f"\n{i}. {result['reduction'].upper()} + {result['clustering']} "
              f"(params: {result['params']})")
        print(f"   Silhouette Score: {result['silhouette']:.3f}")
        print(f"   图片: {result['plot']}")
    
    print(f"\n{'='*80}")
    print(f"所有结果已保存到: {OUT_DIR}/")
    print(f"{'='*80}")


if __name__ == '__main__':
    main()

