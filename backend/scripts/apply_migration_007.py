"""Apply migration 007 (Phase 11 personal finance tables) via direct PostgreSQL connection."""
import os, sys, pathlib
from dotenv import load_dotenv

load_dotenv(dotenv_path=pathlib.Path(__file__).parent.parent / ".env")

SUPABASE_URL    = os.getenv("SUPABASE_URL", "")
DB_PASSWORD     = os.getenv("SUPABASE_DB_PASSWORD", "")
PROJECT_REF     = SUPABASE_URL.replace("https://", "").replace(".supabase.co", "")
DB_HOST         = f"db.{PROJECT_REF}.supabase.co"
DB_URL          = f"postgresql://postgres:{DB_PASSWORD}@{DB_HOST}:5432/postgres"

sql_path = pathlib.Path(__file__).parent.parent / "app" / "migrations" / "007_personal_finance.sql"
sql = sql_path.read_text(encoding="utf-8")

try:
    import psycopg2
    print(f"Connecting to {DB_HOST}...")
    conn = psycopg2.connect(DB_URL, connect_timeout=15)
    conn.autocommit = True
    cur = conn.cursor()
    print("Applying migration 007...")
    cur.execute(sql)
    print("Migration 007 applied successfully.")
    cur.close()
    conn.close()
    sys.exit(0)
except ImportError:
    print("psycopg2 not available, trying alternative...")

# Fallback: try via requests to a known working endpoint
try:
    import requests
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    # Newer Supabase versions expose /pg endpoint
    r = requests.post(f"{SUPABASE_URL}/pg/query", headers=headers, json={"query": "SELECT 1"}, timeout=10)
    if r.status_code == 200:
        # Run actual migration
        r2 = requests.post(f"{SUPABASE_URL}/pg/query", headers=headers, json={"query": sql}, timeout=30)
        if r2.status_code in (200, 201):
            print("Migration 007 applied via /pg/query.")
            sys.exit(0)
    print(f"Fallback failed: {r.status_code}")
except Exception as e:
    print(f"Fallback error: {e}")

print("\n--- MANUAL STEPS REQUIRED ---")
print("Copy and paste backend/app/migrations/007_personal_finance.sql into the Supabase SQL Editor:")
print(f"  https://supabase.com/dashboard/project/{PROJECT_REF}/sql/new")
sys.exit(1)
