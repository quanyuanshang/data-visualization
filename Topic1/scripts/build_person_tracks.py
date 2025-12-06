from __future__ import annotations

import json
import sys
from collections import defaultdict
import csv
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
PREDICTIONS_PATH = ROOT / "output" / "artist_success_predictions.csv"

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


def load_predicted_scores() -> Dict[int, float]:
    """Load AI-predicted scores (if available) for quick lookup."""
    scores: Dict[int, float] = {}
    if not PREDICTIONS_PATH.exists():
        return scores
    with PREDICTIONS_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                pid = int(row.get("person_id"))
            except (TypeError, ValueError):
                continue
            try:
                score = float(row.get("predicted_score"))
            except (TypeError, ValueError):
                score = None
            if score is not None:
                scores[pid] = score
    return scores


def build_primary_artist(
    processor: MusicGraphProcessor,
    work_id: int,
    predicted_scores: Dict[int, float],
) -> Tuple[int | None, str | None]:
    """推断某首作品（歌曲/专辑）的“主要”音乐人."""
    person_candidates: List[Tuple[int, str]] = []
    group_candidates: List[Tuple[int, str]] = []

    for edge_type, source_id in processor.get_edges_to(work_id):
        if edge_type not in ROLES:
            continue

        node = processor.get_node(source_id)
        if not node:
            continue

        node_type = node.get("Node Type")
        if node_type == "Person":
            display_name = format_display_name(node.get("name"), node.get("stage_name"))
            person_candidates.append((source_id, display_name))
            if edge_type == "PerformerOf":
                # Prefer performer
                return source_id, display_name
            continue

        # 允许乐队/其他实体作为 owner
        display_name = node.get("name") or node_type or "Unknown Artist"
        if node_type == "MusicalGroup":
            member_names: List[str] = []
            for member_edge, member_id in processor.get_edges_to(source_id):
                if member_edge != "MemberOf":
                    continue
                member_node = processor.get_node(member_id)
                if member_node and member_node.get("Node Type") == "Person":
                    member_display = format_display_name(
                        member_node.get("name"),
                        member_node.get("stage_name")
                    )
                    score = predicted_scores.get(member_id)
                    if score is not None:
                        member_display = f"{member_display}｜预测 {score:.2f}"
                    member_names.append(member_display)
            if member_names:
                preview = "、".join(member_names[:2])
                suffix = "…" if len(member_names) > 2 else ""
                display_name = f"{display_name}（成员：{preview}{suffix}）"

        group_candidates.append((source_id, display_name))
        if edge_type == "PerformerOf":
            return source_id, display_name

    if person_candidates:
        return person_candidates[0]
    if group_candidates:
        return group_candidates[0]
    return None, None


def gather_collaborators(
    processor: MusicGraphProcessor,
    work_id: int,
    exclude_person: int | None,
    predicted_scores: Dict[int, float],
) -> List[Dict[str, Any]]:
    roles_map: Dict[int, set] = defaultdict(set)
    for edge_type, source_id in processor.get_edges_to(work_id):
        if edge_type in ROLES and (exclude_person is None or source_id != exclude_person):
            roles_map[source_id].add(edge_type)

    collaborators: List[Dict[str, Any]] = []
    for pid, roles in roles_map.items():
        person_node = processor.get_node(pid)
        if not person_node or person_node.get("Node Type") != "Person":
            continue
        collaborators.append({
            "person_id": pid,
            "name": person_node.get("name"),
            "stage_name": person_node.get("stage_name"),
            "roles": sorted(roles),
            "predicted_score": predicted_scores.get(pid)
        })

    collaborators.sort(key=lambda item: item.get("predicted_score") or 0.0, reverse=True)
    return collaborators


def build_person_tracks(
    processor: MusicGraphProcessor,
    person: Dict[str, Any],
    predicted_scores: Dict[int, float]
) -> Dict[str, Any] | None:
    """为单个音乐人生成包含歌曲/专辑及其引用关系的网络结构."""
    person_id = person["person_id"]
    works = processor.get_person_works(person_id)
    work_nodes: Dict[Tuple[str, int], Dict[str, Any]] = {}
    for role in ROLES:
        for node in works.get(role, []):
            node_type = node.get("Node Type")
            if node_type in {"Song", "Album"}:
                work_nodes[(node_type, node["id"])] = node

    if not work_nodes:
        return {
            "person_id": person_id,
            "name": person.get("name"),
            "stage_name": person.get("stage_name"),
            "nodes": [],
            "links": []
        }

    nodes: Dict[str, Dict[str, Any]] = {}
    external_nodes: Dict[str, Dict[str, Any]] = {}
    links_set: Set[Tuple[str, str, str]] = set()

    for (node_type, work_id), node in work_nodes.items():
        node_prefix = node_type.lower()
        node_key = f"{node_prefix}:{work_id}"
        influence_counts = {"cover": 0, "sample": 0, "reference": 0, "style": 0}
        release_year = processor.extract_date(node)
        artist_entry = {
            "id": node_key,
            "work_type": node_type,
            "work_id": work_id,
            "title": node.get("name"),
            "genre": node.get("genre"),
            "notable": bool(node.get("notable")),
            "release_year": release_year,
            "single": bool(node.get("single")) if node_type == "Song" else False,
            "own": True,
            "artist_id": person_id,
            "artist_name": format_display_name(person.get("name"), person.get("stage_name")),
            "influence": 0,
            "influence_breakdown": influence_counts.copy(),
            "relation_types": [],
            "collaborators": gather_collaborators(
                processor,
                work_id,
                exclude_person=person_id,
                predicted_scores=predicted_scores
            )
        }

        # 统计所有指向该作品（歌/专辑）的边
        for edge_type, source_id in processor.get_edges_to(work_id):
            key = TYPE_TO_KEY.get(edge_type)
            if not key:
                continue
            source_node = processor.get_node(source_id)
            if not source_node or source_node.get("Node Type") not in {"Song", "Album"}:
                continue
            influence_counts[key] += 1

            source_prefix = source_node.get("Node Type").lower()
            source_key = f"{source_prefix}:{source_id}"
            if source_key not in nodes and source_key not in external_nodes:
                owner_id, owner_name = build_primary_artist(
                    processor,
                    source_id,
                    predicted_scores
                )
                external_nodes[source_key] = {
                    "id": source_key,
                    "work_type": source_node.get("Node Type"),
                    "work_id": source_id,
                    "title": source_node.get("name"),
                    "genre": source_node.get("genre"),
                    "notable": bool(source_node.get("notable")),
                    "release_year": processor.extract_date(source_node),
                    "single": bool(source_node.get("single")) if source_node.get("Node Type") == "Song" else False,
                    "own": owner_id == person_id,
                    "artist_id": owner_id,
                    "artist_name": owner_name,
                    "influence": 0,
                    "influence_breakdown": {"cover": 0, "sample": 0, "reference": 0, "style": 0},
                    "relation_types": set(),
                    "collaborators": gather_collaborators(
                        processor,
                        source_id,
                        exclude_person=None,
                        predicted_scores=predicted_scores
                    )
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
    predicted_scores = load_predicted_scores()
    for person in persons:
        result = build_person_tracks(processor, person, predicted_scores)
        if not result:
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
