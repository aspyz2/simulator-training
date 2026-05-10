"""
fix_images.py — Remove imagens de questões que não referenciam exhibit.
Questões do tipo drag_drop e lab também perdem a imagem (frontend já ignora).
"""
import json, re

EXHIBIT_PATTERNS = re.compile(
    r'\b(exhibit|refer to|topology shown|diagram|figure|shown below|the following)\b',
    re.IGNORECASE
)

with open('questions.json', encoding='utf-8') as f:
    qs = json.load(f)

removed = 0
kept = 0
for q in qs:
    if not q.get('image'):
        continue
    text = q.get('question', '')
    has_exhibit = bool(EXHIBIT_PATTERNS.search(text))
    # drag_drop and lab don't need images (frontend hides them anyway)
    is_interactive = q.get('type') in ('drag_drop', 'lab')
    if not has_exhibit or is_interactive:
        q['image'] = None
        q['has_exhibit'] = False
        removed += 1
    else:
        kept += 1

with open('questions.json', 'w', encoding='utf-8') as f:
    json.dump(qs, f, ensure_ascii=False, indent=2)

print(f"Imagens removidas:  {removed}")
print(f"Imagens mantidas:   {kept}")
