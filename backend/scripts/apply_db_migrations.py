"""
Apply all SQL migrations to Supabase via direct PostgreSQL connection.
Requires: SUPABASE_DB_PASSWORD in .env (Settings > Database > Database password)

Run: cd backend && uv run python scripts/apply_db_migrations.py
"""
import glob
import os
import sys

import pg8000.native
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD", "")
REF = SUPABASE_URL.replace("https://", "").replace(".supabase.co", "").strip()

if not DB_PASSWORD:
    print("ERROR: SUPABASE_DB_PASSWORD not set in .env")
    print("  Get it: Supabase dashboard > Settings > Database > Database password")
    sys.exit(1)


def run():
    print(f"Connecting to db.{REF}.supabase.co ...")
    conn = pg8000.native.Connection(
        user="postgres",
        password=DB_PASSWORD,
        host=f"db.{REF}.supabase.co",
        port=5432,
        database="postgres",
        ssl_context=True,
        timeout=30,
    )
    print(f"Connected: {conn.run('SELECT version()')[0][0][:50]}\n")

    conn.run("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    total_ok = total_err = 0
    for path in sorted(glob.glob("app/migrations/*.sql")):
        print(f"Applying {path}...")
        with open(path, encoding="utf-8") as f:
            sql = f.read()
        stmts = [
            s.strip() for s in sql.split(";")
            if s.strip() and not s.strip().startswith("--")
        ]
        ok = err = 0
        for stmt in stmts:
            try:
                conn.run(stmt)
                ok += 1
            except Exception as e:
                msg = str(e)
                skip_keywords = ["already exists", "duplicate", "DuplicateTable", "DuplicateObject"]
                if any(k in msg for k in skip_keywords):
                    ok += 1
                else:
                    print(f"  WARN: {msg[:120]}")
                    err += 1
        print(f"  {ok} ok / {err} errors")
        total_ok += ok
        total_err += err

    conn.close()
    print(f"\nTotal: {total_ok} statements ok / {total_err} errors")
    print("Run verify_migrations.py to confirm all tables exist.")


if __name__ == "__main__":
    run()
