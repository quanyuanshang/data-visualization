from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Set, Any

# 项目根目录，供后续读取数据和输出结果使用
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from data_preprocessing import MusicGraphProcessor

GRAPH_PATH = ROOT / "data" / "Topic1_graph.json"
PERSONS_PATH = ROOT / "data" / "person_evaluations_labeled.json"
OUTPUT_DATA_PATH = ROOT / "data" / "person_tracks.json"
PUBLIC_DIR = ROOT / "genre-visualization" / "public" / "data" / "person_tracks"

ROLES = {"PerformerOf", "ComposerOf", "LyricistOf", "ProducerOf"}
TYPE_TO_KEY = {
    "CoverOf": "cover",
    "DirectlySamples": "sample",
    "InterpolatesFrom": "reference",
    "LyricalReferenceTo": "reference",
    "InStyleOf": "style",
}
INFLUENCE_WEIGHTS = {
    # 被翻唱代表强影响力
    "cover": 5,
    # 直接采样次之
    "sample": 4,
    # 引用（Interpolates/LyricalReference）给较低权重
    "reference": 3,
    # 风格模仿权重最低
    "style": 2,
}


def load_persons() -> List[Dict[str, Any]]:
    """读取音乐人评价数据，供后续遍历."""
    if not PERSONS_PATH.exists():
        raise FileNotFoundError(f"Person file not found: {PERSONS_PATH}")
    with PERSONS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_primary_artist(processor: MusicGraphProcessor, song_id: int) -> Tuple[int | None, str | None]:
    """推断某首歌的“主要”音乐人，用于显示外部节点信息."""
    candidates = []
    for edge_type, source_id in processor.get_edges_to(song_id):
        if edge_type in ROLES:
            node = processor.get_node(source_id)
            if not node or node.get("Node Type") != "Person":
                continue
            stage = node.get("stage_name")
            name = node.get("name")
            display_name = f"{name} ({stage})" if stage else name
            candidates.append((source_id, display_name))
            if edge_type == "PerformerOf":
                # Prefer performer
                return source_id, display_name
    return candidates[0] if candidates else (None, None)


def build_person_tracks(processor: MusicGraphProcessor, person: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    为单个音乐人生成包含“自有单曲 + 关联外部曲目 + 关系边”的网络结构.
    """
    person_id = person["person_id"]
    works = processor.get_person_works(person_id)
    song_nodes = {}
    for role in ROLES:
        for node in works.get(role, []):
            if node.get("Node Type") == "Song":
                song_nodes[node["id"]] = node

    if not song_nodes:
        return None

    nodes: Dict[str, Dict[str, Any]] = {}
    external_nodes: Dict[str, Dict[str, Any]] = {}
    links_set: Set[Tuple[str, str, str]] = set()

    for song_id, node in song_nodes.items():
        node_key = f"song:{song_id}"
        # 记录影响力的四种来源
        influence_counts = {"cover": 0, "sample": 0, "reference": 0, "style": 0}
        release_year = processor.extract_date(node)
        artist_entry = {
            "id": node_key,
            "song_id": song_id,
            "title": node.get("name"),
            "genre": node.get("genre"),
            "notable": bool(node.get("notable")),
            "release_year": release_year,
            "single": bool(node.get("single")),
            "own": True,
            "artist_id": person_id,
            "artist_name": format_display_name(person.get("name"), person.get("stage_name")),
            "influence": 0,
            "influence_breakdown": influence_counts.copy(),
            "relation_types": []
        }

        # 统计所有指向该歌曲的边（被谁翻唱/采样/引用/模仿）
        for edge_type, source_id in processor.get_edges_to(song_id):
            key = TYPE_TO_KEY.get(edge_type)
            if not key:
                continue
            source_node = processor.get_node(source_id)
            if not source_node or source_node.get("Node Type") != "Song":
                continue
            influence_counts[key] += 1

            source_key = f"song:{source_id}"
            if source_key not in nodes and source_key not in external_nodes:
                owner_id, owner_name = build_primary_artist(processor, source_id)
                external_nodes[source_key] = {
                    "id": source_key,
                    "song_id": source_id,
                    "title": source_node.get("name"),
                    "genre": source_node.get("genre"),
                    "notable": bool(source_node.get("notable")),
                    "release_year": processor.extract_date(source_node),
                    "single": bool(source_node.get("single")),
                    "own": owner_id == person_id,
                    "artist_id": owner_id,
                    "artist_name": owner_name,
                    "influence": 0,
                    "influence_breakdown": {"cover": 0, "sample": 0, "reference": 0, "style": 0},
                    "relation_types": set()
                }
            if source_key in external_nodes:
                external_nodes[source_key]["relation_types"].add(edge_type)

            # 记录一条“外部作品 → 当前音乐人作品”的边
            links_set.add((source_key, node_key, edge_type))

        artist_entry["influence_breakdown"] = influence_counts
        artist_entry["influence"] = sum(influence_counts[k] * INFLUENCE_WEIGHTS[k] for k in influence_counts)
        artist_entry["relation_types"] = []
        nodes[node_key] = artist_entry

    # finalize external nodes
    for ext in external_nodes.values():
        ext["relation_types"] = sorted(ext["relation_types"])
        if ext["artist_name"] is None:
            ext["artist_name"] = "Unknown Artist"
        if ext["artist_id"] is None:
            ext["artist_id"] = -1

    all_nodes = list(nodes.values()) + list(external_nodes.values())
    links = [
        {"source": source, "target": target, "type": edge_type}
        for source, target, edge_type in links_set
    ]

    return {
        "person_id": person_id,
        "name": person.get("name"),
        "stage_name": person.get("stage_name"),
        "nodes": all_nodes,
        "links": links
    }


def format_display_name(name: str | None, stage: str | None) -> str:
    """拼接姓名 + 艺名."""
    if not name:
        return stage or "Unknown Artist"
    return f"{name} ({stage})" if stage else name


def main() -> None:
    """批量生成每位音乐人的单曲网络文件并输出到前端可读取的位置."""
    persons = load_persons()
    processor = MusicGraphProcessor(str(GRAPH_PATH))

    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    aggregate_data = {}
    for person in persons:
        result = build_person_tracks(processor, person)
        if not result or not result.get("nodes"):
            continue
        person_id = result["person_id"]
        aggregate_data[person_id] = result
        output_file = PUBLIC_DIR / f"{person_id}.json"
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"[INFO] wrote person_tracks/{person_id}.json (nodes={len(result['nodes'])}, links={len(result['links'])})")

    with OUTPUT_DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(aggregate_data, f, ensure_ascii=False, indent=2)
    print(f"[INFO] aggregate data saved to {OUTPUT_DATA_PATH.relative_to(ROOT)} (persons={len(aggregate_data)})")


if __name__ == "__main__":
    main()
