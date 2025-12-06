from __future__ import annotations

"""Identify artists with very small catalogs and low song influence."""

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_preprocessing import MusicGraphProcessor

INFLUENCE_WEIGHTS: Dict[str, int] = {
    "CoverOf": 5,
    "DirectlySamples": 4,
    "InterpolatesFrom": 3,
    "LyricalReferenceTo": 3,
    "InStyleOf": 2,
}
ROLE_TYPES = {"PerformerOf", "ComposerOf", "LyricistOf", "ProducerOf"}
WORK_TYPES = {"Song", "Album"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Count artists that only have a couple of works (Song/Album) "
            "and whose catalog gathers almost no influence."
        )
    )
    default_graph = PROJECT_ROOT / "data" / "Topic1_graph.json"
    parser.add_argument(
        "--graph",
        type=Path,
        default=default_graph,
        help=f"Path to Topic1_graph.json (default: {default_graph})",
    )
    parser.add_argument(
        "--max-works",
        type=int,
        default=2,
        help="Maximum number of unique works for an artist to be considered low-output.",
    )
    parser.add_argument(
        "--max-influence",
        type=float,
        default=5.0,
        help=(
            "Maximum summed influence weight across all of the artist's works. "
            "Weights follow Cover=5, Sample=4, Reference=3, Style=2."
        ),
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=10,
        help="How many example artists to print.",
    )
    return parser.parse_args()


def compute_work_influence(processor: MusicGraphProcessor) -> Dict[int, float]:
    influence = defaultdict(float)
    for edge_type, weight in INFLUENCE_WEIGHTS.items():
        for source_id, target_id in processor.get_edges_by_type(edge_type):
            target_node = processor.get_node(target_id)
            if not target_node or target_node.get("Node Type") not in WORK_TYPES:
                continue
            influence[target_id] += weight
    return influence


def collect_artist_stats(
    processor: MusicGraphProcessor,
    work_influence: Dict[int, float],
) -> List[Dict[str, object]]:
    stats: List[Dict[str, object]] = []
    for person in processor.get_nodes_by_type("Person"):
        works = processor.get_person_works(person["id"])
        unique_work_ids = set()
        for nodes in works.values():
            for node in nodes:
                if node.get("Node Type") in WORK_TYPES:
                    unique_work_ids.add(node["id"])
        if not unique_work_ids:
            continue
        total_influence = sum(work_influence.get(work_id, 0.0) for work_id in unique_work_ids)
        stats.append(
            {
                "person_id": person["id"],
                "name": person.get("name"),
                "stage_name": person.get("stage_name"),
                "work_count": len(unique_work_ids),
                "influence": total_influence,
            }
        )
    return stats


def format_artist_name(entry: Dict[str, object]) -> str:
    name = entry.get("name") or "Unknown"
    stage = entry.get("stage_name")
    if stage and stage != name:
        return f"{name} ({stage})"
    return name  # type: ignore[return-value]


def main() -> None:
    args = parse_args()
    if not args.graph.exists():
        raise FileNotFoundError(f"Graph file not found: {args.graph}")

    processor = MusicGraphProcessor(str(args.graph))
    work_influence = compute_work_influence(processor)
    stats = collect_artist_stats(processor, work_influence)

    filtered = [
        entry
        for entry in stats
        if 1 <= entry["work_count"] <= args.max_works and entry["influence"] <= args.max_influence
    ]

    filtered.sort(key=lambda item: (item["work_count"], item["influence"]))

    print("=== Low-output, low-influence artists ===")
    print(f"Total artists considered: {len(stats)}")
    print(
        f"Artists with 1-{args.max_works} works and total influence ≤ {args.max_influence}: {len(filtered)}"
    )

    sample = filtered[: args.sample]
    if not sample:
        print("No artists matched the criteria.")
        return

    print(f"\nTop {len(sample)} examples:")
    for entry in sample:
        display = format_artist_name(entry)
        print(
            f"- {display} (id={entry['person_id']}) ｜ Works: {entry['work_count']} ｜ Influence: {entry['influence']:.1f}"
        )


if __name__ == "__main__":
    main()
