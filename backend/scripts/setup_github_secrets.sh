#!/bin/bash
# Sets GitHub Actions secrets required for keep-alive workflow
# Requires: gh CLI authenticated — https://cli.github.com/
# Usage: cd backend && bash scripts/setup_github_secrets.sh

set -e

if ! command -v gh &>/dev/null; then
  echo "Install gh CLI: https://cli.github.com/"
  exit 1
fi

source .env 2>/dev/null || true
REPO="OvelhaGod/ovelhainvest"

echo "Setting GitHub Actions secrets for $REPO..."

set_secret() {
  local name=$1
  local value=$2
  if [ -z "$value" ] || [ "$value" = "FILL_IN_REQUIRED" ] || [ "$value" = "FILL_IN_OPTIONAL" ]; then
    echo "  SKIP $name (empty)"
    return
  fi
  echo "$value" | gh secret set "$name" --repo "$REPO"
  echo "  OK   $name"
}

set_secret "SUPABASE_URL"         "$SUPABASE_URL"
set_secret "SUPABASE_SERVICE_KEY" "$SUPABASE_SERVICE_KEY"
set_secret "TELEGRAM_BOT_TOKEN"   "$TELEGRAM_BOT_TOKEN"
set_secret "TELEGRAM_CHAT_ID"     "$TELEGRAM_CHAT_ID"
set_secret "APP_BASE_URL"         "${APP_BASE_URL:-}"

echo ""
echo "Done. Verify at: https://github.com/$REPO/settings/secrets/actions"
echo "Trigger test:    https://github.com/$REPO/actions"
