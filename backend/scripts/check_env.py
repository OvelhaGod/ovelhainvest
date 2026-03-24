"""
Item 1 — Environment verification.
Run: cd backend && uv run python scripts/check_env.py
"""
import sys
import os

# Must run from backend/ directory so .env is found
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import get_settings

s = get_settings()

CHECKS = {
    "SUPABASE_URL":        (s.supabase_url,         lambda v: v.startswith("https://") and "supabase.co" in v),
    "SUPABASE_SERVICE_KEY":(s.supabase_service_key,  lambda v: len(v) > 50 and v != "FILL_IN_REQUIRED"),
    "ANTHROPIC_API_KEY":   (s.anthropic_api_key,     lambda v: v.startswith("sk-ant-") and len(v) > 20),
    "TELEGRAM_BOT_TOKEN":  (s.telegram_bot_token,    lambda v: ":" in v and len(v) > 20 and v != "FILL_IN_REQUIRED"),
    "TELEGRAM_CHAT_ID":    (s.telegram_chat_id,      lambda v: len(v) > 3 and v != "FILL_IN_REQUIRED"),
    "REDIS_URL":           (s.redis_url,             lambda v: (v.startswith("redis://") or v.startswith("rediss://")) and len(v) > 20),
}

OPTIONAL = {"REDIS_URL", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"}

all_required_ok = True
print("\n=== OvelhaInvest Environment Check ===\n")

for name, (value, validator) in CHECKS.items():
    try:
        ok = bool(value) and validator(value)
    except Exception:
        ok = False

    optional = name in OPTIONAL
    if ok:
        print(f"  OK       {name}")
    elif optional:
        print(f"  OPTIONAL {name} (not set — feature disabled)")
    else:
        print(f"  MISSING  {name}  <-- REQUIRED")
        all_required_ok = False

print()
if all_required_ok:
    print("All required env vars are set. Ready to proceed.\n")
else:
    print("Fill in missing vars in backend/.env, then re-run this script.\n")
    print("Reference:")
    print("  SUPABASE_SERVICE_KEY : Supabase dashboard → Settings → API → service_role key")
    print("  ANTHROPIC_API_KEY    : https://console.anthropic.com/settings/keys")
    print("  TELEGRAM_BOT_TOKEN   : @BotFather → /newbot")
    print("  TELEGRAM_CHAT_ID     : curl 'https://api.telegram.org/bot<TOKEN>/getUpdates'")
    print("  REDIS_URL            : https://console.upstash.com → Redis → copy URL\n")
    sys.exit(1)
