import json
import re

GRAPH = 'c:/Users/Meet/Desktop/CalbyAI/college-knowledge-system/data/graph/knowledge_graph.json'
TEXT = 'placements at RVCE'

g = json.load(open(GRAPH, encoding='utf8'))
lower = TEXT.lower()
norm_text = ''.join(ch for ch in TEXT if ch.isalnum()).lower()

alias_map = {}
by_college = {}
for node in g.get('nodes', []):
    if node.get('type') != 'College':
        continue
    name = node.get('name')
    if not name:
        continue
    aliases = set([name] + (node.get('aliases') or []))
    short = ''.join(ch for ch in name if ch.isalnum()).lower()
    aliases.add(short)
    initials = ''.join([p[0] for p in re.split(r"\W+", name) if p])
    # avoid single-letter initials
    if initials and len(initials) > 1:
        aliases.add(initials.lower())
    words = [p for p in re.split(r"\W+", name) if p]
    for k in range(1, min(4, len(words) + 1)):
        aliases.add(''.join(words[:k]).lower())

    by_college[name] = set()
    for a in aliases:
        if not a:
            continue
        alias_map.setdefault(a, set()).add(name)
        by_college[name].add(a)

print('Query lower:', lower)
print('Query norm_text:', norm_text)
print('\nMatched alias keys:')
matched_keys = []
for a, names in alias_map.items():
    if len(a) <= 1:
        continue
    matched = False
    if re.search(r"\b" + re.escape(a) + r"\b", lower):
        matched = True
    elif len(a) >= 2 and a in norm_text:
        matched = True
    if matched:
        matched_keys.append((a, names))
        print(f"  {a} -> {sorted(names)[:5]}")

print('\nColleges matched by alias keys:')
matched_colleges = set()
for a, names in matched_keys:
    matched_colleges.update(names)
for c in sorted(matched_colleges):
    # show which alias keys for this college matched
    keys = [a for a in by_college.get(c, []) if a in lower or a in norm_text]
    print(' ', c, 'matched_keys:', keys)

print('\nTotal matched colleges:', len(matched_colleges))
