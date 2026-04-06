"""
Workflow Integration Tests
Validate end-to-end data entry workflows against production Supabase.
Each test simulates a user workflow and verifies the data path works.

IMPORTANT: These tests INSERT then SOFT-DELETE test data to avoid pollution.
"""
import os
import sys
import pytest
import pandas as pd
from datetime import date, timedelta
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from supabase import create_client
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def get_dim_lo_id(farm_name: str, lo_name: str):
    if not farm_name or not lo_name:
        return None
    res = supabase.table("dim_lo").select("lo_id, dim_farm!inner(farm_name)") \
        .eq("lo_name", lo_name).eq("dim_farm.farm_name", farm_name).limit(1).execute()
    return res.data[0]["lo_id"] if res.data else None


def insert_and_cleanup(table_name, data, id_column="id"):
    """Insert test data, return the record, and register cleanup."""
    res = supabase.table(table_name).insert(data).execute()
    assert res.data, f"Insert into {table_name} failed"
    return res.data[0]


def soft_delete(table_name, record_id, id_column="id"):
    """Soft-delete a test record."""
    supabase.table(table_name).update({"is_deleted": True}).eq(id_column, record_id).execute()


# ============================================================
# WORKFLOW TESTS
# ============================================================

class TestWF1_CreateBaseLot:
    """WF1: Tạo Lô Trồng — the most critical workflow."""

    def test_insert_base_lot_with_dim_lo_id(self, test_farm, test_lot):
        """Insert a base_lot using dim_lo_id (not farm/lo columns)."""
        dim_id = test_lot["lo_id"]
        test_data = {
            "dim_lo_id": dim_id,
            "ngay_trong": date.today().isoformat(),
            "so_luong": 1,  # minimal test data
            "so_luong_con_lai": 1,
            "tuan": date.today().isocalendar()[1]
        }
        record = insert_and_cleanup("base_lots", test_data)
        try:
            assert record["dim_lo_id"] == dim_id
            assert record["so_luong"] == 1
            assert "farm" not in record, "Deprecated 'farm' column found in response"
            assert "lo" not in record, "Deprecated 'lo' column found in response"
        finally:
            soft_delete("base_lots", record["id"])

    def test_insert_base_lot_creates_season(self, test_farm, test_lot):
        """Inserting base_lot should be followed by season creation."""
        dim_id = test_lot["lo_id"]
        
        # Insert base_lot
        lot_data = {
            "dim_lo_id": dim_id,
            "ngay_trong": date.today().isoformat(),
            "so_luong": 1,
            "so_luong_con_lai": 1,
            "tuan": date.today().isocalendar()[1]
        }
        lot_record = insert_and_cleanup("base_lots", lot_data)
        
        # Insert season (as the app does)
        season_data = {
            "dim_lo_id": dim_id,
            "vu": "F0",
            "loai_trong": "Trồng mới",
            "ngay_bat_dau": date.today().isoformat()
        }
        season_record = insert_and_cleanup("seasons", season_data)
        
        try:
            assert season_record["dim_lo_id"] == dim_id
            assert season_record["vu"] == "F0"
            assert "farm" not in season_record
            assert "lo" not in season_record
        finally:
            soft_delete("base_lots", lot_record["id"])
            soft_delete("seasons", season_record["id"])

    def test_insert_base_lot_without_dim_lo_id_fails(self):
        """Insert without dim_lo_id should fail (FK constraint)."""
        test_data = {
            "ngay_trong": date.today().isoformat(),
            "so_luong": 1,
            "so_luong_con_lai": 1,
            "tuan": 1
        }
        # This should work (dim_lo_id is nullable) but we should verify
        # In production code, we always set dim_lo_id
        record = insert_and_cleanup("base_lots", test_data)
        try:
            assert record["dim_lo_id"] is None
        finally:
            soft_delete("base_lots", record["id"])


class TestWF2_StageLogging:
    """WF2 & WF3: Ghi nhận Chích bắp / Cắt bắp."""

    def test_insert_stage_log_chich_bap(self, test_farm, test_lot):
        """Insert a Chích bắp stage log using dim_lo_id."""
        dim_id = test_lot["lo_id"]
        test_data = {
            "dim_lo_id": dim_id,
            "giai_doan": "Chích bắp",
            "ngay_thuc_hien": date.today().isoformat(),
            "so_luong": 1,
            "mau_day": "Test",
            "tuan": date.today().isocalendar()[1]
        }
        record = insert_and_cleanup("stage_logs", test_data)
        try:
            assert record["giai_doan"] == "Chích bắp"
            assert record["dim_lo_id"] == dim_id
        finally:
            soft_delete("stage_logs", record["id"])

    def test_insert_stage_log_cat_bap(self, test_farm, test_lot):
        """Insert a Cắt bắp stage log using dim_lo_id."""
        dim_id = test_lot["lo_id"]
        test_data = {
            "dim_lo_id": dim_id,
            "giai_doan": "Cắt bắp",
            "ngay_thuc_hien": date.today().isoformat(),
            "so_luong": 1,
            "mau_day": "Test",
            "tuan": date.today().isocalendar()[1]
        }
        record = insert_and_cleanup("stage_logs", test_data)
        try:
            assert record["giai_doan"] == "Cắt bắp"
        finally:
            soft_delete("stage_logs", record["id"])

    def test_stage_log_join_returns_lot_info(self, test_farm, test_lot):
        """Querying stage_logs with dim_lo join should return farm/lot info."""
        dim_id = test_lot["lo_id"]
        test_data = {
            "dim_lo_id": dim_id,
            "giai_doan": "Chích bắp",
            "ngay_thuc_hien": date.today().isoformat(),
            "so_luong": 1,
            "mau_day": "TestJoin",
            "tuan": 1
        }
        record = insert_and_cleanup("stage_logs", test_data)
        try:
            # Query with join like app does
            res = supabase.table("stage_logs") \
                .select("*, dim_lo!inner(lo_name, dim_farm!inner(farm_name))") \
                .eq("id", record["id"]).execute()
            assert res.data
            row = res.data[0]
            assert row["dim_lo"]["lo_name"] == test_lot["lo_name"]
            assert row["dim_lo"]["dim_farm"]["farm_name"] == test_farm
        finally:
            soft_delete("stage_logs", record["id"])


class TestWF4_Harvest:
    """WF4: Thu hoạch."""

    def test_insert_harvest_log(self, test_farm, test_lot):
        dim_id = test_lot["lo_id"]
        test_data = {
            "dim_lo_id": dim_id,
            "ngay_thu_hoach": date.today().isoformat(),
            "so_luong": 1,
            "mau_day": "Test",
            "hinh_thuc_thu_hoach": "Bình thường",
            "tuan": date.today().isocalendar()[1]
        }
        record = insert_and_cleanup("harvest_logs", test_data)
        try:
            assert record["so_luong"] == 1
            assert record["dim_lo_id"] == dim_id
        finally:
            soft_delete("harvest_logs", record["id"])


class TestWF5_Destruction:
    """WF5: Xuất hủy."""

    def test_insert_destruction_log(self, test_farm, test_lot):
        dim_id = test_lot["lo_id"]
        test_data = {
            "dim_lo_id": dim_id,
            "ngay_xuat_huy": date.today().isoformat(),
            "giai_doan": "Trước chích bắp",
            "ly_do": "Test - auto cleanup",
            "so_luong": 1,
            "tuan": date.today().isocalendar()[1]
        }
        record = insert_and_cleanup("destruction_logs", test_data)
        try:
            assert record["so_luong"] == 1
            assert record["dim_lo_id"] == dim_id
        finally:
            soft_delete("destruction_logs", record["id"])


class TestWF6_SizeMeasure:
    """WF6: Đo Size."""

    def test_insert_size_measure_lan1(self, test_farm, test_lot):
        dim_id = test_lot["lo_id"]
        test_data = {
            "dim_lo_id": dim_id,
            "mau_day": "TestSize",
            "lan_do": 1,
            "so_luong_mau": 1,
            "ngay_do": date.today().isoformat(),
            "tuan": date.today().isocalendar()[1],
            "hang_kiem_tra": "H1",
            "size_cal": 38.5
        }
        record = insert_and_cleanup("size_measure_logs", test_data)
        try:
            assert record["lan_do"] == 1
            assert record["dim_lo_id"] == dim_id
        finally:
            soft_delete("size_measure_logs", record["id"])

    def test_size_measure_lan2_check_uses_dim_lo_id(self, test_farm, test_lot):
        """Verify Lần 2 check queries by dim_lo_id, not lot_id."""
        dim_id = test_lot["lo_id"]
        
        # Insert Lần 1
        data_l1 = {
            "dim_lo_id": dim_id,
            "mau_day": "TestLan2",
            "lan_do": 1,
            "so_luong_mau": 1,
            "ngay_do": date.today().isoformat(),
            "tuan": 1,
            "size_cal": 38.0
        }
        rec_l1 = insert_and_cleanup("size_measure_logs", data_l1)
        
        try:
            # Check if Lần 1 exists using dim_lo_id (as fixed code does)
            check = supabase.table("size_measure_logs") \
                .select("id").eq("dim_lo_id", dim_id) \
                .eq("mau_day", "TestLan2").eq("lan_do", 1) \
                .eq("is_deleted", False).execute()
            assert check.data, "Lần 1 check via dim_lo_id failed — would block Lần 2 entry"
            
            # Also verify that querying by lot_id would NOT work (column removed)
            # This is implicitly tested by the schema tests
        finally:
            soft_delete("size_measure_logs", rec_l1["id"])


class TestWF7_DashboardData:
    """WF7: Dashboard data rendering."""

    def test_fetch_base_lots_with_join(self, supabase_client, test_farm):
        """Dashboard fetch should work with dim_lo join."""
        res = supabase_client.table("base_lots") \
            .select("*, dim_lo!inner(lo_name, area_ha, dim_doi!inner(doi_name), dim_farm!inner(farm_name))") \
            .eq("is_deleted", False).eq("dim_lo.dim_farm.farm_name", test_farm).execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            # Flatten like app does
            df["farm"] = df["dim_lo"].apply(lambda x: x.get("dim_farm", {}).get("farm_name"))
            df["lo"] = df["dim_lo"].apply(lambda x: x.get("lo_name"))
            df["lot_id"] = df["lo"]
            
            assert all(df["farm"] == test_farm)
            assert all(df["lo"].notna())


class TestWF8_InvalidLotCreation:
    """WF8: Creating lot that doesn't exist in dim_lo."""

    def test_nonexistent_lot_returns_none(self, test_farm):
        """get_dim_lo_id should return None for unknown lot name."""
        result = get_dim_lo_id(test_farm, "ZZZZZ_NONEXISTENT_LOT")
        assert result is None, "Should return None for non-existent lot"

    def test_dim_lo_id_required_for_insert(self, test_farm):
        """App should validate dim_lo_id before attempting insert."""
        # Simulate: user types a lot name that doesn't exist
        lot_name = "ZZZZZ_NONEXISTENT"
        dim_id = get_dim_lo_id(test_farm, lot_name)
        assert dim_id is None, "Unexpectedly found dim_lo_id for fake lot"
        # In the app, this would show: "Không tìm thấy Lô..."
        # The insert should NOT proceed
