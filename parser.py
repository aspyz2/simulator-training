import re
import json
import os
import pdfplumber

IMAGES_DIR = os.path.join(os.path.dirname(__file__), 'static', 'images')
QUESTIONS_FILE = os.path.join(os.path.dirname(__file__), 'questions.json')

NOISE_PATTERNS = [
    r'"Everything is under control"[^\n]*',
    r'www\.pass4sure\.com[^\n]*',
    r'^Cisco 200-301 Exam\s*$',
    r'^Topic \d+.*$',
    r'^Cisco Certified Network Associate\s*$',
    r'^Version:.*$',
    r'^Cisco 200-301 Questions & Answers\s*$',
    r'Reference:\s*https?://\S+',
]


def clean_text(text):
    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, '', text, flags=re.MULTILINE)
    text = text.replace('\ufffd', "'").replace('\u2019', "'").replace('\u2018', "'")
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_page_image(page, q_num, img_index=0):
    """Extract image from a PDF page and save it. Returns filename or None."""
    images = page.images
    if not images:
        return None
    try:
        os.makedirs(IMAGES_DIR, exist_ok=True)
        # Use the largest image on the page (skip tiny logos)
        big_imgs = [img for img in images if img['width'] > 100 and img['height'] > 60]
        if not big_imgs:
            return None
        # Sort by area, pick largest
        big_imgs.sort(key=lambda x: x['width'] * x['height'], reverse=True)
        img_info = big_imgs[img_index] if img_index < len(big_imgs) else big_imgs[0]
        bbox = (img_info['x0'], img_info['top'], img_info['x1'], img_info['bottom'])
        cropped = page.crop(bbox)
        rendered = cropped.to_image(resolution=150).original
        filename = f'q{q_num}.png'
        filepath = os.path.join(IMAGES_DIR, filename)
        rendered.save(filepath)
        return filename
    except Exception as e:
        print(f'  Warning: Could not extract image for Q{q_num}: {e}')
        return None


def parse_options(block):
    """Parse answer options. Handles inline text (A. text) and image-only options (A. with no text)."""
    options = {}
    # Try inline format first: A. some text on same line
    inline = re.compile(r'^([A-E])\.\s+(.+)', re.MULTILINE)
    for m in inline.finditer(block):
        text = m.group(2).strip()
        # Only skip if it looks like another option marker (e.g. "B. something")
        if text and not re.match(r'^[A-E]\.\s', text):
            options[m.group(1)] = text
    if options:
        return options
    # Multi-line format: letter alone on a line, text on next lines
    multiline = re.compile(r'^([A-E])\.\s*\n(.*?)(?=^[A-E]\.\s*[\n$]|Answer:|$)', re.MULTILINE | re.DOTALL)
    for m in multiline.finditer(block):
        letter = m.group(1)
        text = re.sub(r'\n+', ' ', m.group(2)).strip()
        options[letter] = text if text else '[See image]'
    if options:
        return options
    # Image-only options: just letter lines with no text (A.\nB.\nC.\nD.)
    letters = re.findall(r'^([A-E])\.\s*$', block, re.MULTILINE)
    for letter in letters:
        options[letter] = '[See image]'
    return options


def parse_questions(pdf_path, progress_callback=None):
    os.makedirs(IMAGES_DIR, exist_ok=True)

    # Pass 1: collect full text per page + track which page each question starts on
    page_texts = []
    page_has_images = []
    q_start_page = {}  # q_num -> page_index

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f'Reading {total_pages} pages...')
        for i, page in enumerate(pdf.pages):
            t = page.extract_text() or ''
            page_texts.append(t)
            page_has_images.append(bool(page.images))
            for m in re.finditer(r'QUESTION NO:\s*(\d+)', t):
                q_start_page[int(m.group(1))] = i
            if progress_callback and i % 50 == 0:
                progress_callback(i, total_pages)

    # Join all text
    full_text = clean_text('\n'.join(page_texts))

    # Split by QUESTION NO:
    parts = re.split(r'QUESTION NO:\s*(\d+)', full_text)
    questions = []

    print('Parsing questions and extracting images...')
    with pdfplumber.open(pdf_path) as pdf:
        i = 1
        while i < len(parts) - 1:
            q_num = parts[i].strip()
            block = parts[i + 1] if i + 1 < len(parts) else ''

            try:
                q_id = int(q_num)
            except ValueError:
                i += 2
                continue

            # Lab simulation questions — parse tasks + explanation
            if re.search(r'CORRECT TEXT', block[:60]):
                expl_m = re.search(r'Explanation:\s*(.*?)(?=QUESTION NO:|$)', block, re.DOTALL)
                expl   = re.sub(r'\n+', ' ', expl_m.group(1)).strip() if expl_m else ''
                # Extract task block (between "Tasks" header and "Answer:")
                task_m = re.search(r'Tasks\s*\n(.*?)(?=Answer:|Explanation:|$)', block, re.DOTALL)
                task_text = re.sub(r'\n+', '\n', task_m.group(1)).strip() if task_m else ''
                # Fallback: use everything before Answer: as description
                if not task_text:
                    pre_ans = re.split(r'\nAnswer:', block)[0]
                    task_text = re.sub(r'CORRECT TEXT\s*\n?', '', pre_ans).strip()
                    task_text = re.sub(r'Guidelines\s*\n.*?(?=Tasks|\Z)', '', task_text, flags=re.DOTALL).strip()
                if task_text or expl:
                    questions.append({
                        'id': q_id,
                        'question': task_text or 'Lab simulation — refer to Packet Tracer.',
                        'options': {},
                        'answers': [],
                        'explanation': expl,
                        'multiple': False,
                        'image': None,
                        'has_exhibit': False,
                        'type': 'lab',
                    })
                i += 2
                continue

            # Detect DRAG DROP
            is_drag_drop = bool(re.search(r'DRAG DROP', block[:60]))

            # Answer
            answer_match = re.search(r'^Answer:\s*([A-E][, A-E]*)\s*$', block, re.MULTILINE)
            correct_answers = []
            if answer_match:
                raw = answer_match.group(1).strip()
                correct_answers = sorted(set(a.strip() for a in re.split(r'[,\s]+', raw) if a.strip()))

            # Explanation
            explanation = ''
            expl_match = re.search(r'Explanation:\s*(.*?)(?=QUESTION NO:|$)', block, re.DOTALL)
            if expl_match:
                explanation = re.sub(r'\n+', ' ', expl_match.group(1)).strip()

            # Question text
            q_text_match = re.match(r'(.*?)(?=^[A-E]\.\s*[\n$]|Answer:|Explanation:)', block, re.DOTALL | re.MULTILINE)
            q_text = q_text_match.group(1).strip() if q_text_match else block.split('\n')[0].strip()
            q_text = re.sub(r'^(DRAG DROP\s*)', '', q_text, flags=re.IGNORECASE).strip()
            q_text = re.sub(r'\n+', ' ', q_text).strip()

            # Options
            options = parse_options(block) if not is_drag_drop else {}

            # Image: only assign if question references an exhibit/topology
            EXHIBIT_RE = re.compile(
                r'\b(exhibit|refer to|topology shown|diagram|figure|shown below|the following)\b',
                re.IGNORECASE,
            )
            image_file = None
            has_exhibit = bool(EXHIBIT_RE.search(q_text)) and not is_drag_drop
            start_pg = q_start_page.get(q_id)
            if has_exhibit and start_pg is not None:
                for pg_offset in range(3):
                    pg_idx = start_pg + pg_offset
                    if pg_idx < len(pdf.pages) and page_has_images[pg_idx]:
                        img_file = extract_page_image(pdf.pages[pg_idx], q_id)
                        if img_file:
                            image_file = img_file
                            break

            # Include if we have question text and either options+answer or drag-drop
            if q_text and (is_drag_drop or (options and correct_answers)):
                questions.append({
                    'id': q_id,
                    'question': q_text,
                    'options': options,
                    'answers': correct_answers,
                    'explanation': explanation,
                    'multiple': len(correct_answers) > 1,
                    'image': image_file,
                    'has_exhibit': has_exhibit,
                    'type': 'drag_drop' if is_drag_drop else 'mcq',
                })

            i += 2

    return questions


if __name__ == '__main__':
    import sys
    pdf = sys.argv[1] if len(sys.argv) > 1 else 'C:/Users/enzoa/OneDrive/Desktop/200-301.pdf'
    print(f'Parsing {pdf}...')
    questions = parse_questions(pdf)
    with open(QUESTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    total_with_img = sum(1 for q in questions if q['image'])
    print(f'Parsed {len(questions)} questions ({total_with_img} with images) -> questions.json')
    for q in questions[:5]:
        img_marker = f'[IMG:{q["image"]}]' if q['image'] else ''
        print(f"Q{q['id']}: {q['question'][:70]}... {img_marker}")
        print(f"  opts={list(q['options'].keys())} ans={q['answers']}")
