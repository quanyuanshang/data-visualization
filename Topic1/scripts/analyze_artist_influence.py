"""Inspect song-level influence signals for a given artist.

Usage example:
    python scripts/analyze_artist_influence.py --artist "Ashen Valor"
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_preprocessing import MusicGraphProcessor

INFLUENCE_EDGE_TYPES = [
    "CoverOf",
    "DirectlySamples",
    "InterpolatesFrom",
    "LyricalReferenceTo",
    "InStyleOf",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize influence edges for all songs by a specific artist"
    )
    parser.add_argument(
        "--graph",
        type=Path,
        default=Path("Topic1_graph.json"),
        help="Path to Topic1_graph.json",
    )
    parser.add_argument(
        "--artist",
        required=True,
        help="Artist name or stage name (case-insensitive substring match)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of songs in the detailed output",
    )
    parser.add_argument(
        "--sort-by",
        choices=["name", "influence"],
        default="influence",
        help="Sort songs alphabetically or by total influence count",
    )
    return parser.parse_args()


def find_matching_persons(processor: MusicGraphProcessor, query: str) -> List[dict]:
    query = query.lower().strip()
    matches: List[dict] = []
    for node in processor.get_nodes_by_type("Person"):
        name = (node.get("name") or "").lower()
        stage = (node.get("stage_name") or "").lower()
        if query in name or (stage and query in stage):
            matches.append(node)
    return matches


def summarize_song_influence(processor: MusicGraphProcessor, song: dict) -> Dict[str, List[dict]]:
    stats: Dict[str, List[dict]] = {etype: [] for etype in INFLUENCE_EDGE_TYPES}
    song_id = song["id"]
    for edge_type, source_id in processor.get_edges_to(song_id):
        if edge_type not in INFLUENCE_EDGE_TYPES:
            continue
        source_node = processor.get_node(source_id) or {"name": "(unknown)", "Node Type": "?"}
        stats[edge_type].append(
            {
                "id": source_id,
                "name": source_node.get("name") or source_node.get("title") or "(unknown)",
                "node_type": source_node.get("Node Type"),
                "notable": source_node.get("notable", False),
                "year": source_node.get("release_date") or source_node.get("notoriety_date"),
            }
        )
    return stats


def print_song_report(song: dict, stats: Dict[str, List[dict]]) -> None:
    total = sum(len(items) for items in stats.values())
    print(f"- {song.get('name', 'Unknown Song')} (id={song['id']}, genre={song.get('genre')}, notable={song.get('notable')})")
    print(f"  Total influence edges: {total}")
    for edge_type in INFLUENCE_EDGE_TYPES:
        items = stats[edge_type]
        if not items:
            continue
        notable_hits = sum(1 for item in items if item["notable"])
        print(f"    {edge_type}: {len(items)} references ({notable_hits} notable)")
    for edge_type in INFLUENCE_EDGE_TYPES:
        items = stats[edge_type]
        if not items:
            continue
        print(f"      Details for {edge_type}:")
        for item in items:
            flag = "*" if item["notable"] else "-"
            year = item["year"] or "?"
            print(f"        {flag} {item['name']} (id={item['id']}, type={item['node_type']}, year={year})")


def main() -> None:
    args = parse_args()

    processor = MusicGraphProcessor(str(args.graph))
    matches = find_matching_persons(processor, args.artist)
    if not matches:
        raise SystemExit(f"No artist found matching '{args.artist}'")

    print(f"Found {len(matches)} artist(s) matching '{args.artist}':")
    for node in matches:
        print(f"  - {node.get('name')} (stage: {node.get('stage_name')}, id={node['id']})")

    target = matches[0]
    if len(matches) > 1:
        print("\nMultiple matches found; reporting only the first. Specify a more precise name if needed.\n")

    works_by_role = processor.get_person_works(target["id"])
    all_works = []
    for nodes in works_by_role.values():
        all_works.extend(nodes)
    songs = {w["id"]: w for w in all_works if w.get("Node Type") == "Song"}

    print(f"Artist '{target.get('name')}' has {len(songs)} unique songs with recorded roles.")

    song_stats = []
    for song in songs.values():
        stats = summarize_song_influence(processor, song)
        total = sum(len(items) for items in stats.values())
        song_stats.append((total, song, stats))

    if args.sort_by == "influence":
        song_stats.sort(key=lambda item: item[0], reverse=True)
    else:
        song_stats.sort(key=lambda item: (item[1].get("name") or "").lower())

    if args.limit is not None:
        song_stats = song_stats[: args.limit]

    print("\nSong influence breakdown:")
    for total, song, stats in song_stats:
        print_song_report(song, stats)
        print()

    summed = defaultdict(int)
    for total, _song, stats in song_stats:
        for edge_type, items in stats.items():
            summed[edge_type] += len(items)
    print("Overall influence counts in shown subset:")
    for edge_type in INFLUENCE_EDGE_TYPES:
        print(f"  {edge_type}: {summed[edge_type]}")


if __name__ == "__main__":
    main()
