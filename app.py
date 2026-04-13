import json
import os
import random
from datetime import date
from flask import Flask, render_template, jsonify, request, session

app = Flask(__name__)
app.secret_key = 'ccna-simulator-secret-2024'

QUESTIONS_FILE = os.path.join(os.path.dirname(__file__), 'questions.json')
PROGRESS_FILE = os.path.join(os.path.dirname(__file__), 'progress.json')


# ── DATA HELPERS ────────────────────────────────────────────────────────────

def load_questions():
    if not os.path.exists(QUESTIONS_FILE):
        return []
    with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_progress():
    default = {
        'current_position': 0,
        'total_studied': 0,
        'daily_sessions': {},
        'question_stats': {},  # {str(q_id): {correct, wrong}}
    }
    if not os.path.exists(PROGRESS_FILE):
        return default
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Merge with defaults for missing keys
    for k, v in default.items():
        data.setdefault(k, v)
    return data


def save_progress(progress):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


# ── PAGES ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    questions = load_questions()
    progress = load_progress()
    today = str(date.today())
    today_session = progress['daily_sessions'].get(today, {})
    wrong_ids = [int(k) for k, v in progress['question_stats'].items() if v['wrong'] > v['correct']]

    return render_template('index.html',
        total=len(questions),
        current_position=progress['current_position'],
        total_studied=progress['total_studied'],
        today_done=today_session.get('questions_done', 0),
        today_correct=today_session.get('correct', 0),
        wrong_count=len(wrong_ids),
    )


@app.route('/study')
def study():
    return render_template('study.html')


@app.route('/exam')
def exam():
    if 'exam_ids' not in session:
        return render_template('index.html', total=len(load_questions()), error='Start an exam first.')
    return render_template('exam.html')


# ── STUDY MODE API ───────────────────────────────────────────────────────────

@app.route('/api/study/questions')
def study_questions():
    """Return the next batch of study questions from current position."""
    mode = request.args.get('mode', 'sequential')  # sequential | review
    count = int(request.args.get('count', 20))
    questions = load_questions()
    progress = load_progress()

    if mode == 'review':
        # Questions where wrong > correct
        wrong_ids = {int(k) for k, v in progress['question_stats'].items() if v['wrong'] > v['correct']}
        batch = [q for q in questions if q['id'] in wrong_ids][:count]
    else:
        pos = progress['current_position']
        batch = questions[pos:pos + count]

    # Strip answers for delivery
    result = []
    for q in batch:
        result.append({
            'id': q['id'],
            'question': q['question'],
            'options': q['options'],
            'multiple': q['multiple'],
            'image': q.get('image'),
            'has_exhibit': q.get('has_exhibit', False),
        })
    return jsonify({'questions': result, 'position': progress['current_position']})


@app.route('/api/study/answer', methods=['POST'])
def study_answer():
    """Check a single answer, return result + update progress."""
    data = request.get_json()
    q_id = str(data['id'])
    user_ans = sorted(data.get('answers', []))
    mode = data.get('mode', 'sequential')

    questions = load_questions()
    q_map = {str(q['id']): q for q in questions}
    q = q_map.get(q_id)
    if not q:
        return jsonify({'error': 'Question not found'}), 404

    correct = sorted(q['answers'])
    is_correct = user_ans == correct

    # Update progress
    progress = load_progress()
    stats = progress['question_stats'].setdefault(q_id, {'correct': 0, 'wrong': 0})
    if is_correct:
        stats['correct'] += 1
    else:
        stats['wrong'] += 1

    today = str(date.today())
    session_data = progress['daily_sessions'].setdefault(today, {
        'questions_done': 0, 'correct': 0, 'wrong': 0, 'q_ids': []
    })

    if q_id not in [str(x) for x in session_data.get('q_ids', [])]:
        session_data['questions_done'] += 1
        progress['total_studied'] += 1
        session_data['q_ids'].append(int(q_id))

    if is_correct:
        session_data['correct'] += 1
    else:
        session_data['wrong'] += 1

    save_progress(progress)

    return jsonify({
        'correct': is_correct,
        'correct_answers': correct,
        'user_answers': user_ans,
        'explanation': q.get('explanation', ''),
        'question': q['question'],
        'options': q['options'],
    })


@app.route('/api/study/advance', methods=['POST'])
def study_advance():
    """Move current_position forward and save batch record."""
    data = request.get_json()
    count = int(data.get('count', 20))
    correct = int(data.get('correct', 0))
    wrong = int(data.get('wrong', 0))
    progress = load_progress()
    questions = load_questions()

    start_pos = progress['current_position']
    end_pos = min(start_pos + count, len(questions))

    # Save batch to history
    progress.setdefault('batches', []).append({
        'session': len(progress.get('batches', [])) + 1,
        'start_pos': start_pos,          # 0-based index
        'end_pos': end_pos,
        'start_q': questions[start_pos]['id'] if start_pos < len(questions) else None,
        'end_q': questions[end_pos - 1]['id'] if end_pos > 0 and end_pos <= len(questions) else None,
        'correct': correct,
        'wrong': wrong,
        'date': str(date.today()),
    })

    progress['current_position'] = end_pos
    save_progress(progress)
    return jsonify({'new_position': end_pos, 'total': len(questions)})


@app.route('/api/study/jump', methods=['POST'])
def study_jump():
    """Jump to a specific position (0-based index)."""
    data = request.get_json()
    pos = int(data.get('position', 0))
    progress = load_progress()
    questions = load_questions()
    progress['current_position'] = max(0, min(pos, len(questions)))
    save_progress(progress)
    return jsonify({'new_position': progress['current_position'], 'total': len(questions)})


@app.route('/api/study/reset', methods=['POST'])
def study_reset():
    """Reset position to beginning (keep stats)."""
    progress = load_progress()
    progress['current_position'] = 0
    save_progress(progress)
    return jsonify({'ok': True})


@app.route('/api/progress')
def get_progress():
    progress = load_progress()
    questions = load_questions()
    today = str(date.today())
    today_session = progress['daily_sessions'].get(today, {})
    wrong_ids = [int(k) for k, v in progress['question_stats'].items() if v['wrong'] > v['correct']]

    # Build last 7 days history
    history = []
    all_days = sorted(progress['daily_sessions'].keys(), reverse=True)[:7]
    for day in all_days:
        s = progress['daily_sessions'][day]
        history.append({
            'date': day,
            'done': s.get('questions_done', 0),
            'correct': s.get('correct', 0),
            'wrong': s.get('wrong', 0),
        })

    return jsonify({
        'current_position': progress['current_position'],
        'total': len(questions),
        'total_studied': progress['total_studied'],
        'today_done': today_session.get('questions_done', 0),
        'today_correct': today_session.get('correct', 0),
        'wrong_count': len(wrong_ids),
        'history': history,
        'batches': list(reversed(progress.get('batches', []))),  # newest first
    })


# ── EXAM MODE API ────────────────────────────────────────────────────────────

@app.route('/api/start', methods=['POST'])
def start_exam():
    data = request.get_json()
    count = int(data.get('count', 50))
    randomize = data.get('randomize', True)
    questions = load_questions()

    if randomize:
        selected = random.sample(questions, min(count, len(questions)))
    else:
        selected = questions[:min(count, len(questions))]

    session['exam_ids'] = [q['id'] for q in selected]
    return jsonify({'count': len(selected), 'ok': True})


@app.route('/api/questions')
def get_questions():
    if 'exam_ids' not in session:
        return jsonify({'error': 'No active exam'}), 400

    all_qs = {q['id']: q for q in load_questions()}
    result = []
    for qid in session['exam_ids']:
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
    data = request.get_json()
    user_answers = data.get('answers', {})

    all_qs = {str(q['id']): q for q in load_questions()}
    results = []
    correct_count = 0

    for qid_str, user_ans in user_answers.items():
        q = all_qs.get(qid_str)
        if not q:
            continue
        correct = sorted(q['answers'])
        given = sorted(user_ans)
        is_correct = given == correct
        if is_correct:
            correct_count += 1
        results.append({
            'id': q['id'],
            'question': q['question'],
            'options': q['options'],
            'user_answers': given,
            'correct_answers': correct,
            'correct': is_correct,
            'explanation': q.get('explanation', ''),
            'multiple': q['multiple'],
            'image': q.get('image'),
        })

    total = len(results)
    score = round((correct_count / total) * 100, 1) if total else 0
    return jsonify({
        'score': score,
        'correct': correct_count,
        'total': total,
        'passed': score >= 82,
        'results': results,
    })


# ── PDF PARSE ────────────────────────────────────────────────────────────────

@app.route('/api/parse', methods=['POST'])
def parse_pdf():
    from parser import parse_questions
    data = request.get_json()
    pdf_path = data.get('path', '')
    if not os.path.exists(pdf_path):
        return jsonify({'error': 'File not found'}), 400
    try:
        questions = parse_questions(pdf_path)
        with open(QUESTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        return jsonify({'count': len(questions), 'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
