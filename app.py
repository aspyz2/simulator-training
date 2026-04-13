import json
import os
import random
from datetime import date
from flask import Flask, render_template, jsonify, request, session

app = Flask(__name__)
app.secret_key = 'ccna-simulator-secret-2024'

BASE = os.path.dirname(__file__)
QUESTIONS_FILE    = os.path.join(BASE, 'questions.json')
PROGRESS_FILE     = os.path.join(BASE, 'progress.json')
ACTIVE_STUDY_FILE = os.path.join(BASE, 'active_study.json')
ACTIVE_EXAM_FILE  = os.path.join(BASE, 'active_exam.json')


# ── IN-MEMORY QUESTION CACHE ─────────────────────────────────────────────────
# Reads questions.json once; reloads only if the file changes on disk.

_q_cache = None
_q_mtime = None

def load_questions():
    global _q_cache, _q_mtime
    if not os.path.exists(QUESTIONS_FILE):
        return []
    mtime = os.path.getmtime(QUESTIONS_FILE)
    if _q_cache is None or mtime != _q_mtime:
        with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
            _q_cache = json.load(f)
        _q_mtime = mtime
    return _q_cache

def invalidate_questions_cache():
    global _q_cache, _q_mtime
    _q_cache = None
    _q_mtime = None


# ── PROGRESS ─────────────────────────────────────────────────────────────────

def load_progress():
    default = {
        'current_position': 0,
        'total_studied': 0,
        'daily_sessions': {},
        'question_stats': {},
        'batches': [],
    }
    if not os.path.exists(PROGRESS_FILE):
        return default
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for k, v in default.items():
        data.setdefault(k, v)
    return data

def save_progress(progress):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


# ── ACTIVE STUDY SESSION ──────────────────────────────────────────────────────
# Saved to disk so browser close / server restart doesn't lose in-progress work.

def load_active_study():
    if not os.path.exists(ACTIVE_STUDY_FILE):
        return None
    with open(ACTIVE_STUDY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_active_study(state):
    with open(ACTIVE_STUDY_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def clear_active_study():
    if os.path.exists(ACTIVE_STUDY_FILE):
        os.remove(ACTIVE_STUDY_FILE)


# ── ACTIVE EXAM SESSION ───────────────────────────────────────────────────────

def load_active_exam():
    if not os.path.exists(ACTIVE_EXAM_FILE):
        return None
    with open(ACTIVE_EXAM_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_active_exam(state):
    with open(ACTIVE_EXAM_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def clear_active_exam():
    if os.path.exists(ACTIVE_EXAM_FILE):
        os.remove(ACTIVE_EXAM_FILE)


# ── PAGES ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    questions = load_questions()
    progress  = load_progress()
    today     = str(date.today())
    today_s   = progress['daily_sessions'].get(today, {})
    wrong_ids = [int(k) for k, v in progress['question_stats'].items() if v['wrong'] > v['correct']]
    has_active_study = os.path.exists(ACTIVE_STUDY_FILE)
    has_active_exam  = os.path.exists(ACTIVE_EXAM_FILE)

    return render_template('index.html',
        total=len(questions),
        current_position=progress['current_position'],
        total_studied=progress['total_studied'],
        today_done=today_s.get('questions_done', 0),
        today_correct=today_s.get('correct', 0),
        wrong_count=len(wrong_ids),
        has_active_study=has_active_study,
        has_active_exam=has_active_exam,
    )


@app.route('/study')
def study():
    return render_template('study.html')


@app.route('/exam')
def exam():
    if not os.path.exists(ACTIVE_EXAM_FILE) and 'exam_ids' not in session:
        return render_template('index.html', total=len(load_questions()),
                               error='Start an exam first.',
                               has_active_study=os.path.exists(ACTIVE_STUDY_FILE),
                               has_active_exam=False,
                               current_position=load_progress()['current_position'],
                               total_studied=load_progress()['total_studied'],
                               today_done=0, today_correct=0, wrong_count=0)
    return render_template('exam.html')


# ── STUDY MODE API ────────────────────────────────────────────────────────────

@app.route('/api/study/session')
def get_study_session():
    """Return active in-progress study session if one exists."""
    state = load_active_study()
    if state:
        return jsonify({'active': True, 'state': state})
    return jsonify({'active': False})


@app.route('/api/study/session/save', methods=['POST'])
def save_study_session():
    """Save current study session state to disk."""
    data = request.get_json()
    save_active_study(data)
    return jsonify({'ok': True})


@app.route('/api/study/questions')
def study_questions():
    """Return a fresh batch of questions and create a new active session."""
    mode  = request.args.get('mode', 'sequential')
    count = int(request.args.get('count', 20))
    questions = load_questions()
    progress  = load_progress()

    if mode == 'review':
        wrong_ids = {int(k) for k, v in progress['question_stats'].items() if v['wrong'] > v['correct']}
        batch = [q for q in questions if q['id'] in wrong_ids][:count]
    else:
        pos   = progress['current_position']
        batch = questions[pos:pos + count]

    result = [{
        'id': q['id'],
        'question': q['question'],
        'options': q['options'],
        'multiple': q['multiple'],
        'image': q.get('image'),
        'has_exhibit': q.get('has_exhibit', False),
    } for q in batch]

    # Create a fresh active session on disk
    active = {
        'mode': mode,
        'questions': result,
        'current': 0,
        'results': [None] * len(result),   # null=unanswered, true, false, 'skip'
        'correct': 0,
        'wrong': 0,
        'start_position': progress['current_position'],
    }
    save_active_study(active)

    return jsonify({'questions': result, 'position': progress['current_position']})


@app.route('/api/study/answer', methods=['POST'])
def study_answer():
    data    = request.get_json()
    q_id    = str(data['id'])
    user_ans = sorted(data.get('answers', []))
    mode    = data.get('mode', 'sequential')
    idx     = data.get('index', None)   # position in current batch

    questions = load_questions()
    q_map = {str(q['id']): q for q in questions}
    q = q_map.get(q_id)
    if not q:
        return jsonify({'error': 'Question not found'}), 404

    correct    = sorted(q['answers'])
    is_correct = user_ans == correct

    # Update persistent progress
    progress = load_progress()
    stats = progress['question_stats'].setdefault(q_id, {'correct': 0, 'wrong': 0})
    if is_correct:
        stats['correct'] += 1
    else:
        stats['wrong'] += 1

    today = str(date.today())
    day_s = progress['daily_sessions'].setdefault(today, {
        'questions_done': 0, 'correct': 0, 'wrong': 0, 'q_ids': []
    })
    if q_id not in [str(x) for x in day_s.get('q_ids', [])]:
        day_s['questions_done'] += 1
        progress['total_studied'] += 1
        day_s['q_ids'].append(int(q_id))
    if is_correct:
        day_s['correct'] += 1
    else:
        day_s['wrong'] += 1
    save_progress(progress)

    # Update active session on disk
    if idx is not None:
        active = load_active_study()
        if active:
            active['results'][idx] = is_correct
            if is_correct:
                active['correct'] += 1
            else:
                active['wrong'] += 1
            active['current'] = idx
            save_active_study(active)

    return jsonify({
        'correct': is_correct,
        'correct_answers': correct,
        'user_answers': user_ans,
        'explanation': q.get('explanation', ''),
        'question': q['question'],
        'options': q['options'],
    })


@app.route('/api/study/skip', methods=['POST'])
def study_skip():
    """Mark a question as skipped in the active session."""
    data = request.get_json()
    idx  = data.get('index')
    if idx is None:
        return jsonify({'ok': False}), 400
    active = load_active_study()
    if active:
        active['results'][idx] = 'skip'
        save_active_study(active)
    return jsonify({'ok': True})


@app.route('/api/study/advance', methods=['POST'])
def study_advance():
    data    = request.get_json()
    count   = int(data.get('count', 20))
    correct = int(data.get('correct', 0))
    wrong   = int(data.get('wrong', 0))

    progress  = load_progress()
    questions = load_questions()
    start_pos = progress['current_position']
    end_pos   = min(start_pos + count, len(questions))

    progress.setdefault('batches', []).append({
        'session':   len(progress.get('batches', [])) + 1,
        'start_pos': start_pos,
        'end_pos':   end_pos,
        'start_q':   questions[start_pos]['id'] if start_pos < len(questions) else None,
        'end_q':     questions[end_pos - 1]['id'] if 0 < end_pos <= len(questions) else None,
        'correct':   correct,
        'wrong':     wrong,
        'date':      str(date.today()),
    })
    progress['current_position'] = end_pos
    save_progress(progress)
    clear_active_study()   # session complete — remove the active file
    return jsonify({'new_position': end_pos, 'total': len(questions)})


@app.route('/api/study/jump', methods=['POST'])
def study_jump():
    data = request.get_json()
    pos  = int(data.get('position', 0))
    progress  = load_progress()
    questions = load_questions()
    progress['current_position'] = max(0, min(pos, len(questions)))
    save_progress(progress)
    clear_active_study()   # clear any in-progress session when jumping
    return jsonify({'new_position': progress['current_position'], 'total': len(questions)})


@app.route('/api/study/reset', methods=['POST'])
def study_reset():
    progress = load_progress()
    progress['current_position'] = 0
    save_progress(progress)
    clear_active_study()
    return jsonify({'ok': True})


@app.route('/api/progress')
def get_progress():
    progress  = load_progress()
    questions = load_questions()
    today     = str(date.today())
    today_s   = progress['daily_sessions'].get(today, {})
    wrong_ids = [int(k) for k, v in progress['question_stats'].items() if v['wrong'] > v['correct']]
    history   = []
    for day in sorted(progress['daily_sessions'].keys(), reverse=True)[:7]:
        s = progress['daily_sessions'][day]
        history.append({'date': day, 'done': s.get('questions_done', 0),
                        'correct': s.get('correct', 0), 'wrong': s.get('wrong', 0)})
    return jsonify({
        'current_position': progress['current_position'],
        'total':            len(questions),
        'total_studied':    progress['total_studied'],
        'today_done':       today_s.get('questions_done', 0),
        'today_correct':    today_s.get('correct', 0),
        'wrong_count':      len(wrong_ids),
        'history':          history,
        'batches':          list(reversed(progress.get('batches', []))),
    })


# ── EXAM MODE API ─────────────────────────────────────────────────────────────

@app.route('/api/start', methods=['POST'])
def start_exam():
    data      = request.get_json()
    count     = int(data.get('count', 50))
    randomize = data.get('randomize', True)
    questions = load_questions()

    if randomize:
        selected = random.sample(questions, min(count, len(questions)))
    else:
        selected = questions[:min(count, len(questions))]

    exam_state = {
        'exam_ids': [q['id'] for q in selected],
        'answers':  {},
        'marked':   [],
        'current':  0,
    }
    save_active_exam(exam_state)
    session['exam_ids'] = exam_state['exam_ids']
    return jsonify({'count': len(selected), 'ok': True})


@app.route('/api/exam/state')
def get_exam_state():
    """Return saved exam state for resume."""
    state = load_active_exam()
    if state:
        return jsonify({'active': True, 'state': state})
    return jsonify({'active': False})


@app.route('/api/exam/state/save', methods=['POST'])
def save_exam_state():
    """Auto-save exam answers + position to disk."""
    data = request.get_json()
    state = load_active_exam()
    if state:
        state['answers'] = data.get('answers', state.get('answers', {}))
        state['current'] = data.get('current', state.get('current', 0))
        state['marked']  = data.get('marked', state.get('marked', []))
        save_active_exam(state)
    return jsonify({'ok': True})


@app.route('/api/questions')
def get_questions():
    # Support resume from disk if cookie session is gone
    exam_state = load_active_exam()
    if not exam_state:
        if 'exam_ids' not in session:
            return jsonify({'error': 'No active exam'}), 400
        exam_ids = session['exam_ids']
    else:
        exam_ids = exam_state['exam_ids']
        session['exam_ids'] = exam_ids

    all_qs = {q['id']: q for q in load_questions()}
    result = []
    for qid in exam_ids:
        q = all_qs.get(qid)
        if q:
            result.append({
                'id': q['id'],
                'question': q['question'],
                'options': q['options'],
                'multiple': q['multiple'],
                'image': q.get('image'),
            })
    return jsonify(result)


@app.route('/api/submit', methods=['POST'])
def submit():
    data        = request.get_json()
    user_answers = data.get('answers', {})
    all_qs      = {str(q['id']): q for q in load_questions()}
    results     = []
    correct_count = 0

    for qid_str, user_ans in user_answers.items():
        q = all_qs.get(qid_str)
        if not q:
            continue
        correct    = sorted(q['answers'])
        given      = sorted(user_ans)
        is_correct = given == correct
        if is_correct:
            correct_count += 1
        results.append({
            'id': q['id'], 'question': q['question'], 'options': q['options'],
            'user_answers': given, 'correct_answers': correct,
            'correct': is_correct, 'explanation': q.get('explanation', ''),
            'multiple': q['multiple'], 'image': q.get('image'),
        })

    total = len(results)
    score = round((correct_count / total) * 100, 1) if total else 0
    clear_active_exam()   # exam submitted — clear saved state
    return jsonify({'score': score, 'correct': correct_count,
                    'total': total, 'passed': score >= 82, 'results': results})


# ── PDF PARSE ─────────────────────────────────────────────────────────────────

@app.route('/api/parse', methods=['POST'])
def parse_pdf():
    from parser import parse_questions
    data     = request.get_json()
    pdf_path = data.get('path', '')
    if not os.path.exists(pdf_path):
        return jsonify({'error': 'File not found'}), 400
    try:
        questions = parse_questions(pdf_path)
        with open(QUESTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        invalidate_questions_cache()
        return jsonify({'count': len(questions), 'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
