"""
计算每首歌（或专辑）的影响力分数。

权重：
- CoverOf（翻唱）            : 5
- DirectlySamples（采样）    : 4
- LyricalReferenceTo（引用） : 3
- InterpolatesFrom（插值/引用）: 3  （未指定，按引用处理）
- InStyleOf（模仿/风格）      : 2

输入：data/Topic1_graph.json
输出：data/song_influence.json
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any

WEIGHTS = {
    "CoverOf": 5,
    "DirectlySamples": 4,
    "LyricalReferenceTo": 3,
    "InterpolatesFrom": 3,  # 未明确权重，按引用处理
    "InStyleOf": 2,
}


def load_graph(graph_path: Path) -> Dict[str, Any]:
    with graph_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def calc_influence(graph: Dict[str, Any]):
    nodes = graph.get("nodes", [])
    edges = graph.get("links", [])  # 图数据使用 links

    # 仅对 Song / Album 计算
    songs = {
        n["id"]: n
        for n in nodes
        if n.get("Node Type") in ("Song", "Album")
    }

    influence_score = defaultdict(float)
    breakdown = defaultdict(lambda: defaultdict(int))

    for edge in edges:
        etype = edge.get("Edge Type")
        weight = WEIGHTS.get(etype)
        if weight is None:
            continue

        src = edge.get("source")
        tgt = edge.get("target")
        if tgt not in songs:
            continue  # 只累计到歌曲/专辑节点

        influence_score[tgt] += weight
        breakdown[tgt][etype] += 1

    # 生成输出节点列表
    out_nodes = []
    for song_id, node in songs.items():
        bd = breakdown.get(song_id, {})
        out_nodes.append({
            "id": song_id,
            "title": node.get("name", "Unknown"),
            "genre": node.get("genre"),
            "release_year": str(node.get("release_date", ""))[:4],
            "influence": influence_score.get(song_id, 0),
            "influence_breakdown": {
                k: int(v) for k, v in bd.items()
            },
        })

    return {
        "nodes": out_nodes,
        "meta": {
            "total_songs": len(songs),
            "with_influence": sum(1 for v in influence_score.values() if v > 0),
        }
    }


def main():
    base = Path(__file__).resolve().parent
    graph_path = base / "data" / "Topic1_graph.json"
    out_path = base / "data" / "song_influence.json"

    if not graph_path.exists():
        raise FileNotFoundError(f"图数据不存在: {graph_path}")

    print(f"[INFO] 读取图数据: {graph_path}")
    graph = load_graph(graph_path)

    print("[INFO] 计算影响力...")
    result = calc_influence(graph)

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[INFO] 完成，写入: {out_path}")
    print(f"[INFO] 总歌曲/专辑: {result['meta']['total_songs']}, 有影响力记录: {result['meta']['with_influence']}")


if __name__ == "__main__":
    main()

