import sys
import csv
import json

# 尝试导入可选依赖
try:
	import numpy as np
	import matplotlib.pyplot as plt
	from sklearn.decomposition import PCA
	HAS_DEPS = True
except Exception:
	HAS_DEPS = False

INPUT_CSV = 'person_genre_matrix.csv'  # 由 save_results.py 生成
OUTPUT_PNG = 'person_genre_scatter.png'
OUTPUT_META = 'person_genre_scatter_meta.json'


def load_matrix(path):
	with open(path, 'r', encoding='utf-8') as f:
		reader = csv.reader(f)
		header = next(reader)
		rows = list(reader)
	# header: person_id, name, <genres...>
	ids = [r[0] for r in rows]
	names = [r[1] for r in rows]
	genres = header[2:]
	X = [[float(x) for x in r[2:]] for r in rows]
	return ids, names, genres, X


def main():
	try:
		ids, names, genres, X = load_matrix(INPUT_CSV)
	except FileNotFoundError:
		print(f'未找到 {INPUT_CSV}，请先运行 save_results.py 生成矩阵')
		return

	if not HAS_DEPS:
		print('未检测到可视化依赖（numpy/matplotlib/sklearn）。已保留 CSV，可在外部工具绘图。')
		return

	X = np.array(X)
	# PCA降维到2D
	pca = PCA(n_components=2, random_state=42)
	coords = pca.fit_transform(X)

	# 颜色：按每人占比最高的流派上色
	dominant_idx = np.argmax(X, axis=1)
	unique_idxs = sorted(set(dominant_idx))
	# 安全生成颜色
	cmap = plt.cm.get_cmap('tab20', len(unique_idxs))
	color_map = {idx: cmap(i) for i, idx in enumerate(unique_idxs)}
	colors = [color_map[i] for i in dominant_idx]

	plt.figure(figsize=(10, 7))
	plt.scatter(coords[:, 0], coords[:, 1], c=colors, s=12, alpha=0.8, edgecolors='none')
	plt.title('Person vs Genre Share (PCA)')
	plt.xlabel('PC1')
	plt.ylabel('PC2')
	# 图例
	handles = []
	labels = []
	for idx in unique_idxs:
		handles.append(plt.Line2D([0], [0], marker='o', color='w', label=genres[idx], markerfacecolor=color_map[idx], markersize=6))
		labels.append(genres[idx])
	plt.legend(handles, labels, bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
	plt.tight_layout()
	plt.savefig(OUTPUT_PNG, dpi=150)
	print(f'✓ 已保存散点图: {OUTPUT_PNG}')

	# 导出元信息，便于前端或复现实验
	# 注意：numpy 数组不能直接用于 and 判断，这里单独取出并判断 None
	ev_ratio = getattr(pca, 'explained_variance_ratio_', None)
	meta = {
		'point_count': len(ids),
		'genres': genres,
		'explained_variance_ratio': ev_ratio.tolist() if ev_ratio is not None else None
	}
	with open(OUTPUT_META, 'w', encoding='utf-8') as f:
		json.dump(meta, f, ensure_ascii=False, indent=2)
	print(f'✓ 已保存元信息: {OUTPUT_META}')


if __name__ == '__main__':
	main()
