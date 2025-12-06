from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_preprocessing import MusicGraphProcessor
from task_analysis import Task2_GenreAnalysis
from extract_timeline_relations import extract_timeline_relations

GRAPH_PATH = ROOT / "Topic1_graph.json"
DATA_TIMELINE_PATH = ROOT / "data" / "genre_timeline_data.json"
PUBLIC_TIMELINE_PATH = ROOT / "genre-visualization" / "public" / "data" / "genre_timeline_data.json"


def serialize_work(work: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": work.get("id"),
        "title": work.get("name") or work.get("title") or "Unknown",
        "notable": bool(work.get("notable")),
        "node_type": work.get("Node Type"),
        "genre": work.get("genre"),
    }


def build_genre_timelines(task: Task2_GenreAnalysis, genres: List[str]) -> Dict[str, Any]:
    timelines: Dict[str, Any] = {}
    all_years = set()

    for genre in genres:
        analysis = task.analyze_genre_development(genre)
        timeline_entries = []
        yearly_counts: Dict[str, int] = {}

        for year, data in analysis["timeline"]:
            all_years.add(year)
            yearly_counts[str(year)] = data.get("total", 0)
            works = []
            for song in data.get("songs", []):
                works.append(serialize_work(song))
            for album in data.get("albums", []):
                works.append(serialize_work(album))

            timeline_entries.append([
                year,
                {
                    "total": data.get("total", 0),
                    "notable": data.get("notable", 0),
                    "works": works,
                },
            ])

        timelines[genre] = {
            "timeline": timeline_entries,
            "yearly_counts": yearly_counts,
        }

    return timelines, sorted(all_years)


def build_time_range(years: List[int]) -> Dict[str, Any]:
    if not years:
        raise RuntimeError("No years available to build time range")
    return {
        "min": years[0],
        "max": years[-1],
        "all_years": years,
    }


def write_payload(payload: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main() -> None:
    processor = MusicGraphProcessor(str(GRAPH_PATH))
    task = Task2_GenreAnalysis(processor)

    genres = task.get_all_genres()
    genre_timelines, all_years = build_genre_timelines(task, genres)
    time_range = build_time_range(all_years)

    payload = {
        "genres": genres,
        "time_range": time_range,
        "genre_timelines": genre_timelines,
        "relations": [],
    }

    write_payload(payload, DATA_TIMELINE_PATH)
    print(f"[INFO] wrote base timeline -> {DATA_TIMELINE_PATH.relative_to(ROOT)}")

    # 补充跨流派关系并同步到公开目录
    extract_timeline_relations(
        str(GRAPH_PATH),
        str(DATA_TIMELINE_PATH),
        str(DATA_TIMELINE_PATH),
    )

    PUBLIC_TIMELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_TIMELINE_PATH.write_text(DATA_TIMELINE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"[INFO] synced to {PUBLIC_TIMELINE_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
