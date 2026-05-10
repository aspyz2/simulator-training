import json
from collections import Counter

with open('questions.json', encoding='utf-8') as f:
    qs = json.load(f)

dup_questions = []
for q in qs:
    opts = q.get('options', {})
    if len(opts) < 2:
        continue
    vals = list(opts.values())
    # All options identical
    if len(set(vals)) == 1:
        dup_questions.append(q)

print(f"Questoes com todas as opcoes identicas: {len(dup_questions)}")
for q in dup_questions:
    vals = list(q['options'].values())
    print(f"  Q{q['id']:4d} | opts={list(q['options'].keys())} val='{vals[0][:50]}' ans={q['answers']}")
    print(f"         | {q['question'][:90]}")
