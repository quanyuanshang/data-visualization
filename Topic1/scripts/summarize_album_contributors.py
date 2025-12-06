import json
from collections import Counter, defaultdict
from pathlib import Path

ROLE_EDGES = {"PerformerOf", "ComposerOf", "LyricistOf", "ProducerOf"}

def main():
    data_path = Path(r"d:\cs\数据可视化\Topic1\data\Topic1_graph.json")
    data = json.loads(data_path.read_text(encoding="utf-8"))
    nodes = {node["id"]: node for node in data.get("nodes", [])}
    edges = data.get("links") or data.get("edges") or []

    album_people = defaultdict(set)
    for edge in edges:
        edge_type = edge.get("Edge Type")
        if edge_type not in ROLE_EDGES:
            continue
        src = edge.get("source")
        dst = edge.get("target")
        if nodes.get(src, {}).get("Node Type") != "Person":
            continue
        if nodes.get(dst, {}).get("Node Type") != "Album":
            continue
        album_people[dst].add(src)

    counts = Counter(len(people) for people in album_people.values())
    print(f"Albums with contributor metadata: {len(album_people)}")
    for num in sorted(counts):
        print(f"{num} contributor(s): {counts[num]} album(s)")

    singles = [aid for aid, people in album_people.items() if len(people) == 1]
    print(f"\nSingle-person albums count: {len(singles)}")
    for aid in singles[:10]:
        album = nodes.get(aid, {})
        person_id = next(iter(album_people[aid]))
        person = nodes.get(person_id, {})
        print(
            f"- {album.get('name', '(Unnamed)')} "
            f"({album.get('genre', '-')}, {album.get('release_date', '-')}) "
            f"by {person.get('name', 'Unknown')} [Person {person_id}]"
        )

if __name__ == "__main__":
    main()
