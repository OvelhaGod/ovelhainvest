"""
Update workflow JSON files with actual API URL before n8n import.
Run: cd backend && uv run python scripts/prepare_n8n_workflows.py
"""
import json
import os
import glob
from dotenv import load_dotenv

load_dotenv()

# n8n on homelab calls the API via the public tunnel URL
APP_BASE_URL = os.getenv("APP_BASE_URL", "https://ovelhainvest.ovelha.us")
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

print(f"API URL: {APP_BASE_URL}")
print(f"User ID: {DEFAULT_USER_ID}")

WORKFLOW_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "automation", "n8n")
WORKFLOW_DIR = os.path.abspath(WORKFLOW_DIR)

replacements = {
    "{API_URL}": APP_BASE_URL,
    "http://localhost:8000": APP_BASE_URL,
    "{DEFAULT_USER_ID}": DEFAULT_USER_ID,
    "{SUPABASE_URL}": SUPABASE_URL,
    "{SUPABASE_SERVICE_KEY}": SUPABASE_SERVICE_KEY,
    "{TELEGRAM_BOT_TOKEN}": TELEGRAM_BOT_TOKEN,
    "{TELEGRAM_CHAT_ID}": TELEGRAM_CHAT_ID,
}

source_files = sorted(glob.glob(os.path.join(WORKFLOW_DIR, "*.json")))
# Skip already-configured files
source_files = [f for f in source_files if "_configured" not in f]

print(f"\nProcessing {len(source_files)} workflow files from: {WORKFLOW_DIR}\n")

for filepath in source_files:
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    updated = content
    for placeholder, value in replacements.items():
        if value:
            updated = updated.replace(placeholder, value)

    output_path = filepath.replace(".json", "_configured.json")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(updated)

    name = os.path.basename(filepath)
    print(f"  OK: {name} -> {os.path.basename(output_path)}")

print(f"\nConfigured workflows ready in: {WORKFLOW_DIR}")
print("\nFiles ready for import:")
for f in sorted(glob.glob(os.path.join(WORKFLOW_DIR, "*_configured.json"))):
    print(f"  {os.path.basename(f)}")
