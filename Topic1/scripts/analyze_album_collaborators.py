"""Analyze Album nodes to see how many distinct musicians collaborate on each album."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Any, List, Set

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_GRAPH = BASE_DIR / "data" / "Topic1_graph.json"

ROLE_EDGES = {"PerformerOf", "ComposerOf", "LyricistOf", "ProducerOf"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze albums with multiple collaborators")
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH, help="Path to Topic1_graph.json")
    parser.add_argument(
        "--min-persons",
        type=int,
        default=2,
        help="Minimum number of distinct person contributors to report (default: %(default)s)",
    )
    parser.add_argument(
        "--limit", type=int, default=30, help="Limit console output rows (default: %(default)s)"
    )
    parser.add_argument("--csv", type=Path, default=None, help="Optional CSV output path")
    return parser.parse_args()


def load_graph(graph_path: Path) -> Dict[str, Any]:
    with graph_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_album_collaborators(data: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    node_lookup = {node["id"]: node for node in data.get("nodes", [])}
    collaborations: Dict[int, Dict[str, Any]] = {}

    edges = data.get("links") or data.get("edges") or []
    for edge in edges:
        edge_type = edge.get("Edge Type")
        if edge_type not in ROLE_EDGES:
            continue
        source_id = edge.get("source")
        target_id = edge.get("target")
        source_node = node_lookup.get(source_id)
        target_node = node_lookup.get(target_id)
        if not source_node or not target_node:
            continue
        if source_node.get("Node Type") != "Person" or target_node.get("Node Type") != "Album":
            continue

        entry = collaborations.setdefault(
            target_id,
            {
                "album": target_node,
                "persons": set(),
                "roles": {},  # person_id -> set of roles
            },
        )
        entry["persons"].add(source_id)
        entry["roles"].setdefault(source_id, set()).add(edge_type)

    return collaborations


def summarize(collaborations: Dict[int, Dict[str, Any]], min_persons: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for album_id, info in collaborations.items():
        persons: Set[int] = info["persons"]
        if len(persons) < min_persons:
            continue
        album = info["album"]
        row = {
            "album_id": album_id,
            "album_name": album.get("name", f"Album {album_id}"),
            "genre": album.get("genre", "-"),
            "release_date": album.get("release_date", "-"),
            "person_count": len(persons),
            "persons": [
                {
                    "person_id": pid,
                    "name": info_for_person.get("name", f"Person {pid}"),
                    "roles": sorted(info["roles"].get(pid, [])),
                }
                for pid, info_for_person in [
                    (pid, node_lookup_cached(pid, collaborations)) for pid in sorted(persons)
                ]
            ],
        }
        rows.append(row)
    rows.sort(key=lambda r: (-r["person_count"], r["album_name"]))
    return rows


def node_lookup_cached(person_id: int, collaborations: Dict[int, Dict[str, Any]]):
    # Placeholder, to be replaced after we create global lookup
    raise RuntimeError("Should be replaced")


def print_table(rows: List[Dict[str, Any]], limit: int) -> None:
    print("=== Album Collaboration Summary ===")
    print(f"Albums meeting criteria: {len(rows)}")
    print()
    headers = ["#", "Album", "Genre", "Release", "Collaborators"]
    widths = [4, 40, 18, 10, 0]
    header_row = " | ".join(
        header.ljust(widths[i]) if widths[i] else header for i, header in enumerate(headers)
    )
    print(header_row)
    print("-" * len(header_row))

    for idx, row in enumerate(rows[:limit], start=1):
        collaborators = ", ".join(
            f"{person['name']} ({'/'.join(person['roles'])})" for person in row["persons"]
        )
        cells = [
            str(idx).ljust(widths[0]),
            row["album_name"].ljust(widths[1]),
            row["genre"].ljust(widths[2]),
            str(row["release_date"]).ljust(widths[3]),
            collaborators,
        ]
        print(" | ".join(cells))
    if len(rows) > limit:
        print(f"... {len(rows) - limit} more albums not shown")


def export_csv(rows: List[Dict[str, Any]], csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "album_id",
            "album_name",
            "genre",
            "release_date",
            "person_count",
            "person_details",
        ])
        for row in rows:
            person_details = "; ".join(
                f"{person['person_id']}:{person['name']} ({'/'.join(person['roles'])})"
                for person in row["persons"]
            )
            writer.writerow(
                [
                    row["album_id"],
                    row["album_name"],
                    row["genre"],
                    row["release_date"],
                    row["person_count"],
                    person_details,
                ]
            )
    print(f"CSV exported to {csv_path}")


def main() -> None:
    args = parse_args()
    data = load_graph(args.graph)

    global NODE_LOOKUP
    NODE_LOOKUP = {node["id"]: node for node in data.get("nodes", [])}

    collaborations = build_album_collaborators(data)

    def replace_lookup(person_id: int, _collaborations: Dict[int, Dict[str, Any]]):
        return NODE_LOOKUP.get(person_id, {})

    global node_lookup_cached
    node_lookup_cached = replace_lookup

    rows = summarize(collaborations, args.min_persons)
    if not rows:
        print("No albums meet the criteria.")
        return

    print_table(rows, args.limit)
    if args.csv:
        export_csv(rows, args.csv)


if __name__ == "__main__":
    NODE_LOOKUP: Dict[int, Dict[str, Any]] = {}
    main()
