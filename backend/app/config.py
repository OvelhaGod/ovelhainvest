"""Application configuration — reads from .env via pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Supabase
    supabase_url: str = ""
    supabase_service_key: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # Market data
    market_data_provider: str = "yfinance"
    finnhub_api_key: str = ""   # free tier, for news + earnings

    # Notifications
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Caching
    redis_url: str = ""         # Upstash Redis URL

    # App
    app_env: str = "development"
    secret_key: str = "change-me-in-production"
    admin_secret: str = "change-me-in-production"
    app_base_url: str = "http://localhost:8000"

    # Telegram webhook
    telegram_webhook_secret: str = ""  # X-Telegram-Bot-Api-Secret-Token header value

    # Default user (set after creating Thiago's user record)
    default_user_id: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def redis_enabled(self) -> bool:
        return bool(self.redis_url)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)

    @property
    def ai_configured(self) -> bool:
        return bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Module-level singleton for backwards compat
settings = get_settings()


def get_default_user_id() -> str:
    """Return configured default user ID. Single-user app convenience."""
    return settings.default_user_id or "00000000-0000-0000-0000-000000000001"
