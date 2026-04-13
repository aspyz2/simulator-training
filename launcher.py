"""
CCNA Simulator — standalone launcher.
Starts Flask on port 5000, opens the browser, keeps running.
"""
import sys
import os
import threading
import webbrowser
import time


# ── Fix paths when running as PyInstaller bundle ──────────────────────────────
def resource_path(rel):
    """Get absolute path to a resource — works for dev and PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, rel)
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), rel)


def data_path(rel):
    """
    User-writable data path (questions.json, progress.json, images).
    Stored next to the .exe so data persists between runs.
    """
    if hasattr(sys, '_MEIPASS'):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.abspath(os.path.dirname(__file__))
    path = os.path.join(base, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    return path


# Patch BASE in app.py before importing it
os.environ['CCNA_DATA_DIR'] = data_path('.')
os.environ['CCNA_RESOURCE_DIR'] = resource_path('.')

# ── Import app after env is set ───────────────────────────────────────────────
sys.path.insert(0, resource_path('.'))

from app import app, BASE

# Override file paths to use the data directory
import app as app_module

if hasattr(sys, '_MEIPASS'):
    data_dir = os.path.dirname(sys.executable)
    app_module.QUESTIONS_FILE    = os.path.join(data_dir, 'questions.json')
    app_module.PROGRESS_FILE     = os.path.join(data_dir, 'progress.json')
    app_module.ACTIVE_STUDY_FILE = os.path.join(data_dir, 'active_study.json')
    app_module.ACTIVE_EXAM_FILE  = os.path.join(data_dir, 'active_exam.json')
    # Override template/static folder
    app.template_folder = resource_path('templates')
    app.static_folder   = resource_path('static')
    # Images go next to the exe so they persist
    images_dir = os.path.join(data_dir, 'static', 'images')
    os.makedirs(images_dir, exist_ok=True)
    import parser as parser_module
    parser_module.IMAGES_DIR    = images_dir
    parser_module.QUESTIONS_FILE = app_module.QUESTIONS_FILE


PORT = 5000


def open_browser():
    time.sleep(1.5)
    webbrowser.open(f'http://localhost:{PORT}')


def run_server():
    app.run(host='127.0.0.1', port=PORT, debug=False, use_reloader=False)


if __name__ == '__main__':
    print(f'Starting CCNA Simulator on http://localhost:{PORT} ...')
    threading.Thread(target=open_browser, daemon=True).start()
    run_server()
