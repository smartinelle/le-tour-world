"""Supabase client configuration for le-tour.

This module provides a singleton Supabase client for authentication
and database operations.
"""

import os
import logging
from typing import Optional
from functools import lru_cache

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


class SupabaseConfig:
    """Configuration for Supabase connection."""

    def __init__(self) -> None:
        self.url = os.environ.get("SUPABASE_URL", "")
        self.anon_key = os.environ.get("SUPABASE_ANON_KEY", "")
        self.service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        self.app_url = os.environ.get("APP_URL", "http://localhost:8080")

    def is_configured(self) -> bool:
        """Check if Supabase is properly configured."""
        return bool(self.url and self.anon_key)

    def validate(self) -> None:
        """Validate configuration and raise if invalid."""
        if not self.url:
            raise ValueError("SUPABASE_URL environment variable is required")
        if not self.anon_key:
            raise ValueError("SUPABASE_ANON_KEY environment variable is required")


# Global config instance
_config: Optional[SupabaseConfig] = None


def get_supabase_config() -> SupabaseConfig:
    """Get Supabase configuration."""
    global _config
    if _config is None:
        _config = SupabaseConfig()
    return _config


@lru_cache()
def get_supabase_client():
    """Get singleton Supabase client.

    Returns:
        Supabase client instance

    Raises:
        ValueError: If Supabase is not configured
        ImportError: If supabase package is not installed
    """
    try:
        from supabase import create_client, Client
    except ImportError:
        raise ImportError("supabase package not installed. Run: pip install supabase")

    config = get_supabase_config()
    config.validate()

    client: Client = create_client(config.url, config.anon_key)
    logger.info(f"Supabase client initialized for {config.url}")

    return client


def get_supabase():
    """Alias for get_supabase_client.

    Convenience function for shorter imports.
    """
    return get_supabase_client()


def is_supabase_configured() -> bool:
    """Check if Supabase is configured without raising errors.

    Useful for graceful degradation when Supabase is optional.
    """
    return get_supabase_config().is_configured()
