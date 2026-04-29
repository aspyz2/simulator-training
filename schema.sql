-- CCNA Simulator — Supabase Schema
-- Run this in the Supabase SQL Editor

-- ── USER PROGRESS ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_progress (
  user_id     UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  data        JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── ACTIVE STUDY SESSION ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS active_study (
  user_id     UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  data        JSONB,
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── ACTIVE EXAM SESSION ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS active_exam (
  user_id     UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  data        JSONB,
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── ROW LEVEL SECURITY ────────────────────────────────────────────────────────
ALTER TABLE user_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE active_study  ENABLE ROW LEVEL SECURITY;
ALTER TABLE active_exam   ENABLE ROW LEVEL SECURITY;

CREATE POLICY "own_progress" ON user_progress FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "own_study"    ON active_study  FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "own_exam"     ON active_exam   FOR ALL USING (auth.uid() = user_id);
