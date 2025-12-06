import json
from pathlib import Path

data = json.loads(Path('genre-visualization/public/data/genre_timeline_data.json').read_text(encoding='utf-8'))
relations = data.get('relations', [])
cf = [r for r in relations if 'Celtic Folk' in (r['source_genre'], r['target_genre'])]
print('Celtic Folk relations:', len(cf))
for r in cf[:10]:
    print(r)
