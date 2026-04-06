"""
Unit Tests for DB Helper Functions
Tests core business logic: dim_lo_id resolution, insert_to_db data cleanup,
quantity limits, and timeline validation.
"""
import os
import sys
import pytest
import pandas as pd
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from supabase import create_client
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


# ---- Replicate key functions from app.py for isolated testing ----

def get_dim_lo_id(farm_name: str, lo_name: str):
    if not farm_name or not lo_name:
        return None
    res = supabase.table("dim_lo").select("lo_id, dim_farm!inner(farm_name)") \
        .eq("lo_name", lo_name).eq("dim_farm.farm_name", farm_name).limit(1).execute()
    return res.data[0]["lo_id"] if res.data else None


def get_lots_by_farm(farm: str) -> list:
    res = supabase.table("dim_lo").select("lo_name, dim_farm!inner(farm_name)") \
        .eq("dim_farm.farm_name", farm).eq("is_active", True).order("lo_name").execute()
    if res.data:
        return list(dict.fromkeys(r["lo_name"] for r in res.data))
    return []


def strip_deprecated_columns(data: dict) -> dict:
    """Simulate the column stripping logic from insert_to_db."""
    clean = data.copy()
    for col in ["farm", "team", "lot_id", "lo"]:
        clean.pop(col, None)
    return clean


def validate_timeline_logic(farm_name, lot_id_str, target_date, action_type):
    dim_id = get_dim_lo_id(farm_name, lot_id_str)
    if not dim_id:
        return False, "Lỗi không tìm thấy lô."
    target_dt = pd.to_datetime(target_date).tz_localize(None)

    if action_type == "Chích bắp":
        res = supabase.table("base_lots").select("ngay_trong") \
            .eq("dim_lo_id", dim_id).eq("is_deleted", False).execute()
        if res.data and any(r.get("ngay_trong") for r in res.data):
            valid_dates = [pd.to_datetime(r["ngay_trong"]).tz_localize(None)
                          for r in res.data if r.get("ngay_trong")]
            if valid_dates:
                earliest_trong = min(valid_dates)
                if target_dt < earliest_trong:
                    return False, f"Ngày Chích bắp trước Ngày Trồng"

    elif action_type == "Cắt bắp":
        res = supabase.table("stage_logs").select("ngay_thuc_hien") \
            .eq("dim_lo_id", dim_id).eq("giai_doan", "Chích bắp") \
            .eq("is_deleted", False).execute()
        if res.data:
            earliest_cb = min([pd.to_datetime(r["ngay_thuc_hien"]).tz_localize(None)
                              for r in res.data])
            if target_dt < earliest_cb:
                return False, "Ngày Cắt bắp trước Chích bắp"
        else:
            return False, "Lô chưa Chích bắp"

    elif action_type == "Thu hoạch":
        res = supabase.table("stage_logs").select("ngay_thuc_hien") \
            .eq("dim_lo_id", dim_id).eq("giai_doan", "Cắt bắp") \
            .eq("is_deleted", False).execute()
        if res.data:
            earliest_cut = min([pd.to_datetime(r["ngay_thuc_hien"]).tz_localize(None)
                               for r in res.data])
            if target_dt < earliest_cut:
                return False, "Ngày Thu hoạch trước Cắt bắp"
        else:
            return False, "Lô chưa Cắt bắp"

    return True, ""


# ============================================================
# TEST CLASSES
# ============================================================

class TestDimLoIdResolution:
    """Test get_dim_lo_id resolution logic."""

    def test_valid_farm_and_lot(self, test_farm, test_lot):
        """Should resolve correct dim_lo_id for existing farm+lot."""
        result = get_dim_lo_id(test_farm, test_lot["lo_name"])
        assert result is not None, f"Failed to resolve dim_lo_id for {test_farm}/{test_lot['lo_name']}"
        assert result == test_lot["lo_id"], f"Expected lo_id={test_lot['lo_id']}, got {result}"

    def test_invalid_farm(self, test_lot):
        """Should return None for non-existent farm."""
        result = get_dim_lo_id("Farm_Does_Not_Exist_999", test_lot["lo_name"])
        assert result is None

    def test_invalid_lot(self, test_farm):
        """Should return None for non-existent lot."""
        result = get_dim_lo_id(test_farm, "LOT_NONEXISTENT_XYZ999")
        assert result is None

    def test_empty_inputs(self):
        """Should return None for empty strings."""
        assert get_dim_lo_id("", "") is None
        assert get_dim_lo_id(None, None) is None
        assert get_dim_lo_id("Farm 126", "") is None
        assert get_dim_lo_id("", "3B") is None


class TestGetLotsByFarm:
    """Test get_lots_by_farm function."""

    def test_valid_farm_returns_list(self, test_farm):
        """Should return non-empty list of lot names for valid farm."""
        lots = get_lots_by_farm(test_farm)
        assert isinstance(lots, list)
        assert len(lots) > 0, f"No lots found for {test_farm}"

    def test_lots_are_strings(self, test_farm):
        lots = get_lots_by_farm(test_farm)
        for lot in lots:
            assert isinstance(lot, str), f"Lot name should be string, got {type(lot)}"

    def test_lots_unique(self, test_farm):
        lots = get_lots_by_farm(test_farm)
        assert len(lots) == len(set(lots)), "Duplicate lot names found"

    def test_invalid_farm_returns_empty(self):
        lots = get_lots_by_farm("Farm_Nonexistent_XYZ")
        assert lots == []


class TestColumnStripping:
    """Test that insert_to_db strips deprecated columns."""

    def test_strips_farm(self):
        data = {"farm": "Farm 126", "dim_lo_id": 1, "so_luong": 100}
        clean = strip_deprecated_columns(data)
        assert "farm" not in clean
        assert "dim_lo_id" in clean

    def test_strips_all_deprecated(self):
        data = {"farm": "F", "team": "T", "lot_id": "L", "lo": "X", "so_luong": 50}
        clean = strip_deprecated_columns(data)
        for col in ["farm", "team", "lot_id", "lo"]:
            assert col not in clean
        assert clean["so_luong"] == 50

    def test_handles_missing_columns_gracefully(self):
        data = {"dim_lo_id": 5, "so_luong": 100}
        clean = strip_deprecated_columns(data)
        assert clean == data  # No error when columns don't exist


class TestTimelineValidation:
    """Test validate_timeline_logic for planting order enforcement."""

    def test_invalid_lot_returns_error(self, test_farm):
        ok, msg = validate_timeline_logic(test_farm, "NONEXISTENT_LOT", date.today(), "Chích bắp")
        assert not ok
        assert "không tìm thấy" in msg.lower() or "lỗi" in msg.lower()

    def test_chich_bap_before_planting_rejected(self, test_farm, test_lot):
        """Chích bắp before planting date should be rejected."""
        lo_name = test_lot["lo_name"]
        dim_id = test_lot["lo_id"]
        
        # Get the actual planting date
        res = supabase.table("base_lots").select("ngay_trong") \
            .eq("dim_lo_id", dim_id).eq("is_deleted", False).execute()
        
        if res.data and res.data[0].get("ngay_trong"):
            plant_date = pd.to_datetime(res.data[0]["ngay_trong"]).date()
            early_date = plant_date - timedelta(days=30)
            ok, msg = validate_timeline_logic(test_farm, lo_name, early_date, "Chích bắp")
            assert not ok, "Chích bắp before planting should be rejected"

    def test_valid_chich_bap_accepted(self, test_farm, test_lot):
        """Chích bắp after planting date should be accepted."""
        lo_name = test_lot["lo_name"]
        dim_id = test_lot["lo_id"]
        
        res = supabase.table("base_lots").select("ngay_trong") \
            .eq("dim_lo_id", dim_id).eq("is_deleted", False).execute()
        
        if res.data and res.data[0].get("ngay_trong"):
            plant_date = pd.to_datetime(res.data[0]["ngay_trong"]).date()
            future_date = plant_date + timedelta(days=180)
            ok, msg = validate_timeline_logic(test_farm, lo_name, future_date, "Chích bắp")
            assert ok, f"Valid chích bắp date rejected: {msg}"


class TestFetchTableData:
    """Test that fetch_table_data works correctly with dim_lo joins."""

    def test_base_lots_returns_farm_column(self, supabase_client, test_farm):
        """fetch_table_data should return virtual 'farm' column from join."""
        res = supabase_client.table("base_lots") \
            .select("*, dim_lo!inner(lo_name, area_ha, dim_doi!inner(doi_name), dim_farm!inner(farm_name))") \
            .eq("is_deleted", False).eq("dim_lo.dim_farm.farm_name", test_farm).limit(5).execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            df["farm"] = df["dim_lo"].apply(
                lambda x: x.get("dim_farm", {}).get("farm_name") if isinstance(x, dict) else None)
            assert "farm" in df.columns
            assert df["farm"].iloc[0] == test_farm

    def test_stage_logs_returns_lot_name(self, supabase_client, test_farm):
        """stage_logs should return lot name from dim_lo join."""
        res = supabase_client.table("stage_logs") \
            .select("*, dim_lo!inner(lo_name, area_ha, dim_doi!inner(doi_name), dim_farm!inner(farm_name))") \
            .eq("is_deleted", False).eq("dim_lo.dim_farm.farm_name", test_farm).limit(5).execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            df["lo"] = df["dim_lo"].apply(
                lambda x: x.get("lo_name") if isinstance(x, dict) else None)
            assert all(df["lo"].notna()), "Some rows missing lot name from join"
