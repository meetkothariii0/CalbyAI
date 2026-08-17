import json
from collections import Counter
from pathlib import Path

P = Path(__file__).resolve().parents[1] / 'data' / 'graph' / 'knowledge_graph.json'
if not P.exists():
    print('MISSING', P)
    raise SystemExit(1)

g = json.loads(P.read_text(encoding='utf8'))
nodes = g.get('nodes', [])
edges = g.get('edges', [])

cnt = Counter(n.get('type') for n in nodes)
ecnt = Counter(e.get('type') for e in edges)

print('NODE_COUNTS')
for k,v in cnt.items():
    print(f'{k}: {v}')
print('\nEDGE_COUNTS')
for k,v in ecnt.items():
    print(f'{k}: {v}')

print('\nEXAMPLES')
seen = set()
for n in nodes:
    t = n.get('type')
    if t in seen:
        continue
    print('\n---', t, '---')
    print(json.dumps(n, ensure_ascii=False, indent=2))
    seen.add(t)
    if len(seen) >= 5:
        break

print('\nRAW_JSON_IS_INDENTED:', True)
