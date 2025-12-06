import json
from collections import Counter, defaultdict
from pathlib import Path

path = Path('data/person_evaluations_labeled.json')
with path.open('r', encoding='utf-8') as f:
    persons = json.load(f)

counts = Counter()
max_share = defaultdict(float)
min_share = defaultdict(lambda: 1.0)

for person in persons:
    shares = person.get('genre_share') or {}
    for genre, share in shares.items():
        if not isinstance(share, (int, float)):
            continue
        if share >= 0.2:
            counts[genre] += 1
        if share > max_share[genre]:
            max_share[genre] = share
        if share < min_share[genre]:
            min_share[genre] = share

targets = ['Acoustic Folk', 'Celtic Folk', 'Sea Shanties']
for genre in targets:
    print(f"{genre}: count>=0.2 -> {counts[genre]}, max_share -> {max_share[genre]:.3f}")
