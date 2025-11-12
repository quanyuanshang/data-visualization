"""
分析特定聚类的流派分布特征
固定使用 UMAP + DBSCAN (eps=0.08, min_samples=5)
"""
import os
import sys
import csv
import json
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN

# 设置输出编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    import umap
    HAS_UMAP = True
except ImportError:
    HAS_UMAP = False
    print("错误: 未安装 umap-learn")
    exit(1)

INPUT_CSV = 'person_genre_matrix.csv'
OUT_DIR = 'cluster_analysis'
RANDOM_STATE = 42

# 固定的聚类参数
REDUCTION_METHOD = 'umap'
DBSCAN_EPS = 0.10
DBSCAN_MIN_SAMPLES = 15  # 确保每个聚类至少15人


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


def perform_clustering(ids, names, genres, X):
    """执行UMAP降维和DBSCAN聚类"""
    print(f"\n{'='*80}")
    print("执行 UMAP 降维 + DBSCAN 聚类")
    print(f"{'='*80}")
    
    # 标准化数据
    print("标准化数据...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # UMAP降维
    print(f"运行 UMAP (样本数: {len(X)})...")
    reducer = umap.UMAP(n_components=2, random_state=RANDOM_STATE, 
                       n_neighbors=15, min_dist=0.1, metric='euclidean')
    coords = reducer.fit_transform(X_scaled)
    print(f"  降维完成: {coords.shape}")
    
    # DBSCAN聚类
    print(f"运行 DBSCAN (eps={DBSCAN_EPS}, min_samples={DBSCAN_MIN_SAMPLES})...")
    model = DBSCAN(eps=DBSCAN_EPS, min_samples=DBSCAN_MIN_SAMPLES)
    labels = model.fit_predict(X_scaled)
    
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    print(f"  聚类完成: {n_clusters} 个聚类, {n_noise} 个噪声点")
    
    return labels, coords, scaler


def analyze_cluster_genres(cluster_id, ids, names, genres, X, labels):
    """分析特定聚类的流派分布"""
    # 获取该聚类的所有音乐人索引
    cluster_indices = [i for i, label in enumerate(labels) if label == cluster_id]
    
    if len(cluster_indices) == 0:
        print(f"错误: 聚类 {cluster_id} 不存在或为空")
        return None
    
    print(f"\n聚类 {cluster_id} 包含 {len(cluster_indices)} 个音乐人")
    
    # 获取该聚类的音乐人信息
    cluster_ids = [ids[i] for i in cluster_indices]
    cluster_names = [names[i] for i in cluster_indices]
    cluster_X = X[cluster_indices]  # 流派占比矩阵
    
    # 计算每个流派的平均占比
    genre_means = np.mean(cluster_X, axis=0)
    genre_stds = np.std(cluster_X, axis=0)
    
    # 创建流派统计字典
    genre_stats = []
    for i, genre in enumerate(genres):
        genre_stats.append({
            'genre': genre,
            'mean': float(genre_means[i]),
            'std': float(genre_stds[i]),
            'max': float(np.max(cluster_X[:, i])),
            'min': float(np.min(cluster_X[:, i]))
        })
    
    # 按平均占比排序
    genre_stats.sort(key=lambda x: x['mean'], reverse=True)
    
    return {
        'cluster_id': cluster_id,
        'n_members': len(cluster_indices),
        'member_ids': cluster_ids,
        'member_names': cluster_names,
        'genre_stats': genre_stats
    }


def plot_genre_distribution(analysis_result, save_path):
    """绘制流派分布柱状图"""
    if analysis_result is None:
        return
    
    genre_stats = analysis_result['genre_stats']
    cluster_id = analysis_result['cluster_id']
    n_members = analysis_result['n_members']
    
    # 提取数据
    genres = [g['genre'] for g in genre_stats]
    means = [g['mean'] for g in genre_stats]
    stds = [g['std'] for g in genre_stats]
    
    # 只显示平均占比大于0的流派，或者显示前15个
    threshold = 0.01  # 只显示平均占比>1%的流派
    filtered = [(g, m, s) for g, m, s in zip(genres, means, stds) if m > threshold]
    if len(filtered) > 20:  # 如果太多，只显示前20个
        filtered = filtered[:20]
    
    if not filtered:
        print("警告: 没有流派满足显示条件")
        return
    
    filtered_genres, filtered_means, filtered_stds = zip(*filtered)
    
    # 创建图表
    plt.figure(figsize=(14, 8))
    bars = plt.bar(range(len(filtered_genres)), filtered_means, 
                   yerr=filtered_stds, capsize=5, alpha=0.7, 
                   color='steelblue', edgecolor='navy', linewidth=1.2)
    
    # 设置标签
    plt.xlabel('Genre', fontsize=12, fontweight='bold')
    plt.ylabel('Average Proportion', fontsize=12, fontweight='bold')
    plt.title(f'Cluster {cluster_id} Genre Distribution\n({n_members} musicians)', 
              fontsize=14, fontweight='bold', pad=20)
    
    # 设置x轴标签
    plt.xticks(range(len(filtered_genres)), filtered_genres, 
               rotation=45, ha='right', fontsize=10)
    
    # 添加数值标签
    for i, (bar, mean, std) in enumerate(zip(bars, filtered_means, filtered_stds)):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + std + 0.01,
                f'{mean:.3f}', ha='center', va='bottom', fontsize=9)
    
    plt.grid(axis='y', alpha=0.3, linestyle='--')
    plt.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  [OK] 已保存图表: {save_path}")


def get_cluster_info(labels):
    """获取所有聚类的信息"""
    unique_labels = sorted(set(labels))
    cluster_info = []
    
    for label in unique_labels:
        if label == -1:
            continue
        count = list(labels).count(label)
        cluster_info.append({
            'cluster_id': label,
            'size': count
        })
    
    cluster_info.sort(key=lambda x: x['size'], reverse=True)
    return cluster_info


def main():
    """主函数"""
    print("="*80)
    print("聚类流派分布分析工具")
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
    
    # 执行聚类
    labels, coords, scaler = perform_clustering(ids, names, genres, X)
    
    # 保存聚类标签
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
            }
        }, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] 聚类标签已保存到: {labels_path}")
    
    # 显示聚类信息
    cluster_info = get_cluster_info(labels)
    print(f"\n{'='*80}")
    print("聚类信息 (按大小排序):")
    print(f"{'='*80}")
    print(f"{'聚类ID':<10} {'大小':<10} {'颜色索引'}")
    print("-" * 40)
    
    # 计算颜色映射（与可视化代码一致）
    n_clusters = len(cluster_info)
    colors_list = plt.cm.tab20(np.linspace(0, 1, n_clusters))
    
    for i, info in enumerate(cluster_info[:20]):  # 只显示前20个
        color_idx = i % 20
        print(f"Cluster {info['cluster_id']:<6} {info['size']:<10} (颜色索引: {color_idx})")
    
    if len(cluster_info) > 20:
        print(f"... 还有 {len(cluster_info) - 20} 个聚类")
    
    # 分析每个聚类（或用户指定的聚类）
    print(f"\n{'='*80}")
    print("开始分析各聚类的流派分布...")
    print(f"{'='*80}")
    
    # 分析前10个最大的聚类
    clusters_to_analyze = [info['cluster_id'] for info in cluster_info[:10]]
    
    all_analyses = {}
    for cluster_id in clusters_to_analyze:
        print(f"\n分析聚类 {cluster_id}...")
        analysis = analyze_cluster_genres(cluster_id, ids, names, genres, X, labels)
        if analysis:
            all_analyses[cluster_id] = analysis
            
            # 绘制图表
            plot_path = os.path.join(OUT_DIR, f'cluster_{cluster_id}_genre_distribution.png')
            plot_genre_distribution(analysis, plot_path)
            
            # 打印前5个主要流派
            print(f"  前5个主要流派:")
            for i, gs in enumerate(analysis['genre_stats'][:5], 1):
                print(f"    {i}. {gs['genre']}: {gs['mean']:.3f} ± {gs['std']:.3f}")
    
    # 保存所有分析结果
    results_path = os.path.join(OUT_DIR, 'cluster_genre_analyses.json')
    # 转换为可序列化格式
    serializable_analyses = {}
    for cluster_id, analysis in all_analyses.items():
        # 转换numpy类型为Python原生类型
        serializable_analysis = {
            'cluster_id': int(cluster_id),
            'n_members': int(analysis['n_members']),
            'member_ids': [str(id) for id in analysis['member_ids']],
            'member_names': analysis['member_names'],
            'genre_stats': analysis['genre_stats']
        }
        serializable_analyses[str(cluster_id)] = serializable_analysis
    
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(serializable_analyses, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] 所有分析结果已保存到: {results_path}")
    
    print(f"\n{'='*80}")
    print("分析完成！")
    print(f"所有结果已保存到: {OUT_DIR}/")
    print(f"{'='*80}")
    
    # 提示用户如何选择特定聚类
    print(f"\n提示: 要分析特定聚类，可以:")
    print(f"  1. 查看 {OUT_DIR}/cluster_*_genre_distribution.png 文件")
    print(f"  2. 或运行此脚本并修改 clusters_to_analyze 列表")


if __name__ == '__main__':
    main()

