"""
分析用户指定的特定聚类
使用已保存的聚类标签
"""
import os
import sys
import csv
import json
import numpy as np
import matplotlib.pyplot as plt

# 设置输出编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

INPUT_CSV = 'person_genre_matrix.csv'
CLUSTER_LABELS_JSON = 'cluster_analysis/cluster_labels.json'
OUT_DIR = 'cluster_analysis'


def load_matrix(path):
    """加载人员×流派矩阵"""
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    
    ids = [r[0] for r in rows]
    names = [r[1] for r in rows]
    genres = header[2:]
    X = np.array([[float(x) for x in r[2:]] for r in rows], dtype=float)
    
    return ids, names, genres, X


def load_cluster_labels(path):
    """加载聚类标签"""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['ids'], data['names'], data['labels']


def analyze_cluster_genres(cluster_id, ids, names, genres, X, labels):
    """分析特定聚类的流派分布"""
    # 获取该聚类的所有音乐人索引
    cluster_indices = [i for i, label in enumerate(labels) if int(label) == int(cluster_id)]
    
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
    
    # 只显示平均占比大于阈值的流派
    threshold = 0.01  # 只显示平均占比>1%的流派
    filtered = [(g, m, s) for g, m, s in zip(genres, means, stds) if m > threshold]
    
    # 如果太多，只显示前20个
    if len(filtered) > 20:
        filtered = filtered[:20]
    
    if not filtered:
        print("警告: 没有流派满足显示条件（平均占比>1%）")
        # 显示所有流派
        filtered = list(zip(genres, means, stds))[:20]
    
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


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python analyze_specific_cluster.py <cluster_id>")
        print("\n示例: python analyze_specific_cluster.py 0")
        print("      python analyze_specific_cluster.py 5")
        return
    
    cluster_id = int(sys.argv[1])
    
    print("="*80)
    print(f"分析聚类 {cluster_id} 的流派分布")
    print("="*80)
    
    # 加载数据
    print("\n加载数据...")
    ids, names, genres, X = load_matrix(INPUT_CSV)
    label_ids, label_names, labels = load_cluster_labels(CLUSTER_LABELS_JSON)
    
    # 验证数据一致性
    if len(ids) != len(labels):
        print("警告: 数据长度不匹配")
    
    # 分析指定聚类
    analysis = analyze_cluster_genres(cluster_id, ids, names, genres, X, labels)
    
    if analysis:
        # 打印前10个主要流派
        print(f"\n前10个主要流派:")
        for i, gs in enumerate(analysis['genre_stats'][:10], 1):
            print(f"  {i}. {gs['genre']}: {gs['mean']:.3f} ± {gs['std']:.3f} "
                  f"(范围: {gs['min']:.3f} - {gs['max']:.3f})")
        
        # 绘制图表
        plot_path = os.path.join(OUT_DIR, f'cluster_{cluster_id}_genre_distribution.png')
        plot_genre_distribution(analysis, plot_path)
        
        # 保存分析结果
        result_path = os.path.join(OUT_DIR, f'cluster_{cluster_id}_analysis.json')
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump({
                'cluster_id': int(cluster_id),
                'n_members': int(analysis['n_members']),
                'member_ids': [str(id) for id in analysis['member_ids']],
                'member_names': analysis['member_names'],
                'genre_stats': analysis['genre_stats']
            }, f, ensure_ascii=False, indent=2)
        print(f"\n[OK] 分析结果已保存到: {result_path}")
    else:
        print("分析失败")


if __name__ == '__main__':
    main()








