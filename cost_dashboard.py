from __future__ import annotations

from datetime import date
from typing import Any, Iterable

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


COST_DASH_CACHE_TTL_SECONDS = 300
ALL_FARM_ACCOUNTS = {"Admin", "Phòng Kinh doanh"}

COLOR_LABOR = "#3b82f6"
COLOR_MATERIAL = "#f59e0b"
COLOR_TOTAL = "#2f855a"
COLOR_MUTED = "#64748b"


def _money(value: Any) -> float:
    try:
        if value is None or pd.isna(value):
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _to_number_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0)


def _format_vnd(value: Any) -> str:
    return f"{_money(value):,.0f} đ"


def _format_vnd_compact(value: Any) -> str:
    amount = _money(value)
    abs_amount = abs(amount)
    if abs_amount >= 1_000_000_000:
        return f"{amount / 1_000_000_000:,.1f} tỷ đ"
    if abs_amount >= 1_000_000:
        return f"{amount / 1_000_000:,.1f} triệu đ"
    return _format_vnd(amount)


def _farm_label(row: dict) -> str:
    return str(row.get("farm_name") or row.get("farm_code") or "").strip()


def _first_present(row: dict, fields: Iterable[str], default: str = "") -> str:
    for field in fields:
        value = row.get(field)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def _month_start(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.to_period("M").dt.to_timestamp()


def _safe_date(value: Any):
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    return ts.date()


def _select_rows(
    _supabase,
    table_name: str,
    select_cols: str,
    *,
    in_filter: tuple[str, tuple] | None = None,
    eq_filters: tuple[tuple[str, Any], ...] = (),
    order_col: str | None = None,
    page_size: int = 1000,
) -> list[dict]:
    rows: list[dict] = []
    start = 0
    while True:
        query = _supabase.table(table_name).select(select_cols)
        if in_filter:
            col, values = in_filter
            if not values:
                return []
            query = query.in_(col, list(values))
        for col, value in eq_filters:
            query = query.eq(col, value)
        if order_col:
            query = query.order(order_col, desc=False)
        res = query.range(start, start + page_size - 1).execute()
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        start += page_size
    return rows


@st.cache_data(ttl=COST_DASH_CACHE_TTL_SECONDS, show_spinner=False)
def _load_dim_farms(_supabase) -> list[dict]:
    return _select_rows(
        _supabase,
        "dim_farm",
        "farm_id, farm_code, farm_name, is_active",
        order_col="farm_id",
    )


@st.cache_data(ttl=COST_DASH_CACHE_TTL_SECONDS, show_spinner=False)
def _load_cost_dimensions(_supabase, farm_ids: tuple[int, ...]) -> dict[str, list[dict]]:
    lots = _select_rows(
        _supabase,
        "dim_lo",
        "lo_id, farm_id, doi_id, lo_code, lo_name, lo_type, area_ha, is_active",
        in_filter=("farm_id", farm_ids),
        order_col="lo_id",
    )
    lot_ids = tuple(
        int(row["lo_id"])
        for row in lots
        if row.get("lo_id") is not None
    )
    return {
        "lots": lots,
        "teams": _select_rows(
            _supabase,
            "dim_doi",
            "doi_id, farm_id, doi_code, doi_name, is_active",
            in_filter=("farm_id", farm_ids),
            order_col="doi_id",
        ),
        "jobs": _select_rows(
            _supabase,
            "dim_cong_viec",
            "cong_viec_id, ma_cv, ten_cong_viec, cong_doan, loai_cong",
            order_col="cong_viec_id",
        ),
        "materials": _select_rows(
            _supabase,
            "dim_vat_tu",
            "vat_tu_id, ma_vat_tu, ten_vat_tu, loai_vat_tu",
            order_col="vat_tu_id",
        ),
        "seasons": _select_rows(
            _supabase,
            "seasons",
            "id, dim_lo_id, vu, loai_trong, ngay_bat_dau, ngay_ket_thuc_thuc_te, is_deleted",
            in_filter=("dim_lo_id", lot_ids),
            eq_filters=(("is_deleted", False),),
            order_col="ngay_bat_dau",
        ) if lot_ids else [],
    }


@st.cache_data(ttl=COST_DASH_CACHE_TTL_SECONDS, show_spinner=False)
def _load_cost_labor_rows(_supabase, farm_ids: tuple[int, ...]) -> list[dict]:
    return _select_rows(
        _supabase,
        "fact_nhat_ky_san_xuat",
        "nhat_ky_id, farm_id, lo_id, doi_id, cong_viec_id, ngay, so_cong, thanh_tien, is_ho_tro",
        in_filter=("farm_id", farm_ids),
        order_col="nhat_ky_id",
    )


@st.cache_data(ttl=COST_DASH_CACHE_TTL_SECONDS, show_spinner=False)
def _load_cost_material_rows(_supabase, farm_ids: tuple[int, ...]) -> list[dict]:
    return _select_rows(
        _supabase,
        "fact_vat_tu",
        "vat_tu_fact_id, farm_id, lo_id, vat_tu_id, ngay, so_luong, thanh_tien, is_ho_tro",
        in_filter=("farm_id", farm_ids),
        order_col="vat_tu_fact_id",
    )


def _resolve_allowed_farms(current_farm: str, farm_rows: list[dict]) -> list[dict]:
    active_rows = [row for row in farm_rows if row.get("is_active") is not False]
    if current_farm in ALL_FARM_ACCOUNTS:
        return active_rows

    current = str(current_farm or "").strip()
    scoped = [
        row for row in active_rows
        if current in {_farm_label(row), str(row.get("farm_code") or "").strip()}
    ]
    return scoped


def _build_dim_maps(farm_rows: list[dict], dims: dict[str, list[dict]]) -> dict[str, dict]:
    farms = {row.get("farm_id"): row for row in farm_rows}
    lots = {row.get("lo_id"): row for row in dims.get("lots", [])}
    teams = {row.get("doi_id"): row for row in dims.get("teams", [])}
    jobs = {row.get("cong_viec_id"): row for row in dims.get("jobs", [])}
    materials = {row.get("vat_tu_id"): row for row in dims.get("materials", [])}
    return {
        "farms": farms,
        "lots": lots,
        "teams": teams,
        "jobs": jobs,
        "materials": materials,
    }


def _classify_material_type(row: pd.Series) -> str:
    material_type = str(row.get("loai_vat_tu") or "").strip()
    if material_type and material_type != "Không xác định":
        return material_type

    name = str(row.get("ten_vat_tu") or "").lower()
    if any(token in name for token in ["phân", "bio", "calci", "chế phẩm"]):
        return "Phân bón"
    if any(token in name for token in ["cây", "chuối già"]):
        return "Cây giống"
    if any(token in name for token in ["xốp", "túi", "băng keo", "bao", "thùng", "carton", "dây", "pallet"]):
        return "Vật tư tiêu hao"
    return "Không xác định"


def _build_labor_frame(rows: list[dict], maps: dict[str, dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=[
            "farm_code", "lo_code", "lo_type", "doi_code", "cong_doan",
            "ten_cong_viec", "ngay_dt", "thang", "so_cong", "thanh_tien", "is_ho_tro",
        ])

    df = pd.DataFrame(rows)
    farm_map, lot_map, team_map, job_map = maps["farms"], maps["lots"], maps["teams"], maps["jobs"]
    df["farm_code"] = df["farm_id"].map(lambda value: _farm_label(farm_map.get(value, {})))
    df["lo_code"] = df["lo_id"].map(lambda value: _first_present(lot_map.get(value, {}), ("lo_code", "lo_name"), "Khác"))
    df["lo_type"] = df["lo_id"].map(lambda value: _first_present(lot_map.get(value, {}), ("lo_type",), "Không ghi"))
    df["doi_code"] = df["doi_id"].map(lambda value: _first_present(team_map.get(value, {}), ("doi_code", "doi_name"), "Không ghi"))
    df["cong_doan"] = df["cong_viec_id"].map(lambda value: _first_present(job_map.get(value, {}), ("cong_doan",), "Không ghi"))
    df["ten_cong_viec"] = df["cong_viec_id"].map(lambda value: _first_present(job_map.get(value, {}), ("ten_cong_viec", "ma_cv"), "Không ghi"))
    df["ngay_dt"] = pd.to_datetime(df["ngay"], errors="coerce")
    df["thang"] = _month_start(df["ngay_dt"])
    df["so_cong"] = _to_number_series(df.get("so_cong", pd.Series(dtype=float)))
    df["thanh_tien"] = _to_number_series(df.get("thanh_tien", pd.Series(dtype=float)))
    df["is_ho_tro"] = df.get("is_ho_tro", False).fillna(False).astype(bool)
    return df


def _build_material_frame(rows: list[dict], maps: dict[str, dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=[
            "farm_code", "lo_code", "lo_type", "loai_vat_tu", "ten_vat_tu",
            "ngay_dt", "thang", "so_luong", "thanh_tien", "is_ho_tro",
        ])

    df = pd.DataFrame(rows)
    farm_map, lot_map, material_map = maps["farms"], maps["lots"], maps["materials"]
    df["farm_code"] = df["farm_id"].map(lambda value: _farm_label(farm_map.get(value, {})))
    df["lo_code"] = df["lo_id"].map(lambda value: _first_present(lot_map.get(value, {}), ("lo_code", "lo_name"), "Khác"))
    df["lo_type"] = df["lo_id"].map(lambda value: _first_present(lot_map.get(value, {}), ("lo_type",), "Không ghi"))
    df["ten_vat_tu"] = df["vat_tu_id"].map(lambda value: _first_present(material_map.get(value, {}), ("ten_vat_tu", "ma_vat_tu"), "Không xác định"))
    df["loai_vat_tu"] = df["vat_tu_id"].map(lambda value: _first_present(material_map.get(value, {}), ("loai_vat_tu",), "Không xác định"))
    df["loai_vat_tu"] = df.apply(_classify_material_type, axis=1)
    df["ngay_dt"] = pd.to_datetime(df["ngay"], errors="coerce")
    df["thang"] = _month_start(df["ngay_dt"])
    df["so_luong"] = _to_number_series(df.get("so_luong", pd.Series(dtype=float)))
    df["thanh_tien"] = _to_number_series(df.get("thanh_tien", pd.Series(dtype=float)))
    df["is_ho_tro"] = df.get("is_ho_tro", False).fillna(False).astype(bool)
    return df


def _build_season_frame(dims: dict[str, list[dict]], maps: dict[str, dict]) -> pd.DataFrame:
    rows = dims.get("seasons", [])
    if not rows:
        return pd.DataFrame(columns=["label", "lo_id", "vu", "vu_start", "vu_end", "farm_code", "lo_code"])

    data = []
    lot_map = maps["lots"]
    farm_map = maps["farms"]
    for row in rows:
        lo_id = row.get("dim_lo_id")
        lot = lot_map.get(lo_id, {})
        farm = farm_map.get(lot.get("farm_id"), {})
        start = pd.to_datetime(row.get("ngay_bat_dau"), errors="coerce")
        if pd.isna(start):
            continue
        end = pd.to_datetime(row.get("ngay_ket_thuc_thuc_te"), errors="coerce")
        if pd.isna(end):
            end = pd.Timestamp(date.today())
        farm_code = _farm_label(farm)
        lo_code = _first_present(lot, ("lo_code", "lo_name"), "Khác")
        vu = str(row.get("vu") or "Không ghi")
        data.append({
            "label": f"{farm_code} · Lô {lo_code} · Vụ {vu} ({start.strftime('%d/%m/%Y')} → {end.strftime('%d/%m/%Y')})",
            "lo_id": lo_id,
            "vu": vu,
            "vu_start": start,
            "vu_end": end,
            "farm_code": farm_code,
            "lo_code": lo_code,
        })
    return pd.DataFrame(data)


def _apply_season_filter(df: pd.DataFrame, selected_seasons: pd.DataFrame) -> pd.DataFrame:
    if df.empty or selected_seasons.empty:
        return df
    mask = pd.Series(False, index=df.index)
    for _, season in selected_seasons.iterrows():
        mask |= (
            (df.get("lo_id") == season["lo_id"]) &
            (df["ngay_dt"] >= season["vu_start"]) &
            (df["ngay_dt"] <= season["vu_end"])
        )
    return df[mask]


def _apply_cost_filters(
    labor_df: pd.DataFrame,
    material_df: pd.DataFrame,
    *,
    start_date: date,
    end_date: date,
    selected_lo_types: list[str],
    selected_los: list[str],
    selected_dois: list[str],
    selected_seasons: pd.DataFrame,
    include_support: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)

    def base_filter(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        out = df[(df["ngay_dt"] >= start_ts) & (df["ngay_dt"] <= end_ts)].copy()
        if selected_lo_types:
            out = out[out["lo_type"].isin(selected_lo_types)]
        if selected_los:
            out = out[out["lo_code"].isin(selected_los)]
        return _apply_season_filter(out, selected_seasons)

    labor = base_filter(labor_df)
    material = base_filter(material_df)
    if not labor.empty:
        if selected_dois:
            labor = labor[labor["doi_code"].isin(selected_dois)]
        if not include_support:
            labor = labor[~labor["is_ho_tro"]]
    return labor, material


def _apply_plot_style(fig: go.Figure, height: int = 340) -> None:
    fig.update_layout(
        height=height,
        template="plotly_white",
        margin=dict(t=44, r=16, b=46, l=16),
        legend=dict(orientation="h", y=1.06, x=0),
        font=dict(family="Arial, sans-serif", size=12, color="#273043"),
    )


def _render_section_title(title: str, caption: str | None = None) -> None:
    st.markdown(f"#### {title}")
    if caption:
        st.caption(caption)


def _sanitize_multiselect_state(key: str, options: Iterable[str]) -> None:
    if key not in st.session_state:
        return
    allowed = set(options)
    current = st.session_state.get(key) or []
    st.session_state[key] = [value for value in current if value in allowed]


def _sanitize_date_range_state(key: str, min_date: date, max_date: date) -> None:
    if key not in st.session_state:
        return
    current = st.session_state.get(key)
    if not isinstance(current, (tuple, list)) or len(current) != 2:
        st.session_state.pop(key, None)
        return
    start_value = _safe_date(current[0])
    end_value = _safe_date(current[1])
    if (
        start_value is None
        or end_value is None
        or start_value < min_date
        or end_value > max_date
        or start_value > end_value
    ):
        st.session_state.pop(key, None)


def _render_bar(
    df: pd.DataFrame,
    *,
    x_col: str,
    y_col: str,
    label_col: str,
    title: str,
    color: str,
    key: str,
    height: int = 360,
) -> None:
    if df.empty:
        st.info("Không có dữ liệu cho biểu đồ này.")
        return
    fig = go.Figure(go.Bar(
        x=df[x_col],
        y=df[y_col],
        orientation="h",
        marker_color=color,
        text=[_format_vnd_compact(v) for v in df[x_col]],
        textposition="auto",
        hovertemplate=f"<b>%{{y}}</b><br>{title}: %{{x:,.0f}} đ<extra></extra>",
    ))
    fig.update_layout(title=title, xaxis_tickformat=",.0f", yaxis=dict(automargin=True))
    _apply_plot_style(fig, height)
    st.plotly_chart(fig, use_container_width=True, key=key)


def _render_kpis(labor: pd.DataFrame, material: pd.DataFrame) -> None:
    labor_total = labor["thanh_tien"].sum() if not labor.empty else 0
    material_total = material["thanh_tien"].sum() if not material.empty else 0
    total = labor_total + material_total
    total_work = labor["so_cong"].sum() if not labor.empty else 0
    cols = st.columns(4)
    cols[0].metric("Tổng chi phí", _format_vnd_compact(total))
    cols[1].metric("Nhân công", _format_vnd_compact(labor_total), f"{labor_total / total * 100:.1f}%" if total else None)
    cols[2].metric("Vật tư", _format_vnd_compact(material_total), f"{material_total / total * 100:.1f}%" if total else None)
    cols[3].metric("Tổng số công", f"{total_work:,.1f}")


def _render_monthly_trend(labor: pd.DataFrame, material: pd.DataFrame) -> None:
    _render_section_title("Xu hướng chi phí theo tháng")
    mc = labor.groupby("thang")["thanh_tien"].sum().reset_index().rename(columns={"thanh_tien": "Nhân công"}) if not labor.empty else pd.DataFrame(columns=["thang", "Nhân công"])
    mv = material.groupby("thang")["thanh_tien"].sum().reset_index().rename(columns={"thanh_tien": "Vật tư"}) if not material.empty else pd.DataFrame(columns=["thang", "Vật tư"])
    monthly = mc.merge(mv, on="thang", how="outer").fillna(0).sort_values("thang")
    if monthly.empty:
        st.info("Không có dữ liệu theo tháng.")
        return
    monthly["Tháng"] = pd.to_datetime(monthly["thang"]).dt.strftime("%m/%Y")
    col_chart, col_pie = st.columns([3, 1])
    with col_chart:
        fig = go.Figure()
        fig.add_bar(x=monthly["Tháng"], y=monthly["Nhân công"], name="Nhân công", marker_color=COLOR_LABOR)
        fig.add_bar(x=monthly["Tháng"], y=monthly["Vật tư"], name="Vật tư", marker_color=COLOR_MATERIAL)
        fig.update_layout(barmode="stack", yaxis_tickformat=",.0f")
        _apply_plot_style(fig, 360)
        st.plotly_chart(fig, use_container_width=True, key="cost_dash_monthly_trend")
    with col_pie:
        labor_total = labor["thanh_tien"].sum() if not labor.empty else 0
        material_total = material["thanh_tien"].sum() if not material.empty else 0
        fig = go.Figure(go.Pie(
            labels=["Nhân công", "Vật tư"],
            values=[labor_total, material_total],
            marker_colors=[COLOR_LABOR, COLOR_MATERIAL],
            hole=0.58,
        ))
        _apply_plot_style(fig, 360)
        st.plotly_chart(fig, use_container_width=True, key="cost_dash_source_pie")


def _sum_by_source(labor: pd.DataFrame, material: pd.DataFrame, by_cols: list[str]) -> pd.DataFrame:
    labor_group = labor.groupby(by_cols)["thanh_tien"].sum().reset_index().rename(columns={"thanh_tien": "Nhân công"}) if not labor.empty else pd.DataFrame(columns=by_cols + ["Nhân công"])
    material_group = material.groupby(by_cols)["thanh_tien"].sum().reset_index().rename(columns={"thanh_tien": "Vật tư"}) if not material.empty else pd.DataFrame(columns=by_cols + ["Vật tư"])
    out = labor_group.merge(material_group, on=by_cols, how="outer").fillna(0)
    out["Tổng"] = _to_number_series(out["Nhân công"]) + _to_number_series(out["Vật tư"])
    return out.sort_values("Tổng", ascending=False).reset_index(drop=True)


def _render_overview_charts(labor: pd.DataFrame, material: pd.DataFrame) -> None:
    _render_section_title("Tổng quan theo farm, đội và lô")
    col1, col2 = st.columns(2)
    with col1:
        farm_totals = _sum_by_source(labor, material, ["farm_code"]).sort_values("Tổng", ascending=True)
        _render_bar(
            farm_totals.tail(12),
            x_col="Tổng",
            y_col="farm_code",
            label_col="farm_code",
            title="Chi phí theo farm",
            color=COLOR_TOTAL,
            key="cost_dash_farm_bar",
            height=max(300, len(farm_totals.tail(12)) * 42),
        )
    with col2:
        team_totals = labor.groupby("doi_code")["thanh_tien"].sum().reset_index() if not labor.empty else pd.DataFrame(columns=["doi_code", "thanh_tien"])
        team_totals = team_totals[team_totals["thanh_tien"] > 0].sort_values("thanh_tien", ascending=True).tail(15)
        _render_bar(
            team_totals,
            x_col="thanh_tien",
            y_col="doi_code",
            label_col="doi_code",
            title="Chi phí nhân công theo đội",
            color=COLOR_LABOR,
            key="cost_dash_team_bar",
            height=max(300, len(team_totals) * 30),
        )

    lot_totals = _sum_by_source(labor, material, ["farm_code", "lo_code"])
    lot_totals["label"] = lot_totals["farm_code"] + " · " + lot_totals["lo_code"]
    lot_top = lot_totals[lot_totals["Tổng"] > 0].sort_values("Tổng", ascending=True).tail(20)
    _render_bar(
        lot_top,
        x_col="Tổng",
        y_col="label",
        label_col="label",
        title="Top lô theo tổng chi phí",
        color="#6366f1",
        key="cost_dash_lot_bar",
        height=max(420, len(lot_top) * 26),
    )


def _render_cost_structure(labor: pd.DataFrame, material: pd.DataFrame) -> None:
    _render_section_title("Cơ cấu chi phí chi tiết")
    col1, col2 = st.columns(2)
    with col1:
        stage = labor.groupby("cong_doan")["thanh_tien"].sum().reset_index() if not labor.empty else pd.DataFrame(columns=["cong_doan", "thanh_tien"])
        stage = stage[stage["thanh_tien"] > 0].sort_values("thanh_tien", ascending=True).tail(12)
        _render_bar(
            stage,
            x_col="thanh_tien",
            y_col="cong_doan",
            label_col="cong_doan",
            title="Top công đoạn",
            color=COLOR_LABOR,
            key="cost_dash_stage_bar",
            height=max(320, len(stage) * 30),
        )
    with col2:
        material_type = material.groupby("loai_vat_tu")["thanh_tien"].sum().reset_index() if not material.empty else pd.DataFrame(columns=["loai_vat_tu", "thanh_tien"])
        material_type = material_type[material_type["thanh_tien"] > 0].sort_values("thanh_tien", ascending=True).tail(12)
        _render_bar(
            material_type,
            x_col="thanh_tien",
            y_col="loai_vat_tu",
            label_col="loai_vat_tu",
            title="Top loại vật tư",
            color=COLOR_MATERIAL,
            key="cost_dash_material_type_bar",
            height=max(320, len(material_type) * 30),
        )

    col3, col4 = st.columns(2)
    with col3:
        jobs = labor.groupby("ten_cong_viec")["thanh_tien"].sum().reset_index() if not labor.empty else pd.DataFrame(columns=["ten_cong_viec", "thanh_tien"])
        jobs = jobs[jobs["thanh_tien"] > 0].sort_values("thanh_tien", ascending=True).tail(12)
        _render_bar(
            jobs,
            x_col="thanh_tien",
            y_col="ten_cong_viec",
            label_col="ten_cong_viec",
            title="Top công việc",
            color="#2563eb",
            key="cost_dash_job_bar",
            height=max(360, len(jobs) * 32),
        )
    with col4:
        materials = material.groupby("ten_vat_tu")["thanh_tien"].sum().reset_index() if not material.empty else pd.DataFrame(columns=["ten_vat_tu", "thanh_tien"])
        materials = materials[materials["thanh_tien"] > 0].sort_values("thanh_tien", ascending=True).tail(12)
        _render_bar(
            materials,
            x_col="thanh_tien",
            y_col="ten_vat_tu",
            label_col="ten_vat_tu",
            title="Top vật tư",
            color="#d97706",
            key="cost_dash_material_bar",
            height=max(360, len(materials) * 32),
        )


def _render_paginated_dataframe(df: pd.DataFrame, *, key: str, page_size: int = 500) -> None:
    if df.empty:
        st.info("Không có dữ liệu.")
        return
    page_key = f"{key}_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 0
    total_pages = max(1, (len(df) + page_size - 1) // page_size)
    st.session_state[page_key] = min(st.session_state[page_key], total_pages - 1)
    page = st.session_state[page_key]

    col_info, col_prev, col_next = st.columns([6, 1, 1])
    start = page * page_size
    end = min(start + page_size, len(df))
    with col_info:
        st.caption(f"Hiển thị {start + 1:,}-{end:,} / {len(df):,} dòng · Trang {page + 1}/{total_pages}")
    with col_prev:
        if st.button("Trước", key=f"{key}_prev", disabled=page == 0, use_container_width=True):
            st.session_state[page_key] -= 1
            st.rerun()
    with col_next:
        if st.button("Tiếp", key=f"{key}_next", disabled=page >= total_pages - 1, use_container_width=True):
            st.session_state[page_key] += 1
            st.rerun()

    st.dataframe(df.iloc[start:end], use_container_width=True, hide_index=True)


def _render_detail_tables(labor: pd.DataFrame, material: pd.DataFrame) -> None:
    _render_section_title("Bảng chi tiết")
    with st.expander("Chi tiết công việc", expanded=False):
        if labor.empty:
            st.info("Không có dữ liệu nhân công.")
        else:
            grouped = (
                labor.groupby(["farm_code", "doi_code", "lo_code", "cong_doan", "ten_cong_viec"])
                .agg(so_cong=("so_cong", "sum"), thanh_tien=("thanh_tien", "sum"))
                .reset_index()
                .sort_values("thanh_tien", ascending=False)
            )
            display = grouped.rename(columns={
                "farm_code": "Farm",
                "doi_code": "Đội",
                "lo_code": "Lô",
                "cong_doan": "Công đoạn",
                "ten_cong_viec": "Công việc",
                "so_cong": "Số công",
                "thanh_tien": "Thành tiền",
            })
            display["Số công"] = display["Số công"].map(lambda value: f"{value:,.1f}")
            display["Thành tiền"] = display["Thành tiền"].map(lambda value: f"{value:,.0f}")
            _render_paginated_dataframe(display, key="cost_dash_labor_detail")

    with st.expander("Chi tiết vật tư", expanded=False):
        if material.empty:
            st.info("Không có dữ liệu vật tư.")
        else:
            grouped = (
                material.groupby(["farm_code", "lo_code", "loai_vat_tu", "ten_vat_tu"])
                .agg(so_luong=("so_luong", "sum"), thanh_tien=("thanh_tien", "sum"))
                .reset_index()
                .sort_values("thanh_tien", ascending=False)
            )
            display = grouped.rename(columns={
                "farm_code": "Farm",
                "lo_code": "Lô",
                "loai_vat_tu": "Loại vật tư",
                "ten_vat_tu": "Vật tư",
                "so_luong": "Số lượng",
                "thanh_tien": "Thành tiền",
            })
            display["Số lượng"] = display["Số lượng"].map(lambda value: f"{value:,.2f}")
            display["Thành tiền"] = display["Thành tiền"].map(lambda value: f"{value:,.0f}")
            _render_paginated_dataframe(display, key="cost_dash_material_detail")


def render_cost_dashboard(_supabase, current_farm: str, current_team: str) -> None:
    """Render dashboard chi phí raw từ công + vật tư, scoped theo account hiện tại."""
    st.markdown("### Dashboard chi phí")
    st.caption("Số liệu raw từ nhật ký công và vật tư. Popup chi phí/cây trên bản đồ dùng logic clean riêng.")

    farm_rows = _load_dim_farms(_supabase)
    allowed_farms = _resolve_allowed_farms(current_farm, farm_rows)
    if not allowed_farms:
        st.warning("Account này chưa có farm hợp lệ để xem chi phí.")
        return

    allowed_labels = [_farm_label(row) for row in allowed_farms]
    label_to_id = {_farm_label(row): int(row["farm_id"]) for row in allowed_farms if row.get("farm_id") is not None}
    can_select_farms = current_farm in ALL_FARM_ACCOUNTS

    with st.container(border=True):
        filter_cols = st.columns([2, 2, 2, 2])
        with filter_cols[0]:
            if can_select_farms:
                _sanitize_multiselect_state("cost_dash_selected_farms", allowed_labels)
                selected_farm_labels = st.multiselect(
                    "Farm",
                    options=allowed_labels,
                    default=allowed_labels,
                    key="cost_dash_selected_farms",
                    placeholder="Chọn farm",
                )
            else:
                selected_farm_labels = allowed_labels
                st.selectbox("Farm", options=allowed_labels, index=0, disabled=True, key="cost_dash_locked_farm")
        selected_farm_ids = tuple(label_to_id[label] for label in selected_farm_labels if label in label_to_id)
        if not selected_farm_ids:
            st.warning("Chọn ít nhất 1 farm.")
            return

        dims = _load_cost_dimensions(_supabase, selected_farm_ids)
        maps = _build_dim_maps(farm_rows, dims)
        labor_all = _build_labor_frame(_load_cost_labor_rows(_supabase, selected_farm_ids), maps)
        material_all = _build_material_frame(_load_cost_material_rows(_supabase, selected_farm_ids), maps)
        season_df = _build_season_frame(dims, maps)

        all_dates = pd.concat([
            labor_all["ngay_dt"].dropna() if "ngay_dt" in labor_all else pd.Series(dtype="datetime64[ns]"),
            material_all["ngay_dt"].dropna() if "ngay_dt" in material_all else pd.Series(dtype="datetime64[ns]"),
        ], ignore_index=True)
        if all_dates.empty:
            st.info("Chưa có dữ liệu chi phí cho phạm vi này.")
            return

        min_date = all_dates.min().date()
        max_date = all_dates.max().date()
        _sanitize_date_range_state("cost_dash_date_range", min_date, max_date)
        with filter_cols[1]:
            date_range = st.date_input(
                "Khoảng thời gian",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key="cost_dash_date_range",
            )
        if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
            st.info("Chọn đủ ngày bắt đầu và ngày kết thúc.")
            return
        start_date, end_date = date_range
        if start_date > end_date:
            st.error("Ngày bắt đầu phải nhỏ hơn hoặc bằng ngày kết thúc.")
            return

        lots_df = pd.DataFrame(dims.get("lots", []))
        with filter_cols[2]:
            lo_type_opts = sorted([
                str(value) for value in lots_df.get("lo_type", pd.Series(dtype=str)).dropna().unique()
                if str(value).strip()
            ])
            _sanitize_multiselect_state("cost_dash_lo_types", lo_type_opts)
            selected_lo_types = st.multiselect(
                "Loại lô",
                options=lo_type_opts,
                default=lo_type_opts,
                key="cost_dash_lo_types",
                placeholder="Tất cả",
            )
        with filter_cols[3]:
            show_support = st.checkbox("Bao gồm công hỗ trợ", value=True, key="cost_dash_show_support")

        filter_cols2 = st.columns([2, 2, 2])
        lot_opts = sorted(set(labor_all["lo_code"].dropna().astype(str)).union(set(material_all["lo_code"].dropna().astype(str))))
        with filter_cols2[0]:
            _sanitize_multiselect_state("cost_dash_los", lot_opts)
            selected_los = st.multiselect("Lô", options=lot_opts, default=[], key="cost_dash_los", placeholder="Tất cả")
        team_opts = sorted(labor_all["doi_code"].dropna().astype(str).unique()) if not labor_all.empty else []
        with filter_cols2[1]:
            _sanitize_multiselect_state("cost_dash_teams", team_opts)
            selected_dois = st.multiselect("Đội", options=team_opts, default=[], key="cost_dash_teams", placeholder="Tất cả")
        season_labels = season_df["label"].tolist() if not season_df.empty else []
        with filter_cols2[2]:
            _sanitize_multiselect_state("cost_dash_seasons", season_labels)
            selected_season_labels = st.multiselect("Vụ", options=season_labels, default=[], key="cost_dash_seasons", placeholder="Tất cả")
        selected_seasons = season_df[season_df["label"].isin(selected_season_labels)] if selected_season_labels and not season_df.empty else pd.DataFrame()

    labor, material = _apply_cost_filters(
        labor_all,
        material_all,
        start_date=start_date,
        end_date=end_date,
        selected_lo_types=selected_lo_types,
        selected_los=selected_los,
        selected_dois=selected_dois,
        selected_seasons=selected_seasons,
        include_support=show_support,
    )

    if labor.empty and material.empty:
        st.warning("Không có dữ liệu chi phí sau khi áp dụng bộ lọc.")
        return

    _render_kpis(labor, material)
    st.divider()
    _render_monthly_trend(labor, material)
    st.divider()
    _render_overview_charts(labor, material)
    st.divider()
    _render_cost_structure(labor, material)
    st.divider()
    _render_detail_tables(labor, material)
