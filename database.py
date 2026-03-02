"""
Supabase client initialization.
Loads SUPABASE_URL and SUPABASE_KEY from .env.
"""

import os
from typing import Optional

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

_SUPABASE_URL = os.getenv("SUPABASE_URL")
_SUPABASE_KEY = os.getenv("SUPABASE_KEY")
_supabase: Optional[Client] = None


def _get_supabase() -> Client:
    global _supabase
    if _supabase is not None:
        return _supabase
    if not _SUPABASE_URL or not _SUPABASE_KEY:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY must be set in .env to use database endpoints."
        )
    _supabase = create_client(_SUPABASE_URL, _SUPABASE_KEY)
    return _supabase


def get_supabase() -> Client:
    """Return Supabase client. Use this in routes so app can start without .env."""
    return _get_supabase()
