import json
import os
import re
import random
import threading
from datetime import date
from functools import wraps
from typing import Optional
from dotenv import load_dotenv
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import db

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'ccna-simulator-secret-2024')

BASE           = os.path.dirname(__file__)
QUESTIONS_FILE = os.path.join(BASE, 'questions.json')

SUPABASE_URL  = os.environ['SUPABASE_URL']
SUPABASE_ANON = os.environ['SUPABASE_ANON_KEY']


# ── AUTH HELPERS ──────────────────────────────────────────────────────────────

def current_user_id() -> Optional[str]:
    return session.get('user_id')

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user_id():
            if request.is_json:
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated


# ── IN-MEMORY QUESTION CACHE ──────────────────────────────────────────────────

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


# ── PROGRESS (per-user via Supabase) ─────────────────────────────────────────

def load_progress():
    return db.load_progress(current_user_id())

def save_progress(progress):
    db.save_progress(current_user_id(), progress)

def load_active_study():
    return db.load_active_study(current_user_id())

def save_active_study(state):
    db.save_active_study(current_user_id(), state)

def clear_active_study():
    db.clear_active_study(current_user_id())

def load_active_exam():
    return db.load_active_exam(current_user_id())

def save_active_exam(state):
    db.save_active_exam(current_user_id(), state)

def clear_active_exam():
    db.clear_active_exam(current_user_id())


# ── AUTH ROUTES ───────────────────────────────────────────────────────────────

@app.route('/login')
def login_page():
    if current_user_id():
        return redirect(url_for('index'))
    return render_template('login.html',
        supabase_url=SUPABASE_URL,
        supabase_anon=SUPABASE_ANON,
    )

@app.route('/auth/session', methods=['POST'])
def auth_session():
    """Called by frontend after Supabase login — stores user_id in Flask session."""
    token = request.get_json().get('access_token', '')
    user_id = db.verify_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token'}), 401
    session['user_id'] = user_id
    session['token']   = token
    return jsonify({'ok': True})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))


# ── PAGES ─────────────────────────────────────────────────────────────────────

@app.route('/')
@login_required
def index():
    questions = load_questions()
    progress  = load_progress()
    today     = str(date.today())
    today_s   = progress['daily_sessions'].get(today, {})
    wrong_ids = [int(k) for k, v in progress['question_stats'].items() if v['wrong'] > v['correct']]
    active_study = load_active_study()
    active_exam  = load_active_exam()

    return render_template('index.html',
        total=len(questions),
        current_position=progress['current_position'],
        total_studied=progress['total_studied'],
        today_done=today_s.get('questions_done', 0),
        today_correct=today_s.get('correct', 0),
        wrong_count=len(wrong_ids),
        has_active_study=bool(active_study),
        has_active_exam=bool(active_exam),
    )


@app.route('/study')
@login_required
def study():
    return render_template('study.html')


@app.route('/exam')
@login_required
def exam():
    active_exam = load_active_exam()
    if not active_exam and 'exam_ids' not in session:
        progress = load_progress()
        return render_template('index.html', total=len(load_questions()),
                               error='Start an exam first.',
                               has_active_study=bool(load_active_study()),
                               has_active_exam=False,
                               current_position=progress['current_position'],
                               total_studied=progress['total_studied'],
                               today_done=0, today_correct=0, wrong_count=0)
    return render_template('exam.html')


# ── GLOBAL API AUTH ───────────────────────────────────────────────────────────

@app.before_request
def require_login_for_api():
    """All /api/ routes require an authenticated session."""
    if request.path.startswith('/api/') and not current_user_id():
        return jsonify({'error': 'Unauthorized'}), 401


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

    if mode == 'labs':
        batch = [q for q in questions if q.get('type') == 'lab']
        # respect position for labs too
        lab_pos = progress.get('lab_position', 0)
        batch = batch[lab_pos:lab_pos + count]
    elif mode == 'review':
        wrong_ids = {int(k) for k, v in progress['question_stats'].items() if v['wrong'] > v['correct']}
        batch = [q for q in questions if q['id'] in wrong_ids and q.get('type') != 'lab'][:count]
    else:
        non_labs = [q for q in questions if q.get('type') != 'lab']
        pos   = progress['current_position']
        batch = non_labs[pos:pos + count]

    result = [{
        'id': q['id'],
        'question': q['question'],
        'options': q['options'],
        'multiple': q['multiple'],
        'image': q.get('image'),
        'has_exhibit': q.get('has_exhibit', False),
        'type': q.get('type', 'mcq'),
        'explanation': q.get('explanation', ''),
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


@app.route('/api/study/lab-result', methods=['POST'])
def lab_result():
    """Record self-assessed lab result (correct/wrong)."""
    data       = request.get_json()
    q_id       = str(data['id'])
    is_correct = bool(data.get('correct', False))
    idx        = data.get('index')

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

    return jsonify({'ok': True})


@app.route('/api/study/labs/advance', methods=['POST'])
def labs_advance():
    """Advance the lab position after completing a batch."""
    data  = request.get_json()
    count = data.get('count', 0)
    progress = load_progress()
    all_labs = [q for q in load_questions() if q.get('type') == 'lab']
    progress['lab_position'] = min(
        progress.get('lab_position', 0) + count,
        len(all_labs)
    )
    save_progress(progress)
    return jsonify({'ok': True, 'lab_position': progress['lab_position']})


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
    all_labs  = [q for q in questions if q.get('type') == 'lab']
    non_labs  = [q for q in questions if q.get('type') != 'lab']
    return jsonify({
        'current_position': progress['current_position'],
        'total':            len(non_labs),
        'total_labs':       len(all_labs),
        'lab_position':     progress.get('lab_position', 0),
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

@app.route('/api/open-packet-tracer', methods=['POST'])
def open_packet_tracer():
    import subprocess, shutil
    pt_path = '/Applications/Cisco Packet Tracer 9.0.0/Cisco Packet Tracer 9.0.app'
    try:
        if os.path.exists(pt_path):
            subprocess.Popen(['open', pt_path])
        else:
            subprocess.Popen(['open', '-a', 'Cisco Packet Tracer'])
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/list-pdfs')
def list_pdfs():
    search_dirs = [
        os.path.expanduser('~/Downloads'),
        os.path.expanduser('~/Desktop'),
        os.path.expanduser('~/Documents'),
    ]
    found = []
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if name.lower().endswith('.pdf'):
                found.append({'name': name, 'path': os.path.join(d, name)})
    return jsonify(found)


# ── LAB VERIFICATION ──────────────────────────────────────────────────────────

_DEVICE_RE = re.compile(
    r'(?:On\s+)?(R\d+|SW-?\d+|Sw\w{0,3}\d*|Router\d*|Switch\w{0,6}\d*|DSW\d+|ASW\d+|HQ|Branch|Core)\s*:',
    re.IGNORECASE
)
_CLI_STARTS = re.compile(
    r'^(interface\b|int\s|ip\s|ipv6\s|no\s|switchport\b|vlan\s|router\s|spanning|channel-group|port-channel|shutdown|conf\b|configure\b|hostname\s|banner\s|line\s|username\s|crypto\s|aaa\s|snmp\s|logging\s|ntp\s|network\s|passive|area\s|neighbor\s|redistribute|eigrp\b|ospf\b|access-list\s|ip\s+route|ipv6\s+route|duplex|speed|description)',
    re.IGNORECASE
)
_SKIP_CMDS = re.compile(r'^(conf(igure)?(\s+t(erminal)?)?$|end$|exit$|enable$)', re.IGNORECASE)


def _tokenize_commands(flat_text):
    words, cmds, buf = flat_text.split(), [], []
    for w in words:
        if buf and _CLI_STARTS.match(w):
            line = ' '.join(buf).strip()
            if line and not _SKIP_CMDS.match(line):
                cmds.append(line)
            buf = [w]
        else:
            buf.append(w)
    if buf:
        line = ' '.join(buf).strip()
        if line and not _SKIP_CMDS.match(line):
            cmds.append(line)
    return cmds


def extract_lab_devices(explanation):
    if not explanation:
        return {}
    parts = _DEVICE_RE.split(explanation)
    devices = {}
    i = 1
    while i < len(parts) - 1:
        dev   = parts[i].strip().rstrip(':')
        block = parts[i + 1]
        block = re.split(r'(?:Task|Step)\s+\d+', block)[0]
        cmds  = _tokenize_commands(block)
        cmds  = [c for c in cmds if c.split() and _CLI_STARTS.match(c.split()[0])]
        key   = dev.upper()
        if key not in devices:
            devices[key] = {'name': dev, 'commands': []}
        for c in cmds:
            if c not in devices[key]['commands']:
                devices[key]['commands'].append(c)
        i += 2
    return devices


def _normalize(cmd):
    return re.sub(r'\s+', ' ', cmd.lower().strip())


def _cmd_in_showrun(cmd, showrun_lines):
    norm = _normalize(cmd)
    if len(norm) < 8:
        return None
    for line in showrun_lines:
        if norm in line:
            return True
    words = norm.split()
    if len(words) >= 2:
        for line in showrun_lines:
            if all(w in line for w in words):
                return True
    return False


@app.route('/api/lab/<int:lab_id>/devices')
def lab_devices(lab_id):
    q_map = {q['id']: q for q in load_questions()}
    q = q_map.get(lab_id)
    if not q or q.get('type') != 'lab':
        return jsonify({'error': 'Lab not found'}), 404
    devices = extract_lab_devices(q.get('explanation', ''))
    return jsonify({'devices': [{'name': v['name'], 'commands': v['commands']} for v in devices.values()]})


@app.route('/api/lab/verify', methods=['POST'])
def lab_verify():
    data    = request.get_json()
    lab_id  = data.get('lab_id')
    configs = data.get('configs', {})
    q_map   = {q['id']: q for q in load_questions()}
    q       = q_map.get(lab_id)
    if not q or q.get('type') != 'lab':
        return jsonify({'error': 'Lab not found'}), 404
    devices = extract_lab_devices(q.get('explanation', ''))
    results = {}
    for key, dev_data in devices.items():
        user_text = configs.get(dev_data['name'], configs.get(key, ''))
        if not user_text.strip():
            results[dev_data['name']] = {'skipped': True, 'commands': []}
            continue
        showrun_lines = [_normalize(l) for l in user_text.splitlines() if l.strip() and not l.strip().startswith('!')]
        cmd_results = []
        for cmd in dev_data['commands']:
            match = _cmd_in_showrun(cmd, showrun_lines)
            if match is None:
                continue
            cmd_results.append({'cmd': cmd, 'ok': match})
        results[dev_data['name']] = {'skipped': False, 'commands': cmd_results}
    return jsonify({'results': results})


_parse_state = {'running': False, 'page': 0, 'total': 0, 'done': False, 'error': None, 'count': 0}

@app.route('/api/parse-status')
def parse_status():
    return jsonify(_parse_state)

@app.route('/api/parse', methods=['POST'])
def parse_pdf():
    global _parse_state
    if _parse_state['running']:
        return jsonify({'error': 'Parse already running'}), 400
    data     = request.get_json()
    pdf_path = data.get('path', '')
    if not os.path.exists(pdf_path):
        return jsonify({'error': 'File not found'}), 400

    _parse_state = {'running': True, 'page': 0, 'total': 0, 'done': False, 'error': None, 'count': 0}

    def do_parse():
        global _parse_state
        try:
            from parser import parse_questions

            def on_progress(page, total):
                _parse_state['page'] = page
                _parse_state['total'] = total

            questions = parse_questions(pdf_path, progress_callback=on_progress)
            with open(QUESTIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(questions, f, ensure_ascii=False, indent=2)
            invalidate_questions_cache()
            _parse_state.update({'running': False, 'done': True, 'count': len(questions)})
        except Exception as e:
            _parse_state.update({'running': False, 'done': True, 'error': str(e)})

    threading.Thread(target=do_parse, daemon=True).start()
    return jsonify({'ok': True, 'started': True})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
