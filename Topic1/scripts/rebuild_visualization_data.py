from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Any

THRESHOLD = 0.00001
TOP_PREVIEW_COUNT = 100

ROOT = Path(__file__).resolve().parent.parent
PERSON_SOURCE = ROOT / "data" / "person_evaluations_labeled.json"
DEFAULT_VIS_PATH = ROOT / "data" / "visualization_data.json"
PUBLIC_VIS_PATH = ROOT / "genre-visualization" / "public" / "data" / "visualization_data.json"


def load_target_genres() -> List[str]:
    """Get the ordered genre list, ensuring every genre in the source data is kept."""
    existing_order: List[str] | None = None
    for candidate in (DEFAULT_VIS_PATH, PUBLIC_VIS_PATH):
        if candidate.exists():
            with candidate.open("r", encoding="utf-8") as f:
                data = json.load(f)
                genres = data.get("genres")
                if isinstance(genres, list) and genres:
                    existing_order = genres
                    break

    with PERSON_SOURCE.open("r", encoding="utf-8") as f:
        persons = json.load(f)

    genre_set = []
    seen = set()
    for person in persons:
        share_map = person.get("genre_share")
        if not isinstance(share_map, dict):
            continue
        for genre in share_map.keys():
            if genre and genre not in seen:
                seen.add(genre)
                genre_set.append(genre)

    if not genre_set:
        raise RuntimeError("Unable to determine target genres list")

    # If there is a previous order, keep it but append any newly found genres.
    if existing_order:
        ordered = list(existing_order)
        ordered.extend(g for g in genre_set if g not in existing_order)
        return ordered

    return sorted(genre_set)


def _derive_full_genre_share(person: Dict[str, Any]) -> Dict[str, float]:
    """Recalculate genre shares so all work types (songs, albums, etc.) contribute."""
    base_share = person.get("genre_share", {})
    if not isinstance(base_share, dict):
        base_share = {}

    distribution = person.get("genre_distribution", {})
    if not isinstance(distribution, dict):
        return base_share

    total = 0.0
    normalized_counts: Dict[str, float] = {}
    for genre, count in distribution.items():
        if isinstance(count, (int, float)) and count > 0:
            normalized_counts[genre] = float(count)
            total += float(count)

    if total <= 0:
        return base_share

    combined = dict(base_share)
    for genre, count in normalized_counts.items():
        combined[genre] = count / total
    return combined


def collect_artists_by_genre(genres: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Collect artists per genre with genre_share >= threshold."""
    with PERSON_SOURCE.open("r", encoding="utf-8") as f:
        persons = json.load(f)

    buckets: Dict[str, List[Dict[str, Any]]] = {genre: [] for genre in genres}

    for person in persons:
        share_map = _derive_full_genre_share(person)
        if not isinstance(share_map, dict):
            continue
        score = person.get("score", 0)
        for genre, share in share_map.items():
            if genre in buckets and isinstance(share, (int, float)) and share >= THRESHOLD:
                buckets[genre].append({
                    "person_id": person.get("person_id"),
                    "name": person.get("name"),
                    "stage_name": person.get("stage_name"),
                    "score": score,
                    "genre_share": share
                })

    # Sort each bucket by score desc, then genre_share desc, then name
    for artists in buckets.values():
        artists.sort(key=lambda a: (
            -(a.get("score") or 0),
            -(a.get("genre_share") or 0),
            (a.get("name") or "")
        ))
    return buckets


def build_visualization_payload(genres: List[str], buckets: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    payload = {
        "genres": genres,
        "genres_data": {}
    }
    for genre in genres:
        artists = buckets.get(genre, [])
        payload["genres_data"][genre] = {
            "count": len(artists),
            "display_count": min(len(artists), TOP_PREVIEW_COUNT),
            "artists": artists
        }
    return payload


def main() -> None:
    if not PERSON_SOURCE.exists():
        raise FileNotFoundError(f"Source file not found: {PERSON_SOURCE}")

    genres = load_target_genres()
    buckets = collect_artists_by_genre(genres)
    payload = build_visualization_payload(genres, buckets)

    DEFAULT_VIS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DEFAULT_VIS_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[INFO] wrote {DEFAULT_VIS_PATH.relative_to(ROOT)}")

    PUBLIC_VIS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PUBLIC_VIS_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[INFO] synced to {PUBLIC_VIS_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
