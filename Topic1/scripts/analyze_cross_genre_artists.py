"""Analyze multi-genre artists ("rain droplets on every crop" / 雨露均沾).

This script scans the visualization_data.json file, counts how many distinct genres each
artist participates in, and reports those who cover the most genres. Optionally it can
export the results to CSV for further analysis.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Set, List, Any

DEFAULT_DATA_PATH = Path(__file__).resolve().parents[1] / "genre-visualization" / "public" / "data" / "visualization_data.json"

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze cross-genre artists")
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help="Path to visualization_data.json (default: %(default)s)",
    )
    parser.add_argument(
        "--min-genres",
        type=int,
        default=None,
        help="Minimum distinct genres required to be reported. Default: artists with the maximum genre coverage.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of rows to display in the console table (default: %(default)s)",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Optional CSV output path to dump the full results.",
    )
    return parser.parse_args()

def load_artist_genres(data_path: Path) -> Dict[int, Dict[str, Any]]:
    with data_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    artist_map: Dict[int, Dict[str, Any]] = {}
    genre_sections: Dict[str, Dict[str, Any]] = data.get("genres_data", {})

    for genre, info in genre_sections.items():
        for artist in info.get("artists", []):
            pid = int(artist["person_id"])
            entry = artist_map.setdefault(
                pid,
                {
                    "name": artist.get("name") or "Unknown",
                    "stage_name": artist.get("stage_name"),
                    "genres": set(),
                },
            )
            entry["genres"].add(genre)

    return artist_map

def summarize(artist_map: Dict[int, Dict[str, Any]], min_genres: int | None) -> List[Dict[str, Any]]:
    # Determine coverage counts
    for info in artist_map.values():
        info["genre_count"] = len(info["genres"])

    max_count = max((info["genre_count"] for info in artist_map.values()), default=0)

    if min_genres is None:
        threshold = max_count
    else:
        threshold = min_genres

    selected = [
        {
            "person_id": pid,
            "name": info["name"],
            "stage_name": info.get("stage_name"),
            "genre_count": info["genre_count"],
            "genres": sorted(info["genres"]),
        }
        for pid, info in artist_map.items()
        if info["genre_count"] >= threshold
    ]

    selected.sort(key=lambda row: (-row["genre_count"], row["name"]))

    summary = {
        "total_artists": len(artist_map),
        "max_genres": max_count,
        "threshold": threshold,
        "selected_count": len(selected),
    }
    return selected, summary

def print_table(rows: List[Dict[str, Any]], summary: Dict[str, Any], limit: int) -> None:
    print("=== Cross-Genre Artist Summary ===")
    print(
        f"Total artists: {summary['total_artists']} | "
        f"Max genres covered: {summary['max_genres']} | "
        f"Threshold: {summary['threshold']} | "
        f"Artists meeting threshold: {summary['selected_count']}"
    )
    print()

    headers = ["Rank", "Person ID", "Artist", "Stage Name", "#Genres", "Genres"]
    col_widths = [6, 10, 30, 20, 10, 0]
    header_row = " | ".join(
        header.ljust(col_widths[idx]) if col_widths[idx] else header
        for idx, header in enumerate(headers)
    )
    print(header_row)
    print("-" * len(header_row))

    for idx, row in enumerate(rows[:limit], start=1):
        genres_str = ", ".join(row["genres"])
        cells = [
            str(idx).ljust(col_widths[0]),
            str(row["person_id"]).ljust(col_widths[1]),
            row["name"].ljust(col_widths[2]),
            (row["stage_name"] or "-").ljust(col_widths[3]),
            str(row["genre_count"]).ljust(col_widths[4]),
            genres_str,
        ]
        print(" | ".join(cells))

    if len(rows) > limit:
        print(f"... ({len(rows) - limit} more rows not shown)")


def export_csv(rows: List[Dict[str, Any]], csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["person_id", "name", "stage_name", "genre_count", "genres"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "person_id": row["person_id"],
                    "name": row["name"],
                    "stage_name": row["stage_name"] or "",
                    "genre_count": row["genre_count"],
                    "genres": ", ".join(row["genres"]),
                }
            )
    print(f"CSV exported to: {csv_path}")

def main() -> None:
    args = parse_args()
    artist_map = load_artist_genres(args.data)
    rows, summary = summarize(artist_map, args.min_genres)

    if not rows:
        print("No artists meet the specified criteria.")
        return

    print_table(rows, summary, args.limit)

    if args.csv:
        export_csv(rows, args.csv)

if __name__ == "__main__":
    main()
