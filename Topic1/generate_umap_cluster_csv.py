"""
生成包含UMAP坐标和聚类信息的CSV文件，供前端可视化使用
"""
import os
import sys
import csv
import json
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN

try:
    import umap
    HAS_UMAP = True
except ImportError:
    HAS_UMAP = False
    print("错误: 未安装 umap-learn")
    sys.exit(1)

# 设置输出编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 使用相对于脚本所在目录的路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_CSV = os.path.join(SCRIPT_DIR, 'data', 'person_genre_matrix.csv')
OUTPUT_CSV = os.path.join(SCRIPT_DIR, 'viz-app', 'public', 'data', 'person_genre_matrix.csv')
RANDOM_STATE = 42

# 使用与fine_tune实验相同的参数
DBSCAN_EPS = 0.1
DBSCAN_MIN_SAMPLES = 15


def load_matrix(path):
    """加载人员×流派矩阵"""
    print(f"正在加载 {path}...")
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        # 跳过可能的空行
        header = None
        for line in reader:
            if line and line[0].strip():
                header = line
                break
        rows = list(reader)
        # 过滤空行
        rows = [r for r in rows if r and len(r) > 2 and r[0].strip()]
    
    ids = [r[0] for r in rows]
    names = [r[1] for r in rows]
    genres = header[2:] if header else []
    X = np.array([[float(x) for x in r[2:]] for r in rows], dtype=float)
    
    print(f"  加载完成: {len(ids)} 个音乐人, {len(genres)} 个流派")
    return ids, names, genres, X, header, rows


def reduce_dimension(X, method='umap', n_components=2):
    """降维到2D"""
    if method == 'umap':
        if not HAS_UMAP:
            raise ValueError("UMAP 未安装")
        print(f"  运行 UMAP (样本数: {len(X)})...")
        reducer = umap.UMAP(n_components=n_components, random_state=RANDOM_STATE, 
                           n_neighbors=15, min_dist=0.1, metric='euclidean')
        coords = reducer.fit_transform(X)
        print(f"  UMAP完成: {coords.shape}")
        return coords
    else:
        raise ValueError(f"未知的降维方法: {method}")


def apply_dbscan(X, eps, min_samples):
    """应用DBSCAN聚类"""
    print(f"  运行 DBSCAN (eps={eps}, min_samples={min_samples})...")
    model = DBSCAN(eps=eps, min_samples=min_samples)
    labels = model.fit_predict(X)
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    print(f"  聚类完成: {n_clusters} 个聚类, {n_noise} 个噪声点")
    return labels


def main():
    """主函数"""
    print("="*80)
    print("生成包含UMAP坐标和聚类信息的CSV文件")
    print("="*80)
    
    # 检查输入文件
    if not os.path.exists(INPUT_CSV):
        print(f"错误: 未找到 {INPUT_CSV}")
        return
    
    # 加载数据
    ids, names, genres, X, header, rows = load_matrix(INPUT_CSV)
    
    # 标准化数据
    print("\n标准化数据...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 降维
    print(f"\n降维方法: UMAP")
    coords = reduce_dimension(X_scaled, method='umap')
    
    # DBSCAN聚类
    labels = apply_dbscan(X_scaled, DBSCAN_EPS, DBSCAN_MIN_SAMPLES)
    
    # 创建输出目录
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    
    # 写入新的CSV文件，包含umap_x, umap_y, cluster列
    print(f"\n写入输出文件: {OUTPUT_CSV}")
    with open(OUTPUT_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        # 写入表头：原有列 + umap_x, umap_y, cluster
        new_header = header + ['umap_x', 'umap_y', 'cluster']
        writer.writerow(new_header)
        
        # 写入数据行
        for i, row in enumerate(rows):
            new_row = row + [str(coords[i, 0]), str(coords[i, 1]), str(int(labels[i]))]
            writer.writerow(new_row)
    
    print(f"✓ 已保存到: {OUTPUT_CSV}")
    print(f"  总行数: {len(rows)}")
    print(f"  包含列: {len(new_header)} (原有{len(header)}列 + umap_x, umap_y, cluster)")
    
    print(f"\n{'='*80}")
    print("完成！")
    print(f"{'='*80}")


if __name__ == '__main__':
    main()

