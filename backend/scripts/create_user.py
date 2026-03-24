"""
Item 3 — Create Thiago's user record.
Run: cd backend && uv run python scripts/create_user.py

After running, DEFAULT_USER_ID is appended to backend/.env automatically.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.supabase_client import get_supabase_client
from app.config import get_settings
from pathlib import Path

EMAIL = "thiago@ovelha.us"
DISPLAY_NAME = "Thiago"

def main():
    settings = get_settings()
    if not settings.supabase_configured:
        print("ERROR: SUPABASE_SERVICE_KEY not set. Fill in backend/.env first.")
        sys.exit(1)

    client = get_supabase_client()

    existing = client.table("users").select("*").eq("email", EMAIL).execute()
    if existing.data:
        user_id = existing.data[0]["id"]
        print(f"User already exists: {user_id}")
    else:
        result = client.table("users").insert({
            "email": EMAIL,
            "display_name": DISPLAY_NAME,
        }).execute()
        user_id = result.data[0]["id"]
        print(f"Created user: {user_id}")

    # Write DEFAULT_USER_ID to .env
    env_path = Path(__file__).parent.parent / ".env"
    env_content = env_path.read_text(encoding="utf-8")

    if f"DEFAULT_USER_ID={user_id}" in env_content:
        print("DEFAULT_USER_ID already set in .env")
    elif "DEFAULT_USER_ID=" in env_content:
        # Replace the empty value
        lines = env_content.splitlines()
        new_lines = []
        for line in lines:
            if line.startswith("DEFAULT_USER_ID="):
                new_lines.append(f"DEFAULT_USER_ID={user_id}")
            else:
                new_lines.append(line)
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        print(f"Updated DEFAULT_USER_ID={user_id} in .env")
    else:
        with open(env_path, "a", encoding="utf-8") as f:
            f.write(f"\nDEFAULT_USER_ID={user_id}\n")
        print(f"Appended DEFAULT_USER_ID={user_id} to .env")

    print(f"\nUSER_ID={user_id}")
    return user_id


if __name__ == "__main__":
    main()
