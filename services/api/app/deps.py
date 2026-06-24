from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from supabase import create_client


load_dotenv()


@lru_cache(maxsize=1)
def get_supabase_client():
    """Create the Supabase REST client used by the read-only API."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY")
    return create_client(url, key)
