"""Train a regression model that predicts high-scoring musicians based on notable signals.

The script follows the user-provided plan:
1. Build a target score for every Person node by aggregating notable interactions.
2. Engineer graph-topological, statistical, and embedding-style features.
3. Fit an XGBoost regressor and report evaluation metrics.
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# ================= 配置区域 =================
# 核心修改 1: 降低训练门槛，纳入中层艺人
TRAINING_THRESHOLD_SCORE = 1.0 
TRAINING_THRESHOLD_PR = 1e-4    
# ===========================================
from data_preprocessing import MusicGraphProcessor

try:
    from xgboost import XGBRegressor
except ImportError as exc:  # pragma: no cover - dependency guard
    raise SystemExit(
        "xgboost is required for this script. Install via `pip install xgboost`."
    ) from exc

INFLUENCE_EDGE_TYPES = {"DirectlySamples", "CoverOf", "InStyleOf"}
INFLUENCE_WEIGHTS = {
    "CoverOf": 5.0,
    "DirectlySamples": 4.0,
    "InterpolatesFrom": 3.0,
    "LyricalReferenceTo": 3.0,
    "InStyleOf": 2.0,
}
ROLE_EDGE_TYPES = {"PerformerOf", "ComposerOf", "LyricistOf", "ProducerOf"}
RECORD_LABEL_EDGE_TYPES = {"RecordedBy", "DistributedBy"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Predict high-scoring artists using notable-based targets"
    )
    parser.add_argument(
        "--graph",
        type=Path,
        default=Path("Topic1_graph.json"),
        help="Path to Topic1_graph.json",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Test split size (default: 0.2)",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--embedding-dim",
        type=int,
        default=32,
        help="Dimension of collaboration-graph spectral embedding",
    )
    parser.add_argument(
        "--predictions-csv",
        type=Path,
        default=Path("output/artist_success_predictions.csv"),
        help="Path to save full prediction results",
    )
    parser.add_argument(
        "--model-output",
        type=Path,
        default=None,
        help="Optional path to pickle the trained model",
    )
    parser.add_argument(
        "--feature-output",
        type=Path,
        default=Path("output/artist_features.parquet"),
        help="Path to export engineered features (parquet)",
    )
    parser.add_argument(
        "--n-estimators",
        type=int,
        default=600,
        help="Number of trees for XGBoost",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.05,
        help="Learning rate for XGBoost",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=6,
        help="Maximum depth of trees",
    )
    parser.add_argument(
        "--subsample",
        type=float,
        default=0.8,
        help="Subsample ratio of the training instances",
    )
    parser.add_argument(
        "--colsample-bytree",
        type=float,
        default=0.8,
        help="Subsample ratio of columns when constructing each tree",
    )
    return parser.parse_args()


def load_graph(path: Path) -> Tuple[nx.MultiDiGraph, Dict[str, List[dict]]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    graph = nx.node_link_graph(data, multigraph=True, directed=True)
    return graph, data


def build_person_work_maps(processor: MusicGraphProcessor) -> Tuple[
    Dict[int, dict],
    Dict[int, List[dict]],
    Dict[int, List[int]],
]:
    persons = {node["id"]: node for node in processor.get_nodes_by_type("Person")}
    person_to_works: Dict[int, List[dict]] = {}
    work_to_persons: Dict[int, List[int]] = defaultdict(list)

    for pid in persons.keys():
        works_by_role = processor.get_person_works(pid)
        flattened = []
        for role_works in works_by_role.values():
            flattened.extend(role_works)
        unique_works = list({w["id"]: w for w in flattened}.values())
        person_to_works[pid] = unique_works
        for work in unique_works:
            work_to_persons[work["id"]].append(pid)

    return persons, person_to_works, work_to_persons


def compute_artist_influence(
    links: List[dict],
    work_to_persons: Dict[int, List[int]],
) -> Dict[int, float]:
    """Aggregate influence weights for each artist based on their works."""
    totals: Dict[int, float] = defaultdict(float)
    for edge in links:
        weight = INFLUENCE_WEIGHTS.get(edge.get("Edge Type"))
        if weight is None:
            continue
        target_work = edge.get("target")
        if target_work is None:
            continue
        for pid in work_to_persons.get(target_work, []):
            totals[pid] += weight
    return totals


def compute_target_scores(
    processor: MusicGraphProcessor,
    person_to_works: Dict[int, List[dict]],
) -> Dict[int, float]:
    weights = {
        "notable_direct": 10.0,
        "sampled_by_notable": 5.0,
        "cover_notable": 2.0,
    }
    targets: Dict[int, float] = {}

    for pid, works in person_to_works.items():
        score = 0.0
        for work in works:
            work_id = work["id"]
            if work.get("notable"):
                score += weights["notable_direct"]

            # for edge_type, source_id in processor.get_edges_to(work_id):
            #     if edge_type in INFLUENCE_EDGE_TYPES:
            #         source_node = processor.get_node(source_id)
            #         if source_node and source_node.get("notable"):
            #             score += weights["sampled_by_notable"]

            # for edge_type, target_id in processor.get_edges_from(work_id):
            #     if edge_type in INFLUENCE_EDGE_TYPES:
            #         target_node = processor.get_node(target_id)
            #         if target_node and target_node.get("notable"):
            #             score += weights["cover_notable"]

        targets[pid] = math.log1p(score)

    return targets


def build_collaboration_graph(
    person_ids: Iterable[int],
    work_to_persons: Dict[int, List[int]],
) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(person_ids)

    for person_list in work_to_persons.values():
        if len(person_list) < 2:
            continue
        for i, pid in enumerate(person_list):
            for other_pid in person_list[i + 1 :]:
                graph.add_edge(pid, other_pid)

    return graph


def build_influence_graph(
    processor: MusicGraphProcessor,
    data_links: List[dict],
    work_to_persons: Dict[int, List[int]],
    person_ids: Iterable[int],
) -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_nodes_from(person_ids)

    for edge in data_links:
        edge_type = edge.get("Edge Type")
        if edge_type not in INFLUENCE_EDGE_TYPES:
            continue
        source_work = edge["source"]
        target_work = edge["target"]
        source_persons = work_to_persons.get(source_work, [])
        target_persons = work_to_persons.get(target_work, [])
        if not source_persons or not target_persons:
            continue
        for sp in source_persons:
            for tp in target_persons:
                if sp == tp:
                    continue
                graph.add_edge(sp, tp)

    return graph


def safe_pagerank(graph: nx.DiGraph) -> Dict[int, float]:
    if graph.number_of_edges() == 0:
        return {node: 0.0 for node in graph.nodes}
    return nx.pagerank(graph, alpha=0.85)


def safe_hits(graph: nx.DiGraph) -> Tuple[Dict[int, float], Dict[int, float]]:
    if graph.number_of_edges() == 0:
        zeros = {node: 0.0 for node in graph.nodes}
        return zeros, zeros
    hubs, authorities = nx.hits(graph, max_iter=1000, tol=1e-08)
    return hubs, authorities


def safe_eigenvector(graph: nx.Graph) -> Dict[int, float]:
    if graph.number_of_edges() == 0:
        return {node: 0.0 for node in graph.nodes}
    try:
        return nx.eigenvector_centrality(graph, max_iter=1000, tol=1e-06)
    except nx.NetworkXException:
        return {node: 0.0 for node in graph.nodes}


def compute_spectral_embedding(
    graph: nx.Graph, dim: int
) -> Dict[int, np.ndarray]:
    nodes = list(graph.nodes)
    if len(nodes) <= 1:
        return {node: np.zeros(dim) for node in nodes}

    effective_dim = min(dim, len(nodes) - 1)
    adjacency = nx.to_scipy_sparse_array(graph, nodelist=nodes, dtype=float)
    svd = TruncatedSVD(n_components=effective_dim, random_state=42)
    latent = svd.fit_transform(adjacency)

    embeddings: Dict[int, np.ndarray] = {}
    for idx, node in enumerate(nodes):
        emb = latent[idx]
        if effective_dim < dim:
            padded = np.zeros(dim)
            padded[:effective_dim] = emb
            embeddings[node] = padded
        else:
            embeddings[node] = emb
    return embeddings


def entropy_from_counter(counter: Counter[str]) -> float:
    total = sum(counter.values())
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in counter.values():
        p = count / total
        entropy -= p * math.log(p + 1e-12, 2)
    return entropy


def extract_year(node: dict) -> int | None:
    for field in ("release_date", "written_date", "notoriety_date"):
        value = node.get(field)
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


def compute_statistical_features(
    processor, pid, works, work_to_persons, 
    pagerank_val=0.0, collab_degree_val=0, max_neighbor_pr=0.0
):
    total_works = len(works)
    safe_works = max(total_works, 1)
    
    genres = Counter([w.get("genre") for w in works if w.get("genre")])
    years = []
    for w in works:
        val = w.get("release_date") or w.get("written_date")
        if val and str(val).isdigit(): years.append(int(val))
    
    recent_year = max(years) if years else 0
    span = (max(years) - min(years)) if len(years) > 1 else 0
    
    # === 关键特征构造 ===
    return {
        "total_works": total_works,
        "genre_entropy": entropy_from_counter(genres),
        "career_span": span,
        "recent_year": recent_year,
        "avg_year": sum(years)/len(years) if years else 0,
        
        # 效率特征：作品少但 PR 高，说明单曲质量爆炸
        "pr_efficiency": pagerank_val / safe_works,
        
        # 借势特征：你的邻居是否比你强很多？
        "max_neighbor_pr": max_neighbor_pr,
        "leverage_ratio": max_neighbor_pr / (pagerank_val + 1e-9),
        
        # 潜力新人标记
        "is_fresh": 1.0 if (total_works <= 3 and recent_year >= 2020) else 0.0
    }


def assemble_feature_table(
    processor, targets, person_to_works, work_to_persons, 
    collab_graph, influence_graph, pagerank, hubs, authorities, eigenvector, embeddings, degree_centrality
):
    rows = []
    for pid, target in targets.items():
        works = person_to_works.get(pid, [])
        pr_val = pagerank.get(pid, 0.0)
        
        # 获取最强邻居 PR
        neighbors = list(collab_graph.neighbors(pid)) if pid in collab_graph else []
        max_neigh_pr = max([pagerank.get(n, 0.0) for n in neighbors]) if neighbors else 0.0
        
        stats = compute_statistical_features(
            processor, pid, works, work_to_persons,
            pagerank_val=pr_val,
            collab_degree_val=collab_graph.degree(pid),
            max_neighbor_pr=max_neigh_pr
        )
        
        row = {
            "person_id": pid,
            "name": processor.get_node(pid).get("name", "Unknown"),
            "target_score": target,
            "pagerank": pr_val,
            "hub_score": hubs.get(pid, 0.0),
            "authority_score": authorities.get(pid, 0.0),
            "collab_degree": collab_graph.degree(pid),
            "eigenvector": eigenvector.get(pid, 0.0),
        }
        row.update(stats)
        
        # Embeddings
        emb = embeddings.get(pid)
        if emb is not None:
            for i, v in enumerate(emb): row[f"embed_{i}"] = float(v)
            
        rows.append(row)
    
    return pd.DataFrame(rows).fillna(0.0)


def train_model(df, test_size, random_state, args):
    feature_cols = [c for c in df.columns if c not in {"person_id", "name", "target_score", "predicted_score", "residual"}]
    
    # === 核心修改：放宽训练门槛 ===
    # 只要有任何一点成绩(>1.0) 或者 稍微有一点点影响力(>1e-5) 的人，都算“入门了”。
    # 我们让模型学习“从入门到精通”的规律，而不仅仅是“精通”的规律。
    train_mask = (df["target_score"] > TRAINING_THRESHOLD_SCORE) | (df["pagerank"] > TRAINING_THRESHOLD_PR)
    
    df_train = df[train_mask].copy()
    print(f"💎 Training Set Size: {len(df_train)} (Filtered from {len(df)})")
    
    X = df_train[feature_cols].values
    y = df_train["target_score"].values
    
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=test_size, random_state=random_state)
    
    model = XGBRegressor(
        objective="reg:squarederror",
        n_estimators=args.n_estimators,
        learning_rate=args.learning_rate,
        max_depth=args.max_depth,
        subsample=args.subsample,
        colsample_bytree=args.colsample_bytree,
        random_state=random_state,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    
    # 预测全量
    full_preds = model.predict(df[feature_cols].values)
    res_df = df.copy()
    res_df["predicted_score"] = full_preds
    res_df["residual"] = res_df["target_score"] - res_df["predicted_score"]
    
    # 计算验证集指标
    val_preds = model.predict(X_val)
    metrics = {
        "rmse": float(np.sqrt(mean_squared_error(y_val, val_preds))),
        "r2": float(r2_score(y_val, val_preds)),
        "n_train": len(y_train)
    }
    
    return model, metrics, res_df

def main() -> None:
    args = parse_args()

    graph, raw_data = load_graph(args.graph)
    processor = MusicGraphProcessor(str(args.graph))
    persons, p2w, w2p = build_person_work_maps(processor)
    targets = compute_target_scores(processor, p2w)
    artist_influence = compute_artist_influence(raw_data["links"], w2p)
    
    collab_g = build_collaboration_graph(persons.keys(), w2p)
    # 这里注意：确保你原来的 build_influence_graph 逻辑是正确的
    infl_g = nx.DiGraph() # Placeholder, use your original function
    infl_g.add_nodes_from(persons.keys())
    for link in raw_data["links"]:
        if link["Edge Type"] in INFLUENCE_EDGE_TYPES:
            # 简化的逻辑，请替换为你更完善的逻辑
            s, t = link["source"], link["target"]
            s_ps = w2p.get(s, [])
            t_ps = w2p.get(t, [])
            for sp in s_ps:
                for tp in t_ps:
                    if sp!=tp: infl_g.add_edge(sp, tp)

    pr = safe_pagerank(infl_g)
    hubs, auths = safe_hits(infl_g)
    eig = safe_eigenvector(collab_g)
    deg = nx.degree_centrality(collab_g)
    embs = compute_spectral_embedding(collab_g, args.embedding_dim)
    
    df = assemble_feature_table(processor, targets, p2w, w2p, collab_g, infl_g, pr, hubs, auths, eig, embs, deg)
    df["influence_weight"] = df["person_id"].map(lambda pid: artist_influence.get(pid, 0.0))

    low_output_mask = (df["total_works"] <= 1) & (df["influence_weight"] <= 0.0)
    filtered_df = df.loc[~low_output_mask].copy()
    removed = low_output_mask.sum()
    if removed:
        print(f"[INFO] Dropped {removed} low-output / zero-influence artists before training.")
    else:
        print("[INFO] No low-output / zero-influence artists detected for removal.")

    # 保存特征
    args.feature_output.parent.mkdir(parents=True, exist_ok=True)
    filtered_df.to_parquet(args.feature_output, index=False)

    # 训练
    model, metrics, preds = train_model(filtered_df, args.test_size, args.random_state, args)
    
    print(f"R^2: {metrics['r2']:.4f}")
    
    # 保存
    args.predictions_csv.parent.mkdir(parents=True, exist_ok=True)
    preds.to_csv(args.predictions_csv, index=False)
    if args.model_output:
        with open(args.model_output, "wb") as f: pickle.dump(model, f)
        
    # === 自动筛选潜力股 (直接打印出来) ===
    print("\n🔎 Hunt for the 'Co-Signed' Artists (Low works, High Connections):")
    
    # 筛选逻辑：
    # 1. 还没红 (Target Score 低)
    # 2. 作品少 (Total Works < 5)
    # 3. 认识大哥 (Max Neighbor PR > 0)
    # 4. 预测分还可以 (Predicted > 1.5)
    mask = (preds["target_score"] < 1.5) & \
           (preds["total_works"] <= 5) & \
           (preds["max_neighbor_pr"] > 0.0) & \
           (preds["predicted_score"] > 1.5)
           
    candidates = preds[mask].sort_values(by="leverage_ratio", ascending=False).head(10)
    
    if not candidates.empty:
        print(candidates[["name", "total_works", "target_score", "predicted_score", "max_neighbor_pr", "leverage_ratio"]].to_string(index=False))
    else:
        print("No candidates found with strict filter. Try relaxing thresholds.")

if __name__ == "__main__":
    main()