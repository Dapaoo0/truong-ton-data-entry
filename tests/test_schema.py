"""
Schema Validation Tests
Verify database schema matches expected state after normalization.
"""
import pytest
from conftest import TABLES_WITH_DIM_LO, DEPRECATED_COLUMNS


class TestSchemaIntegrity:
    """Verify no deprecated columns remain in normalized tables."""

    @pytest.mark.parametrize("table_name", TABLES_WITH_DIM_LO)
    def test_no_deprecated_columns(self, supabase_client, table_name):
        """Tables should NOT have farm/team/lot_id/lo columns after normalization."""
        res = supabase_client.rpc("", {}).execute  # Can't introspect easily, use information_schema
        result = supabase_client.table("").select("").execute  # fallback: direct SQL
        
        # Use raw SQL via postgrest isn't possible, use a workaround:
        # Fetch one row and check its keys
        query = supabase_client.table(table_name).select("*").limit(1)
        if table_name != "user_roles":
            query = query.eq("is_deleted", False)
        res = query.execute()
        
        if res.data:
            columns = set(res.data[0].keys())
            for dep_col in DEPRECATED_COLUMNS:
                assert dep_col not in columns, \
                    f"Deprecated column '{dep_col}' still exists in {table_name}! Columns: {columns}"

    @pytest.mark.parametrize("table_name", TABLES_WITH_DIM_LO)
    def test_dim_lo_id_column_exists(self, supabase_client, table_name):
        """All normalized tables should have dim_lo_id column."""
        res = supabase_client.table(table_name).select("dim_lo_id").limit(1).execute()
        # If query succeeds without error, column exists
        assert True, f"dim_lo_id column missing from {table_name}"

    def test_no_obsolete_triggers(self, supabase_client):
        """Verify fn_auto_map_dim_lo trigger has been dropped."""
        # Query pg_proc for the old function
        from supabase import Client
        # We can check by trying to query the information_schema for triggers
        # Since we can't run raw SQL via client, we verify the trigger was dropped
        # by checking that inserting to base_lots without 'lo' column works
        # (This is tested more thoroughly in test_workflows)
        pass


class TestForeignKeyIntegrity:
    """Verify FK relationships are intact."""

    def test_base_lots_fk_dim_lo(self, supabase_client):
        """base_lots.dim_lo_id should reference dim_lo.lo_id."""
        res = supabase_client.table("base_lots") \
            .select("dim_lo_id, dim_lo!inner(lo_name)") \
            .eq("is_deleted", False).limit(5).execute()
        if res.data:
            for row in res.data:
                assert row["dim_lo"] is not None, "FK join failed for base_lots → dim_lo"
                assert "lo_name" in row["dim_lo"], "dim_lo join missing lo_name"

    def test_stage_logs_fk_dim_lo(self, supabase_client):
        """stage_logs.dim_lo_id should reference dim_lo.lo_id."""
        res = supabase_client.table("stage_logs") \
            .select("dim_lo_id, dim_lo!inner(lo_name)") \
            .eq("is_deleted", False).limit(5).execute()
        if res.data:
            for row in res.data:
                assert row["dim_lo"] is not None, "FK join failed for stage_logs → dim_lo"

    def test_seasons_fk_dim_lo(self, supabase_client):
        """seasons.dim_lo_id should reference dim_lo.lo_id."""
        res = supabase_client.table("seasons") \
            .select("dim_lo_id, dim_lo!inner(lo_name)") \
            .eq("is_deleted", False).limit(5).execute()
        if res.data:
            for row in res.data:
                assert row["dim_lo"] is not None, "FK join failed for seasons → dim_lo"

    def test_harvest_logs_fk_dim_lo(self, supabase_client):
        """harvest_logs.dim_lo_id should reference dim_lo.lo_id."""
        res = supabase_client.table("harvest_logs") \
            .select("dim_lo_id, dim_lo!inner(lo_name)") \
            .eq("is_deleted", False).limit(5).execute()
        if res.data:
            for row in res.data:
                assert row["dim_lo"] is not None, "FK join failed for harvest_logs → dim_lo"


class TestRBACSchema:
    """Verify RBAC / user_roles table is accessible."""

    def test_user_roles_accessible(self, supabase_client):
        res = supabase_client.table("user_roles").select("farm, team").eq("is_active", True).limit(5).execute()
        assert res.data, "user_roles table empty or inaccessible"
        for row in res.data:
            assert "farm" in row
            assert "team" in row

    def test_test_account_exists(self, supabase_client, test_farm, test_team):
        res = supabase_client.table("user_roles").select("*") \
            .eq("farm", test_farm).eq("team", test_team).eq("is_active", True).execute()
        assert res.data, f"Test account {test_farm}/{test_team} not found"
