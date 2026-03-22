"""Supabase client singleton — backend uses service key."""

import logging
from functools import lru_cache

from supabase import Client, create_client

from app.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Return a cached Supabase client instance (service key)."""
    try:
        client = create_client(settings.supabase_url, settings.supabase_service_key)
        logger.info("Supabase client initialised")
        return client
    except Exception as exc:
        logger.error("Failed to initialise Supabase client: %s", exc)
        raise


def check_supabase_connection() -> bool:
    """Ping Supabase to verify connectivity. Returns True if healthy."""
    try:
        client = get_supabase_client()
        # Light query — just checks auth/connection
        client.table("users").select("id").limit(1).execute()
        return True
    except Exception as exc:
        logger.warning("Supabase connection check failed: %s", exc)
        return False
