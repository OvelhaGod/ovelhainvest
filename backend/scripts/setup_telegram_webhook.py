"""
Item 9 — Register Telegram webhook.
Run: cd backend && uv run python scripts/setup_telegram_webhook.py

Requires: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, APP_BASE_URL in .env
The APP_BASE_URL must be publicly accessible (Cloudflare tunnel or ngrok).
"""
import sys
import os
import httpx
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import get_settings


def main():
    settings = get_settings()

    if not settings.telegram_bot_token or settings.telegram_bot_token == "FILL_IN_REQUIRED":
        print("ERROR: TELEGRAM_BOT_TOKEN not set in backend/.env")
        sys.exit(1)
    if not settings.telegram_chat_id or settings.telegram_chat_id == "FILL_IN_REQUIRED":
        print("ERROR: TELEGRAM_CHAT_ID not set in backend/.env")
        sys.exit(1)

    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id
    base_url = settings.app_base_url
    webhook_secret = settings.telegram_webhook_secret

    api_base = f"https://api.telegram.org/bot{token}"

    print(f"\nTelegram bot token: {token[:10]}...")
    print(f"Chat ID: {chat_id}")
    print(f"App base URL: {base_url}")

    # Register webhook
    webhook_url = f"{base_url}/webhooks/telegram"
    payload = {"url": webhook_url}
    if webhook_secret:
        payload["secret_token"] = webhook_secret

    print(f"\nRegistering webhook: {webhook_url}")
    resp = httpx.post(f"{api_base}/setWebhook", json=payload)
    print(f"  Response: {resp.json()}")

    # Get webhook info
    info = httpx.get(f"{api_base}/getWebhookInfo").json()
    print(f"\nWebhook info:")
    print(f"  url: {info.get('result', {}).get('url')}")
    print(f"  pending_update_count: {info.get('result', {}).get('pending_update_count')}")
    print(f"  last_error: {info.get('result', {}).get('last_error_message', 'none')}")

    # Send test message
    print("\nSending test message...")
    msg_resp = httpx.post(f"{api_base}/sendMessage", json={
        "chat_id": chat_id,
        "text": "OvelhaInvest v1.1.0 — Telegram connected. Webhook registered.",
        "parse_mode": "HTML",
    })
    if msg_resp.json().get("ok"):
        print("  Test message sent successfully.")
    else:
        print(f"  Message failed: {msg_resp.json()}")


if __name__ == "__main__":
    main()
