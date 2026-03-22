"""
Redis client singleton (Upstash Redis).

Cache TTLs:
  - Market data:         15 minutes
  - Portfolio snapshots:  5 minutes
  - Monte Carlo results: 24 hours (invalidated on new snapshot)

Phase 2 implementation — stub only.
"""

import logging
from functools import lru_cache

import redis as redis_lib

from app.config import settings

logger = logging.getLogger(__name__)

# Cache TTL constants (seconds)
TTL_MARKET_DATA = 60 * 15       # 15 minutes
TTL_PORTFOLIO_SNAPSHOT = 60 * 5  # 5 minutes
TTL_MONTE_CARLO = 60 * 60 * 24  # 24 hours


@lru_cache(maxsize=1)
def get_redis_client() -> redis_lib.Redis:
    """Return a cached Redis client connected to Upstash."""
    try:
        client = redis_lib.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
        )
        client.ping()
        logger.info("Redis client initialised")
        return client
    except Exception as exc:
        logger.error("Failed to initialise Redis client: %s", exc)
        raise


def check_redis_connection() -> bool:
    """Ping Redis to verify connectivity."""
    try:
        client = get_redis_client()
        client.ping()
        return True
    except Exception as exc:
        logger.warning("Redis connection check failed: %s", exc)
        return False
