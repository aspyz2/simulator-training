import json

with open('questions.json', encoding='utf-8') as f:
    qs = json.load(f)

with_img = [q for q in qs if q.get('image')]
with_exhibit = [q for q in qs if q.get('image') and q.get('has_exhibit')]
without_exhibit = [q for q in qs if q.get('image') and not q.get('has_exhibit')]

print(f"Total com imagem:     {len(with_img)}")
print(f"  has_exhibit=True:   {len(with_exhibit)}")
print(f"  has_exhibit=False:  {len(without_exhibit)}  <- provavelmente erradas")
print()
print("Amostra sem exhibit (primeiras 20):")
for q in without_exhibit[:20]:
    print(f"  Q{q['id']:4d} | {q['question'][:85]}")
