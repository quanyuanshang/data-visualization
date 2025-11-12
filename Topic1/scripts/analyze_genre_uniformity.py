from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
PERSON_FILE = ROOT / "data" / "person_evaluations_labeled.json"


@dataclass
class PersonShareStats:
    person_id: int
    name: str
    stage_name: str | None
    num_genres: int
    max_share: float
    min_share: float
    spread: float
    std_dev: float
    entropy: float
    shares: List[float]
    genres: List[str]


def load_persons() -> List[Dict[str, Any]]:
    if not PERSON_FILE.exists():
        raise FileNotFoundError(f"Source file not found: {PERSON_FILE}")
    with PERSON_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def entropy(shares: List[float]) -> float:
    return -sum(p * math.log(p, 2) for p in shares if p > 0)


def std_dev(shares: List[float]) -> float:
    if not shares:
        return 0.0
    mean = sum(shares) / len(shares)
    return math.sqrt(sum((p - mean) ** 2 for p in shares) / len(shares))


def find_uniform_persons(
    persons: List[Dict[str, Any]],
    min_genres: int,
    max_spread: float,
    max_dominant: float,
) -> List[PersonShareStats]:
    results: List[PersonShareStats] = []
    for person in persons:
        share_map: Dict[str, float] = person.get("genre_share") or {}
        active_items = [(g, s) for g, s in share_map.items() if isinstance(s, (int, float)) and s > 0]
        if len(active_items) < min_genres:
            continue
        genres, shares = zip(*active_items)
        max_share = max(shares)
        min_share = min(shares)
        spread = max_share - min_share
        if spread > max_spread:
            continue
        if max_share > max_dominant:
            continue
        stats = PersonShareStats(
            person_id=person.get("person_id"),
            name=person.get("name", ""),
            stage_name=person.get("stage_name"),
            num_genres=len(shares),
            max_share=max_share,
            min_share=min_share,
            spread=spread,
            std_dev=std_dev(list(shares)),
            entropy=entropy(list(shares)),
            shares=list(shares),
            genres=list(genres),
        )
        results.append(stats)
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect persons whose genre_share distribution is close to uniform"
    )
    parser.add_argument("--min-genres", type=int, default=3, help="Minimum number of active genres")
    parser.add_argument(
        "--max-spread",
        type=float,
        default=0.15,
        help="Maximum allowed difference between max and min share",
    )
    parser.add_argument(
        "--max-dominant",
        type=float,
        default=0.5,
        help="Maximum allowed dominant share (largest share)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="How many sample persons to list",
    )
    parser.add_argument(
        "--export-json",
        type=Path,
        default=None,
        help="Optional path to export full result list as JSON",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    persons = load_persons()
    uniform_persons = find_uniform_persons(
        persons,
        min_genres=args.min_genres,
        max_spread=args.max_spread,
        max_dominant=args.max_dominant,
    )

    uniform_persons.sort(key=lambda x: (x.spread, x.std_dev, -x.entropy))

    print(f"[INFO] total persons: {len(persons)}")
    print(f"[INFO] persons with >= {args.min_genres} genres: {sum(1 for p in persons if sum(1 for s in (p.get('genre_share') or {}).values() if s and s > 0) >= args.min_genres)}")
    print(f"[INFO] matching uniform persons: {len(uniform_persons)}")

    limit = min(args.top, len(uniform_persons))
    if limit:
        print(f"\nTop {limit} examples (spread ≤ {args.max_spread}, max share ≤ {args.max_dominant}):")
        for stats in uniform_persons[:limit]:
            name_display = stats.name
            if stats.stage_name:
                name_display += f" ({stats.stage_name})"
            shares_str = ", ".join(f"{g}:{s:.3f}" for g, s in zip(stats.genres, stats.shares))
            print(
                f"- #{stats.person_id} {name_display}: genres={stats.num_genres}, "
                f"spread={stats.spread:.3f}, std={stats.std_dev:.3f}, entropy={stats.entropy:.3f} | {shares_str}"
            )
    else:
        print("[INFO] no persons satisfied the criteria")

    if args.export_json:
        export_data = [
            {
                "person_id": stats.person_id,
                "name": stats.name,
                "stage_name": stats.stage_name,
                "num_genres": stats.num_genres,
                "max_share": stats.max_share,
                "min_share": stats.min_share,
                "spread": stats.spread,
                "std_dev": stats.std_dev,
                "entropy": stats.entropy,
                "shares": stats.shares,
                "genres": stats.genres,
            }
            for stats in uniform_persons
        ]
        args.export_json.parent.mkdir(parents=True, exist_ok=True)
        with args.export_json.open("w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        print(f"[INFO] exported {len(export_data)} records to {args.export_json}")


if __name__ == "__main__":
    main()
