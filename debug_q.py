import json, sys

qid = int(sys.argv[1]) if len(sys.argv) > 1 else 40

with open('questions.json', encoding='utf-8') as f:
    qs = json.load(f)

q = next((q for q in qs if q['id'] == qid), None)
if not q:
    print(f'Q{qid} not found')
else:
    print(f"Q{q['id']} [{q['type']}]")
    print(f"Question: {q['question']}")
    print(f"Options:")
    for k, v in q['options'].items():
        print(f"  {k}: {v}")
    print(f"Answers: {q['answers']}")
    print(f"Explanation: {q['explanation'][:200]}")
