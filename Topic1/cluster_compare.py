import os
import sys
import csv
import json
import math

# Optional deps
HAS_NUMPY = True
HAS_SK = True
HAS_PLOT = True
HAS_UMAP = True
try:
	import numpy as np
except Exception:
	HAS_NUMPY = False
try:
	import matplotlib.pyplot as plt
except Exception:
	HAS_PLOT = False
try:
	from sklearn.preprocessing import StandardScaler
	from sklearn.decomposition import PCA
	from sklearn.manifold import TSNE
	from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN
	from sklearn.metrics import silhouette_score
except Exception:
	HAS_SK = False
try:
	import umap  # umap-learn
except Exception:
	HAS_UMAP = False

INPUT_CSV = 'person_genre_matrix.csv'
OUT_DIR = 'cluster_outputs'

MAX_POINTS_TSNE = 15000  # 安全上限（过大将非常慢）
POINT_SIZE = 6
ALPHA = 0.8
RANDOM_STATE = 42


def load_matrix(path):
	with open(path, 'r', encoding='utf-8') as f:
		reader = csv.reader(f)
		header = next(reader)
		rows = list(reader)
	ids = [r[0] for r in rows]
	names = [r[1] for r in rows]
	genres = header[2:]
	X = [[float(x) for x in r[2:]] for r in rows]
	return ids, names, genres, X


def ensure_dir(d):
	if not os.path.isdir(d):
		os.makedirs(d, exist_ok=True)


def reduce_2d(X, method='pca'):
	if method == 'pca':
		p = PCA(n_components=2, random_state=RANDOM_STATE)
		coords = p.fit_transform(X)
		meta = {'method': 'pca', 'explained_variance_ratio': getattr(p, 'explained_variance_ratio_', []).tolist()}
		return coords, meta
	elif method == 'tsne':
		# t-SNE 很慢，必要时下采样
		tsne = TSNE(n_components=2, random_state=RANDOM_STATE, init='pca', learning_rate='auto', perplexity=30)
		coords = tsne.fit_transform(X)
		return coords, {'method': 'tsne'}
	elif method == 'umap':
		reducer = umap.UMAP(n_components=2, random_state=RANDOM_STATE, n_neighbors=15, min_dist=0.1)
		coords = reducer.fit_transform(X)
		return coords, {'method': 'umap'}
	else:
		raise ValueError('Unknown reduction method')


def cluster_labels(X, algo='kmeans', **kwargs):
	if algo == 'kmeans':
		k = kwargs.get('n_clusters', 8)
		model = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init='auto')
		labels = model.fit_predict(X)
		return labels, {'algo': 'kmeans', 'n_clusters': int(k)}
	elif algo == 'agglomerative':
		k = kwargs.get('n_clusters', 8)
		model = AgglomerativeClustering(n_clusters=k)
		labels = model.fit_predict(X)
		return labels, {'algo': 'agglomerative', 'n_clusters': int(k)}
	elif algo == 'dbscan':
		eps = kwargs.get('eps', 0.08)
		min_samples = kwargs.get('min_samples', 5)
		model = DBSCAN(eps=eps, min_samples=min_samples)
		labels = model.fit_predict(X)
		return labels, {'algo': 'dbscan', 'eps': float(eps), 'min_samples': int(min_samples)}
	else:
		raise ValueError('Unknown clustering algo')


def safe_silhouette(X, labels):
	try:
		# 至少应有两个簇且都非单点
		uniq = set(labels)
		if len(uniq) <= 1 or (len(uniq) == 2 and (-1 in uniq) and len(uniq) == 1):
			return None
		# 排除全部为-1的情况
		if all(l == -1 for l in labels):
			return None
		return float(silhouette_score(X, labels))
	except Exception:
		return None


def plot_scatter(coords, labels, title, out_path):
	if not HAS_PLOT:
		return False
	plt.figure(figsize=(10, 8))
	# 映射标签到颜色
	uniq = sorted(set(labels))
	if len(uniq) == 1:
		colors = ['#1f77b4'] * len(labels)
	else:
		cmap = plt.cm.get_cmap('tab20', max(2, len(uniq)))
		label_to_color = {lab: cmap(i % 20) for i, lab in enumerate(uniq)}
		colors = [label_to_color[l] for l in labels]
	plt.scatter(coords[:, 0], coords[:, 1], c=colors, s=POINT_SIZE, alpha=ALPHA, edgecolors='none')
	plt.title(title)
	plt.xlabel('Dim 1')
	plt.ylabel('Dim 2')
	plt.tight_layout()
	plt.savefig(out_path, dpi=150)
	plt.close()
	return True


def main():
	if not (HAS_NUMPY and HAS_SK):
		print('缺少依赖（numpy 或 scikit-learn），无法运行比较。')
		return
	try:
		ids, names, genres, X = load_matrix(INPUT_CSV)
	except FileNotFoundError:
		print(f'未找到 {INPUT_CSV}，请先运行 save_results.py 生成矩阵')
		return

	X = np.array(X, dtype=float)
	# 标准化有助于聚类
	scaler = StandardScaler()
	X_std = scaler.fit_transform(X)

	ensure_dir(OUT_DIR)

	reductions = [('pca', HAS_SK), ('tsne', HAS_SK), ('umap', HAS_UMAP)]
	k_list = [5, 8, 12]
	dbscan_settings = [(0.06, 5), (0.08, 5), (0.10, 5)]

	metrics = {'reductions': {}}

	for method, available in reductions:
		if not available:
			continue
		X_in = X_std
		if method == 'tsne' and len(X_in) > MAX_POINTS_TSNE:
			print(f't-SNE 样本过多({len(X_in)}). 建议先随机采样或改用 UMAP/PCA。跳过 t-SNE。')
			continue
		coords, rmeta = reduce_2d(X_in, method)
		coords = np.array(coords)
		mkey = method
		metrics['reductions'][mkey] = {'meta': rmeta, 'clusterings': []}

		# KMeans
		for k in k_list:
			labs, cmeta = cluster_labels(X_in, 'kmeans', n_clusters=k)
			sil = safe_silhouette(X_in, labs)
			title = f'{method.upper()} + KMeans(k={k})  Silhouette={sil:.3f}' if sil is not None else f'{method.upper()} + KMeans(k={k})'
			out_path = os.path.join(OUT_DIR, f'{method}_kmeans_k{k}.png')
			plot_scatter(coords, labs, title, out_path)
			metrics['reductions'][mkey]['clusterings'].append({'algo': 'kmeans', 'params': {'k': k}, 'silhouette': sil, 'plot': out_path})

		# Agglomerative
		for k in k_list:
			labs, cmeta = cluster_labels(X_in, 'agglomerative', n_clusters=k)
			sil = safe_silhouette(X_in, labs)
			title = f'{method.upper()} + Agglomerative(k={k})  Silhouette={sil:.3f}' if sil is not None else f'{method.upper()} + Agglomerative(k={k})'
			out_path = os.path.join(OUT_DIR, f'{method}_agg_k{k}.png')
			plot_scatter(coords, labs, title, out_path)
			metrics['reductions'][mkey]['clusterings'].append({'algo': 'agglomerative', 'params': {'k': k}, 'silhouette': sil, 'plot': out_path})

		# DBSCAN
		for eps, min_samples in dbscan_settings:
			labs, cmeta = cluster_labels(X_in, 'dbscan', eps=eps, min_samples=min_samples)
			sil = safe_silhouette(X_in, labs)
			core = sum(1 for l in labs if l != -1)
			title = f'{method.upper()} + DBSCAN(eps={eps},ms={min_samples})  Silhouette={sil:.3f}  Core={core}' if sil is not None else f'{method.upper()} + DBSCAN(eps={eps},ms={min_samples})  Core={core}'
			out_path = os.path.join(OUT_DIR, f'{method}_dbscan_eps{eps}_ms{min_samples}.png')
			plot_scatter(coords, labs, title, out_path)
			metrics['reductions'][mkey]['clusterings'].append({'algo': 'dbscan', 'params': {'eps': eps, 'min_samples': min_samples}, 'silhouette': sil, 'core': core, 'plot': out_path})

	# 保存指标
	with open(os.path.join(OUT_DIR, 'cluster_metrics.json'), 'w', encoding='utf-8') as f:
		json.dump(metrics, f, ensure_ascii=False, indent=2)
	print(f'✓ 已输出比较图与指标至 {OUT_DIR}/')


if __name__ == '__main__':
	main()

















