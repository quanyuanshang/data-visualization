"""
调优DBSCAN参数，找到合适的参数组合
目标：减少聚类数量，每个聚类至少15人
"""
import os
import sys
import csv
import json
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
import argparse
import os

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

INPUT_CSV = 'data/person_genre_matrix.csv'
RANDOM_STATE = 42
MIN_CLUSTER_SIZE = 15  # 每个聚类至少15人


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


def test_dbscan_params(X_scaled, eps_values, min_samples_values):
    """测试不同的DBSCAN参数组合"""
    print("\n" + "="*80)
    print("测试DBSCAN参数组合")
    print("="*80)
    
    results = []
    
    for eps in eps_values:
        for min_samples in min_samples_values:
            model = DBSCAN(eps=eps, min_samples=min_samples)
            labels = model.fit_predict(X_scaled)
            
            # 统计聚类信息
            unique_labels = set(labels)
            n_clusters = len([l for l in unique_labels if l != -1])
            n_noise = list(labels).count(-1)
            
            # 统计每个聚类的大小
            cluster_sizes = {}
            for label in labels:
                if label != -1:
                    cluster_sizes[label] = cluster_sizes.get(label, 0) + 1
            
            # 计算满足最小大小的聚类数
            valid_clusters = [size for size in cluster_sizes.values() if size >= MIN_CLUSTER_SIZE]
            n_valid_clusters = len(valid_clusters)
            n_small_clusters = n_clusters - n_valid_clusters
            
            # 计算小聚类中的总人数
            small_cluster_members = sum(size for size in cluster_sizes.values() if size < MIN_CLUSTER_SIZE)
            
            result = {
                'eps': eps,
                'min_samples': min_samples,
                'n_clusters': n_clusters,
                'n_valid_clusters': n_valid_clusters,
                'n_small_clusters': n_small_clusters,
                'n_noise': n_noise,
                'small_cluster_members': small_cluster_members,
                'total_members': len(labels) - n_noise,
                'max_cluster_size': max(cluster_sizes.values()) if cluster_sizes else 0,
                'min_cluster_size': min(cluster_sizes.values()) if cluster_sizes else 0,
                'avg_cluster_size': np.mean(list(cluster_sizes.values())) if cluster_sizes else 0
            }
            results.append(result)
            
            print(f"\neps={eps:.2f}, min_samples={min_samples}:")
            print(f"  总聚类数: {n_clusters}, 有效聚类(≥{MIN_CLUSTER_SIZE}人): {n_valid_clusters}")
            print(f"  小聚类数(<{MIN_CLUSTER_SIZE}人): {n_small_clusters}, 噪声点: {n_noise}")
            print(f"  聚类大小范围: {result['min_cluster_size']}-{result['max_cluster_size']}, "
                  f"平均: {result['avg_cluster_size']:.1f}")
    
    return results


def find_best_params(results):
    """找到最佳参数组合"""
    print("\n" + "="*80)
    print("推荐参数组合（按有效聚类数排序）")
    print("="*80)
    
    # 按有效聚类数排序，然后按总聚类数排序（更少更好）
    sorted_results = sorted(results, 
                           key=lambda x: (-x['n_valid_clusters'], x['n_clusters'], x['n_noise']))
    
    print(f"\n{'eps':<8} {'min_samples':<12} {'总聚类':<8} {'有效聚类':<10} {'小聚类':<8} {'噪声点':<8} {'平均大小':<10}")
    print("-" * 80)
    
    for i, r in enumerate(sorted_results[:10], 1):
        print(f"{r['eps']:<8.2f} {r['min_samples']:<12} {r['n_clusters']:<8} "
              f"{r['n_valid_clusters']:<10} {r['n_small_clusters']:<8} "
              f"{r['n_noise']:<8} {r['avg_cluster_size']:<10.1f}")
    
    # 推荐最佳参数
    best = sorted_results[0]
    print(f"\n推荐参数: eps={best['eps']:.2f}, min_samples={best['min_samples']}")
    print(f"  将产生 {best['n_valid_clusters']} 个有效聚类（每个≥{MIN_CLUSTER_SIZE}人）")
    print(f"  总聚类数: {best['n_clusters']}, 噪声点: {best['n_noise']}")
    
    return best


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="DBSCAN 参数调优并导出 UMAP 可视化 CSV")
    parser.add_argument("--input", default=INPUT_CSV, help="输入的人员×流派矩阵 CSV 路径")
    parser.add_argument("--export-umap", action="store_true", help="导出前端可视化所需的 UMAP CSV")
    parser.add_argument("--umap-csv", default=os.path.join("viz-app", "public", "data", "person_genre_matrix.csv"),
                        help="导出的 UMAP CSV 路径（默认写入前端数据目录）")
    args = parser.parse_args()

    print("="*80)
    print("DBSCAN参数调优工具")
    print(f"目标: 每个聚类至少包含 {MIN_CLUSTER_SIZE} 个音乐人")
    print("="*80)
    
    # 加载数据
    ids, names, genres, X = load_matrix(args.input)
    
    # 标准化数据
    print("\n标准化数据...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # UMAP降维（固定参数）
    print("\n运行 UMAP 降维...")
    reducer = umap.UMAP(n_components=2, random_state=RANDOM_STATE, 
                       n_neighbors=15, min_dist=0.1, metric='euclidean')
    coords = reducer.fit_transform(X_scaled)
    print(f"  降维完成: {coords.shape}")
    
    # 注意：DBSCAN在原始特征空间上运行，不是在降维后的空间
    # 但为了与之前的分析一致，我们在标准化后的特征空间上运行
    
    # 测试不同的参数组合
    eps_values = [0.10, 0.12, 0.15, 0.18, 0.20, 0.25, 0.30]
    min_samples_values = [5, 10, 15]
    
    results = test_dbscan_params(X_scaled, eps_values, min_samples_values)
    
    # 找到最佳参数
    best_params = find_best_params(results)
    
    # 保存结果
    output_path = 'dbscan_param_tuning_results.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'min_cluster_size': MIN_CLUSTER_SIZE,
            'best_params': best_params,
            'all_results': results
        }, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] 调优结果已保存到: {output_path}")
    
    # 使用最佳参数在标准化空间运行一次 DBSCAN，得到最终聚类标签（供导出）
    labels = None
    if best_params is not None:
        print("\n使用最佳参数运行 DBSCAN 以生成聚类标签用于导出...")
        model = DBSCAN(eps=best_params['eps'], min_samples=best_params['min_samples'])
        labels = model.fit_predict(X_scaled)
        print("  完成。")

    # 可选导出：前端所需 UMAP 坐标 CSV
    if args.export_umap:
        # 计算 UMAP 2D（使用上文同样的设定）
        print("\n计算 UMAP 2D 用于前端可视化导出...")
        reducer = umap.UMAP(n_components=2, random_state=RANDOM_STATE, 
                           n_neighbors=15, min_dist=0.1, metric='euclidean')
        coords = reducer.fit_transform(X_scaled)
        print(f"  降维完成: {coords.shape}")

        # 主导风格：按原始占比矩阵 X 的 argmax
        dom_idx = np.argmax(X, axis=1)
        dominant_genre = [genres[i] for i in dom_idx]

        # 创建输出目录
        out_dir = os.path.dirname(args.umap_csv)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        # 写 CSV：id,name,umap_x,umap_y,dominant_genre,cluster
        print(f"导出可视化 CSV -> {args.umap_csv}")
        with open(args.umap_csv, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "umap_x", "umap_y", "dominant_genre", "cluster"])
            for i in range(len(ids)):
                cid = ids[i]
                cname = names[i]
                x, y = coords[i, 0], coords[i, 1]
                dgenre = dominant_genre[i]
                clabel = "" if labels is None else (labels[i] if labels[i] != -1 else "noise")
                writer.writerow([cid, cname, x, y, dgenre, clabel])
        print("[OK] 导出完成。刷新前端页面可查看 UMAP 主视图。")

    print("\n" + "="*80)
    print("下一步:")
    print(f"  使用推荐参数重新运行聚类分析")
    print(f"  或手动选择参数: eps={best_params['eps']:.2f}, min_samples={best_params['min_samples']}")
    print("="*80)


if __name__ == '__main__':
    main()





