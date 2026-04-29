"""
db.py — Supabase data access layer.
Replaces local progress.json / active_study.json / active_exam.json.
"""
import os
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_client: Client = create_client(
    os.environ['SUPABASE_URL'],
    os.environ['SUPABASE_SERVICE_KEY'],   # service key — server-side only
)

_PROGRESS_DEFAULT = {
    'current_position': 0,
    'lab_position': 0,
    'total_studied': 0,
    'daily_sessions': {},
    'question_stats': {},
    'batches': [],
}


# ── PROGRESS ──────────────────────────────────────────────────────────────────

def load_progress(user_id: str) -> dict:
    res = _client.table('user_progress').select('data').eq('user_id', user_id).maybe_single().execute()
    if res and res.data:
        merged = dict(_PROGRESS_DEFAULT)
        merged.update(res.data['data'])
        return merged
    return dict(_PROGRESS_DEFAULT)


def save_progress(user_id: str, progress: dict):
    _client.table('user_progress').upsert({
        'user_id': user_id,
        'data': progress,
    }).execute()


# ── ACTIVE STUDY ──────────────────────────────────────────────────────────────

def load_active_study(user_id: str) -> Optional[dict]:
    res = _client.table('active_study').select('data').eq('user_id', user_id).maybe_single().execute()
    return res.data['data'] if res and res.data and res.data.get('data') else None


def save_active_study(user_id: str, state: dict):
    _client.table('active_study').upsert({
        'user_id': user_id,
        'data': state,
    }).execute()


def clear_active_study(user_id: str):
    _client.table('active_study').upsert({
        'user_id': user_id,
        'data': None,
    }).execute()


# ── ACTIVE EXAM ───────────────────────────────────────────────────────────────

def load_active_exam(user_id: str) -> Optional[dict]:
    res = _client.table('active_exam').select('data').eq('user_id', user_id).maybe_single().execute()
    return res.data['data'] if res and res.data and res.data.get('data') else None


def save_active_exam(user_id: str, state: dict):
    _client.table('active_exam').upsert({
        'user_id': user_id,
        'data': state,
    }).execute()


def clear_active_exam(user_id: str):
    _client.table('active_exam').upsert({
        'user_id': user_id,
        'data': None,
    }).execute()


# ── AUTH ──────────────────────────────────────────────────────────────────────

def verify_token(jwt_token: str) -> Optional[str]:
    """Verify a Supabase JWT and return user_id, or None if invalid."""
    try:
        user = _client.auth.get_user(jwt_token)
        return user.user.id if user and user.user else None
    except Exception:
        return None
