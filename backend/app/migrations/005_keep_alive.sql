-- Migration 005: Keep-alive table for preventing Supabase free tier pausing
-- Written by GitHub Actions (Mon/Thu) and n8n homelab (Tue/Fri)
-- Also written as side effect of every successful /run_allocation call

CREATE TABLE IF NOT EXISTS keep_alive_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  pinged_at timestamptz NOT NULL DEFAULT now(),
  source text NOT NULL DEFAULT 'github-actions',
  notes text
);

-- Index for cleanup queries (delete entries older than 30 days)
CREATE INDEX IF NOT EXISTS keep_alive_log_pinged_at_idx ON keep_alive_log(pinged_at);

-- Initial row so table is never empty
INSERT INTO keep_alive_log (source, notes)
VALUES ('initial-setup', 'Table created during OvelhaInvest Option B setup');
