"""
fix_dup_options.py â€” Re-parses only the 22 questions with identical options
from the original PDF, applying the fixed multiline parse_options logic.
"""
import json, re, sys, os
sys.path.insert(0, os.path.dirname(__file__))

import pdfplumber
from parser import clean_text, parse_options, _parse_options_multiline

PDF_PATH = r'C:\Users\eavsec\Downloads\200-301 V3.pdf'
TARGET_IDS = {40, 138, 193, 199, 222, 233, 249, 260, 268, 287, 291,
              409, 417, 418, 419, 430, 495, 506, 510, 518, 609, 617}

EXHIBIT_RE = re.compile(
    r'\b(exhibit|refer to|topology shown|diagram|figure|shown below|the following)\b',
    re.IGNORECASE,
)

with open('questions.json', encoding='utf-8') as f:
    questions = json.load(f)
q_by_id = {q['id']: q for q in questions}

# Rebuild page text + q_start_page from PDF
page_texts = []
q_start_page = {}
with pdfplumber.open(PDF_PATH) as pdf:
    for i, page in enumerate(pdf.pages):
        t = page.extract_text() or ''
        page_texts.append(t)
        for m in re.finditer(r'QUESTION NO:\s*(\d+)', t):
            q_start_page[int(m.group(1))] = i

full_text = clean_text('\n'.join(page_texts))
parts = re.split(r'QUESTION NO:\s*(\d+)', full_text)

fixed = 0
for i in range(1, len(parts) - 1, 2):
    try:
        q_id = int(parts[i].strip())
    except ValueError:
        continue
    if q_id not in TARGET_IDS:
        continue

    block = parts[i + 1] if i + 1 < len(parts) else ''

    answer_match = re.search(r'^Answer:\s*([A-E][, A-E]*)\s*$', block, re.MULTILINE)
    if not answer_match:
        continue
    correct_answers = sorted(set(a.strip() for a in re.split(r'[,\s]+', answer_match.group(1)) if a.strip()))

    opts = parse_options(block)
    if not opts:
        print(f'  Q{q_id}: no options found â€” skipping')
        continue

    vals = list(opts.values())
    if len(set(vals)) == 1 and len(vals) > 1:
        print(f'  Q{q_id}: still all identical after reparse: "{vals[0][:60]}"')
        continue

    if q_id in q_by_id:
        q_by_id[q_id]['options'] = opts
        q_by_id[q_id]['answers'] = correct_answers
        q_by_id[q_id]['multiple'] = len(correct_answers) > 1
        distinct = len(set(vals))
        print(f'  Q{q_id}: OK  {len(opts)} opts, {distinct} distinct  ans={correct_answers}')
        fixed += 1

with open('questions.json', 'w', encoding='utf-8') as f:
    json.dump(questions, f, ensure_ascii=False, indent=2)

print(f'\nDone. Fixed={fixed}/{len(TARGET_IDS)}')
