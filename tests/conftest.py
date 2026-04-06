"""
Shared fixtures and helpers for the test suite.
Tests run against production Supabase — no mock.
"""
import os
import sys
import pytest
import pandas as pd
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


@pytest.fixture(scope="session")
def supabase_client() -> Client:
    """Shared Supabase client for all tests."""
    assert SUPABASE_URL, "SUPABASE_URL not set in .env"
    assert SUPABASE_KEY, "SUPABASE_KEY not set in .env"
    return create_client(SUPABASE_URL, SUPABASE_KEY)


@pytest.fixture(scope="session")
def test_farm():
    """Farm to use for all tests."""
    return "Farm 126"


@pytest.fixture(scope="session")
def test_team():
    return "NT1"


@pytest.fixture(scope="session")
def test_password():
    return "6677028"


@pytest.fixture(scope="session")
def test_lot(supabase_client, test_farm):
    """Get a real lot name that exists in dim_lo for the test farm."""
    res = supabase_client.table("dim_lo").select("lo_name, lo_id, dim_farm!inner(farm_name)") \
        .eq("dim_farm.farm_name", test_farm).eq("is_active", True).limit(1).execute()
    assert res.data, f"No lots found in dim_lo for {test_farm}"
    return res.data[0]


@pytest.fixture(scope="session")
def dim_lo_id_for_test(test_lot):
    return test_lot["lo_id"]


# All insertable tables that use dim_lo_id
TABLES_WITH_DIM_LO = [
    "stage_logs", "harvest_logs", "destruction_logs", "bsr_logs",
    "size_measure_logs", "tree_inventory_logs", "soil_ph_logs",
    "fusarium_logs", "seasons", "base_lots"
]

# Columns that were REMOVED from fact tables during normalization
DEPRECATED_COLUMNS = ["farm", "team", "lot_id", "lo"]
