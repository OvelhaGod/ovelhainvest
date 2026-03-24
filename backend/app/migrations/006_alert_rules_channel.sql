-- Migration 006: Add channel column to alert_rules
-- Fixes seed: BUILT_IN_ALERT_RULES includes channel field which was missing from schema.

ALTER TABLE alert_rules
  ADD COLUMN IF NOT EXISTS channel text NOT NULL DEFAULT 'telegram';
