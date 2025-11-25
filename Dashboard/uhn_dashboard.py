from __future__ import annotations

import io
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
import json
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
try:
    import folium  # type: ignore
    from streamlit_folium import st_folium  # type: ignore
    HAS_FOLIUM = True
except Exception:
    HAS_FOLIUM = False


# ----------------------------- Styles & Shell -----------------------------

def _inject_styles():
    st.markdown(
        """
        <style>
        :root {
          --brand:#0f172a; /* slate-900 for active nav */
          --soft:#f1f5f9;  /* slate-100 */
          --border: rgba(148,163,184,0.32);
        }
        .stApp > header { display: none; }
        .stApp { background: linear-gradient(145deg, #f8fafc 0%, #ffffff 56%, #eef2f7 100%); }
        .shell { max-width: 1180px; margin: 0 auto; padding: 16px 20px 24px; }
        .topbar { position: sticky; top: 0; z-index: 5; background: rgba(255,255,255,0.92); backdrop-filter: blur(8px); border-bottom:1px solid #e5e7eb; }
        .topbar-inner { max-width: 1180px; margin: 0 auto; padding: 12px 20px; display:flex; align-items:center; justify-content:space-between; }
        .brand { display:flex; gap:12px; align-items:center; }
        .brand .icon { width:40px; height:40px; display:grid; place-items:center; border-radius:14px; background:#e0f2fe; color:#0369a1; font-size:18px; }
        .brand h1 { margin:0; font:600 18px/1.2 Inter,ui-sans-serif; color:#0f172a; }
        .brand p { margin:2px 0 0; color:#64748b; font:500 11px/1 Inter; }
        .grid { display:grid; grid-template-columns: 220px 1fr; gap: 16px; margin-top: 16px; }
        .nav { position: sticky; top: 68px; display:flex; flex-direction:column; gap: 10px; }
        .nav button { text-align:left; padding:8px 12px; border:1px solid #e5e7eb; border-radius:12px; background:#fff; color:#0f172a; font:500 13px Inter; }
        .nav button.active { background:#0f172a; color:#fff; border-color:#0f172a; }
        .panel { background:#fff; border:1px solid var(--border); border-radius:16px; padding:16px; }
        .scorecard { border:1px solid #e5e7eb; border-radius:14px; padding:14px; background:#fff; }
        .scoregrid { display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:12px; }
        .gauge-wrap { display:flex; gap:12px; align-items:center; }
        .gauge { width:56px; height:56px; border-radius:50%; display:grid; place-items:center; }
        .gauge-inner { width:42px; height:42px; background:#fff; border-radius:50%; display:grid; place-items:center; font:600 12px Inter; color:#0f172a; }
        .kgrid { display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap:10px; }
        .kitem { background:#f8fafc; border:1px solid #e5e7eb; padding:10px 12px; border-radius:10px; display:flex; align-items:center; justify-content:space-between; font:500 13px Inter; }
        .zonecard { border:1px solid #e5e7eb; border-radius:12px; padding:10px; background:#fff; }
        .zonegrid { display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap:8px; }
        .dot { width:8px; height:8px; border-radius:50%; display:inline-block; }
        .warn { color:#b45309 }
        .ok { color:#065f46 }
        .bad { color:#991b1b }
        .meta { color:#475569; font:500 11px Inter; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _shell_topbar():
    st.markdown(
        """
        <div class="topbar">
          <div class="topbar-inner">
            <div class="brand">
              <div class="icon">💧</div>
              <div>
                <h1>Utility Health Navigator</h1>
                <p>React parity • Tailwind vibe via CSS</p>
              </div>
            </div>
            <div class="meta">Fusion 4 • Challenge W3</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------- Mock Data -----------------------------

DATA_DIR = Path(__file__).resolve().parents[1] / "Data"

def _load_json(name: str) -> Optional[Dict[str, Any]]:
    p = DATA_DIR / name
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return None
    return None

def _filter_df_by_months(df: pd.DataFrame, col: str = "m") -> pd.DataFrame:
    sm = st.session_state.get("start_month")
    em = st.session_state.get("end_month")
    if (sm or em) and col in df.columns:
        try:
            d = pd.to_datetime(df[col], errors="coerce")
            if sm:
                d0 = pd.to_datetime(sm, errors="coerce")
                df = df[d >= d0]
            if em:
                d1 = pd.to_datetime(em, errors="coerce")
                df = df[d <= d1]
        except Exception:
            pass
    return df
def _dq_badge(ok: bool, partial: bool = False) -> str:
    if ok:
        return "<span style='color:#065f46'>Data quality: complete</span>"
    if partial:
        return "<span style='color:#b45309'>Data quality: partial</span>"
    return "<span style='color:#991b1b'>Data quality: missing</span>"

ZONES = [
    {"id": "n", "name": "North", "safeAccess": 58},
    {"id": "s", "name": "South", "safeAccess": 66},
    {"id": "e", "name": "East", "safeAccess": 74},
    {"id": "w", "name": "West", "safeAccess": 49},
    {"id": "c", "name": "Central", "safeAccess": 81},
    {"id": "se", "name": "South-East", "safeAccess": 63},
    {"id": "ne", "name": "North-East", "safeAccess": 71},
    {"id": "nw", "name": "North-West", "safeAccess": 55},
]

SERVICE_LADDER = [
    {"zone": "North", "safely_managed": 41, "basic": 28, "limited": 18, "unimproved": 9, "open_defecation": 4},
    {"zone": "South", "safely_managed": 45, "basic": 31, "limited": 14, "unimproved": 7, "open_defecation": 3},
    {"zone": "East", "safely_managed": 52, "basic": 29, "limited": 12, "unimproved": 5, "open_defecation": 2},
    {"zone": "West", "safely_managed": 33, "basic": 26, "limited": 23, "unimproved": 12, "open_defecation": 6},
    {"zone": "Central", "safely_managed": 64, "basic": 22, "limited": 8, "unimproved": 4, "open_defecation": 2},
]

PROGRESS = [
    {"m": "Jan", "v": 56},
    {"m": "Feb", "v": 57},
    {"m": "Mar", "v": 58},
    {"m": "Apr", "v": 58},
    {"m": "May", "v": 59},
    {"m": "Jun", "v": 60},
]

WQ_MONTHLY = [
    {"m": "Jan", "v": 95},
    {"m": "Feb", "v": 93},
    {"m": "Mar", "v": 96},
    {"m": "Apr", "v": 92},
    {"m": "May", "v": 94},
    {"m": "Jun", "v": 97},
]

BLOCKAGES = [
    {"m": "Jan", "v": 16}, {"m": "Feb", "v": 14}, {"m": "Mar", "v": 12},
    {"m": "Apr", "v": 10}, {"m": "May", "v": 13}, {"m": "Jun", "v": 11}
]

COMPLAINTS_VS_INTERRUP = [
    {"zone": "North", "complaints": 120, "interruptions": 15},
    {"zone": "South", "complaints": 90, "interruptions": 11},
    {"zone": "East", "complaints": 80, "interruptions": 9},
    {"zone": "West", "complaints": 150, "interruptions": 18},
    {"zone": "Central", "complaints": 70, "interruptions": 7},
]

REVENUE_OPEX = [
    {"year": 2020, "revenue": 98, "opex": 102, "coverage": 96},
    {"year": 2021, "revenue": 110, "opex": 108, "coverage": 102},
    {"year": 2022, "revenue": 118, "opex": 114, "coverage": 104},
    {"year": 2023, "revenue": 120, "opex": 118, "coverage": 102},
    {"year": 2024, "revenue": 130, "opex": 122, "coverage": 107},
]

NRW_COLLECTION = [
    {"year": 2020, "nrw": 42, "collection": 89},
    {"year": 2021, "nrw": 39, "collection": 90},
    {"year": 2022, "nrw": 37, "collection": 91},
    {"year": 2023, "nrw": 35, "collection": 92},
    {"year": 2024, "nrw": 33, "collection": 93},
]

FINANCIALS_TABLE = [
    {"metric": "Collection Efficiency %", "value": 92},
    {"metric": "Cost Coverage %", "value": 107},
    {"metric": "NRW %", "value": 33},
    {"metric": "Working Ratio", "value": 0.87},
    {"metric": "Tariff Gap %", "value": 8},
]


# ----------------------------- Utilities -----------------------------

def _conic_css(value: int, good_color: str = "#10b981", soft_color: str = "#e2e8f0") -> str:
    angle = max(0, min(100, int(value))) * 3.6
    return f"background: conic-gradient({good_color} {angle}deg, {soft_color} {angle}deg);"


def _download_button(filename: str, rows: List[dict], label: str = "Export CSV"):
    if not rows:
        return
    df = pd.DataFrame(rows)
    data = df.to_csv(index=False).encode("utf-8")
    st.download_button(label, data=data, file_name=filename, mime="text/csv")


# ----------------------------- Scenes -----------------------------

def _scene_page_path(scene_key: str) -> Optional[str]:
    mapping = {
        "exec": "Home.py",
        "access": "pages/2_🗺️_Access_&_Coverage.py",
        "quality": "pages/3_🛠️_Service_Quality_&_Reliability.py",
        "finance": "pages/4_💹_Financial_Health.py",
        "production": "pages/5_♻️_Production.py",
    }
    return mapping.get(scene_key)

def scene_executive(go_to):
    st.markdown("<div class='panel warn'>Coverage progressing slower than plan in 2 zones; review pipeline projects.</div>", unsafe_allow_html=True)

    es = _load_json("executive_summary.json") or {
        "month": "2025-08",
        "water_safe_pct": 59,
        "san_safe_pct": 31,
        "collection_eff_pct": 94,
        "om_coverage_pct": 98,
        "nrw_pct": 44,
        "asset_health_idx": 72,
        "hours_per_day": 20.3,
        "dwq_pct": 96,
    }

    scorecards = [
        {"label": "Safely Managed Water", "value": es["water_safe_pct"], "target": 60, "scene": "access", "delta": +1.4},
        {"label": "Safely Managed Sanitation", "value": es["san_safe_pct"], "target": 70, "scene": "access", "delta": +0.8},
        {"label": "Collection Efficiency", "value": es["collection_eff_pct"], "target": 95, "scene": "finance", "delta": +2.1},
        {"label": "O&M Coverage", "value": es["om_coverage_pct"], "target": 150, "scene": "finance", "delta": +0.6},
        {"label": "NRW", "value": es["nrw_pct"], "target": 25, "scene": "finance", "delta": -0.6},
    ]
    st.markdown("<div class='scoregrid'>", unsafe_allow_html=True)
    cols = st.columns(4)
    for i, sc in enumerate(scorecards[:4]):
        with cols[i % 4]:
            gauge_style = _conic_css(sc["value"]) if sc.get("target") is None else _conic_css(sc["value"], "#10b981" if sc["value"] >= sc["target"] else "#f59e0b")
            st.markdown(
                f"""
                <div class='scorecard'>
                  <div class='gauge-wrap'>
                    <div class='gauge' style="{gauge_style}"><div class='gauge-inner'>{sc['value']}%</div></div>
                    <div>
                      <div style='font:600 13px Inter;color:#0f172a'>{sc['label']}</div>
                      <div class='meta'>Target: {sc['target']}% • Δ {abs(sc.get('delta',0))}%</div>
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            target = _scene_page_path(sc["scene"])
            if target:
                st.page_link(target, label="View details →", icon=None)
    st.markdown("</div>", unsafe_allow_html=True)

    # Second row gauges
    row2 = [
        {"label": "Asset Health Index", "value": es["asset_health_idx"], "target": 80, "scene": "finance"},
        {"label": "Hours of Supply", "value": es["hours_per_day"], "target": 22, "scene": "quality"},
        {"label": "DWQ", "value": es["dwq_pct"], "target": 95, "scene": "quality"},
    ]
    cols2 = st.columns(3)
    for i, sc in enumerate(row2):
        with cols2[i % 3]:
            unit = "%" if sc["label"] != "Hours of Supply" else "h/d"
            val = sc["value"] if unit == "%" else round(sc["value"], 1)
            gauge_style = _conic_css(sc["value"] if unit == "%" else min(100, sc["value"]*4))
            st.markdown(
                f"""
                <div class='scorecard'>
                  <div class='gauge-wrap'>
                    <div class='gauge' style="{gauge_style}"><div class='gauge-inner'>{val}{unit}</div></div>
                    <div>
                      <div style='font:600 13px Inter;color:#0f172a'>{sc['label']}</div>
                      <div class='meta'>Target: {sc['target']}{unit}</div>
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            target = _scene_page_path(sc["scene"])
            if target:
                st.page_link(target, label="View details →", icon=None)

    left, right = st.columns(2)
    with left:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div style='display:flex;align-items:center;justify-content:space-between'><h3>Quick Stats</h3>", unsafe_allow_html=True)
        quick_stats = [
            {"metric": "Population Served", "value": "1.2M"},
            {"metric": "Active Connections", "value": "198k"},
            {"metric": "Active Staff", "value": "512"},
            {"metric": "Staff per 1k Conns", "value": "6.4"},
        ]
        _download_button("quick-stats.csv", quick_stats)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div class='kgrid'>", unsafe_allow_html=True)
        for row in quick_stats:
            st.markdown(
                f"<div class='kitem'><span>{row['metric']}</span><span>{row['value']}</span></div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div></div>", unsafe_allow_html=True)

    with right:
        recent = [
            {"when": "Today 10:12", "activity": "Zone West below DWQ target for May"},
            {"when": "Yesterday", "activity": "Tariff review submitted to regulator"},
            {"when": "2 days ago", "activity": "NRW taskforce created for Zone North"},
        ]
        st.markdown("<div class='panel'><h3>Recent Activity</h3>", unsafe_allow_html=True)
        _download_button("recent-activity.csv", recent)
        st.table(pd.DataFrame(recent))
        st.markdown("</div>", unsafe_allow_html=True)
@st.cache_data
def load_csv_data() -> Dict[str, pd.DataFrame]:
    """
    Read sewer and water access CSV datasets from disk and cache the resulting DataFrames.
    """
    csv_map = {
        "sewer": "Sewer Access Data.csv",
        "water": "Water Access Data.csv",
    }
    frames: Dict[str, pd.DataFrame] = {}
    for key, filename in csv_map.items():
        path = DATA_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        frames[key] = pd.read_csv(path)
    return frames


def _normalise_access_df(df: pd.DataFrame, *, prefix: str, extra_pct_cols: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Clean up access data: trim text, coerce numeric percentage columns, and ensure year is numeric.
    """
    frame = df.copy()
    if "zone" in frame.columns:
        frame["zone"] = frame["zone"].astype(str).str.strip()
    if "country" in frame.columns:
        frame["country"] = frame["country"].astype(str).str.strip()
    if "year" in frame.columns:
        frame["year"] = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")
    pct_cols = [col for col in frame.columns if col.startswith(prefix) and col.endswith("_pct")]
    if extra_pct_cols:
        pct_cols.extend(col for col in extra_pct_cols if col in frame.columns)
    for col in pct_cols:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame


def _latest_snapshot(
    df: pd.DataFrame,
    *,
    rename_map: Dict[str, str],
    additional_columns: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Return the most recent record per (country, zone) pair and rename columns for clarity.
    """
    keys = [col for col in ("country", "zone") if col in df.columns]
    if not keys:
        keys = ["zone"]
    if "year" in df.columns:
        idx = df.groupby(keys)["year"].idxmax()
        latest = df.loc[idx].copy()
    else:
        latest = df.drop_duplicates(keys, keep="last").copy()
    keep_cols = set(keys + ["year"] + list(rename_map.keys()))
    if additional_columns:
        keep_cols.update(additional_columns)
    available_cols = [col for col in keep_cols if col in latest.columns]
    latest = latest[available_cols]
    latest = latest.rename(columns=rename_map)
    return latest


def _zone_identifier(country: Optional[str], zone: Optional[str]) -> str:
    base = f"{country or 'na'}-{zone or 'zone'}".lower()
    return re.sub(r"[^a-z0-9]+", "-", base).strip("-") or "zone"


@st.cache_data
def _prepare_access_data() -> Dict[str, Any]:
    """
    Prepare derived access datasets for the Access & Coverage scene.
    Returns cached water/sewer snapshots, full histories, and zone-level summaries.
    """
    csv_data = load_csv_data()
    water_df = _normalise_access_df(csv_data["water"], prefix="w_", extra_pct_cols=["municipal_coverage"])
    sewer_df = _normalise_access_df(csv_data["sewer"], prefix="s_")

    water_latest = _latest_snapshot(
        water_df,
        rename_map={
            "year": "water_year",
            "w_safely_managed_pct": "water_safely_pct",
            "w_basic_pct": "water_basic_pct",
            "w_limited_pct": "water_limited_pct",
            "w_unimproved_pct": "water_unimproved_pct",
            "surface_water_pct": "water_surface_pct",
            "municipal_coverage": "water_municipal_coverage",
        },
        additional_columns=["municipal_coverage", "w_safely_managed", "w_basic", "w_limited", "w_unimproved", "surface_water"],
    )
    sewer_latest = _latest_snapshot(
        sewer_df,
        rename_map={
            "year": "sewer_year",
            "s_safely_managed_pct": "sewer_safely_pct",
            "s_basic_pct": "sewer_basic_pct",
            "s_limited_pct": "sewer_limited_pct",
            "s_unimproved_pct": "sewer_unimproved_pct",
            "open_def_pct": "sewer_open_def_pct",
        },
        additional_columns=["s_safely_managed", "s_basic", "s_limited", "s_unimproved", "open_def"],
    )

    merge_keys = [col for col in ("country", "zone") if col in water_latest.columns and col in sewer_latest.columns]
    if not merge_keys:
        merge_keys = ["zone"]
    zones_df = water_latest.merge(sewer_latest, on=merge_keys, how="outer", suffixes=("", "_dup"))
    if "country_dup" in zones_df.columns and "country" not in merge_keys:
        zones_df["country"] = zones_df["country"].fillna(zones_df["country_dup"])
        zones_df = zones_df.drop(columns=["country_dup"])
    zones_df["safeAccess"] = zones_df[["water_safely_pct", "sewer_safely_pct"]].mean(axis=1, skipna=True)
    zone_records: List[Dict[str, Any]] = []
    for _, row in zones_df.sort_values(by=[col for col in ("country", "zone") if col in zones_df.columns]).iterrows():
        record = {
            "id": _zone_identifier(row.get("country"), row.get("zone")),
            "name": row.get("zone"),
            "country": row.get("country"),
            "safeAccess": float(row["safeAccess"]) if pd.notna(row.get("safeAccess")) else None,
            "water_safely_pct": float(row["water_safely_pct"]) if pd.notna(row.get("water_safely_pct")) else None,
            "sewer_safely_pct": float(row["sewer_safely_pct"]) if pd.notna(row.get("sewer_safely_pct")) else None,
            "water_year": int(row["water_year"]) if pd.notna(row.get("water_year")) else None,
            "sewer_year": int(row["sewer_year"]) if pd.notna(row.get("sewer_year")) else None,
        }
        zone_records.append(record)

    return {
        "water_full": water_df,
        "sewer_full": sewer_df,
        "water_latest": water_latest,
        "sewer_latest": sewer_latest,
        "zones": zone_records,
    }

def scene_access():
    access_data = _prepare_access_data()
    zones_records = [z for z in access_data["zones"] if z.get("name")]
    if not zones_records:
        zones_records = [dict(z) for z in ZONES]
    zone_lookup = {z["name"].lower(): z for z in zones_records if z.get("name")}

    selected_zone = st.session_state.get("selected_zone")
    if selected_zone and selected_zone.get("name"):
        selected_match = zone_lookup.get(selected_zone["name"].lower())
        if selected_match:
            st.session_state["selected_zone"] = selected_match
            selected_zone = selected_match
        else:
            selected_zone = None
    else:
        selected_zone = None

    def _to_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            val = float(value)
        except (TypeError, ValueError):
            return None
        return None if pd.isna(val) else val

    def _filter_zone(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or not selected_zone or not selected_zone.get("name") or "zone" not in df.columns:
            return df
        name = selected_zone["name"].lower()
        filtered = pd.DataFrame()
        if "country" in df.columns and selected_zone.get("country"):
            country_mask = df["country"].str.lower() == selected_zone["country"].lower()
            filtered = df[country_mask & (df["zone"].str.lower() == name)]
        if filtered.empty:
            filtered = df[df["zone"].str.lower() == name]
        return filtered.copy() if not filtered.empty else df

    def _access_color(value: Optional[float]) -> str:
        if value is None:
            return "#94a3b8"
        if value >= 80:
            return "#10b981"
        if value >= 60:
            return "#f59e0b"
        return "#ef4444"

    def _format_pct(value: Optional[float], *, digits: int = 1, suffix: str = "%") -> str:
        val = _to_float(value)
        if val is None:
            return "N/A"
        return f"{val:.{digits}f}{suffix}"

    water_latest = access_data["water_latest"]
    sewer_latest = access_data["sewer_latest"]
    water_full = access_data["water_full"]

    water_latest_sel = _filter_zone(water_latest)
    sewer_latest_sel = _filter_zone(sewer_latest)
    water_history_sel = _filter_zone(water_full)

    safe_values: List[float] = []
    for zone in zones_records:
        val = _to_float(zone.get("safeAccess"))
        if val is not None:
            safe_values.append(val)
    avg_safe = sum(safe_values) / len(safe_values) if safe_values else 0.0
    current_value = _to_float(selected_zone.get("safeAccess")) if selected_zone else None
    if current_value is None:
        current_value = avg_safe

    # Left column: zones and gap panel
    l, r = st.columns([1, 2])

    with l:
        st.markdown("<div class='panel'><h3>Zones Map</h3>", unsafe_allow_html=True)
        if HAS_FOLIUM:
            selected_name = _render_zone_map_overlay(
                geojson_path="Data/zones.geojson",
                id_property="id",
                name_property="name",
                metric_property="safeAccess",
                key="zones_map_access",
            )
            if selected_name:
                match = zone_lookup.get(selected_name.lower())
                if match:
                    st.session_state["selected_zone"] = match
                    selected_zone = match

        st.markdown("<div class='zonegrid'>", unsafe_allow_html=True)
        cols = st.columns(2)
        for i, zone in enumerate(zones_records):
            with cols[i % 2]:
                safe_val = _to_float(zone.get("safeAccess"))
                color = _access_color(safe_val)
                highlight = "border:2px solid #0f172a;" if selected_zone and selected_zone.get("id") == zone.get("id") else ""
                safe_label = f"{safe_val:.1f}%" if safe_val is not None else "N/A"
                fill_pct = max(0.0, min(100.0, safe_val if safe_val is not None else 0.0))
                st.markdown(
                    f"<div class='zonecard' style='{highlight}'><div style='display:flex;justify-content:space-between;align-items:center'><span style='font:600 12px Inter'>{zone.get('name')}</span><span class='dot' style='background:{color}'></span></div><div style='height:8px;background:#f1f5f9;border-radius:6px;margin-top:8px'><div style='height:8px;width:{fill_pct}%;background:{color};border-radius:6px'></div></div><div class='meta'>Safe access: {safe_label}</div></div>",
                    unsafe_allow_html=True,
                )
                st.button(
                    "Select",
                    key=f"select_zone_{zone.get('id') or i}",
                    on_click=lambda record=zone: st.session_state.update({"selected_zone": record}),
                    use_container_width=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='panel'><h3>Gap to Target</h3>", unsafe_allow_html=True)
        target = 80.0
        st.metric("Current", f"{current_value:.1f}%")
        st.metric("Target", f"{target:.0f}%")
        st.metric("Gap", f"{max(0.0, target - current_value):.1f}%")
        proj = st.slider("Projection (+% over next 12 months)", 0, 10, 0)
        st.caption(f"Projected safely managed: {min(100.0, current_value + proj):.1f}%")
        st.markdown("</div>", unsafe_allow_html=True)

    with r:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div style='display:flex;align-items:center;justify-content:space-between'><h3>Service Ladders</h3>", unsafe_allow_html=True)

        water_ladder_map = {
            "surface": "water_surface_pct",
            "unimproved": "water_unimproved_pct",
            "limited": "water_limited_pct",
            "basic": "water_basic_pct",
            "safely": "water_safely_pct",
        }
        sewer_ladder_map = {
            "open_def": "sewer_open_def_pct",
            "unimproved": "sewer_unimproved_pct",
            "limited": "sewer_limited_pct",
            "basic": "sewer_basic_pct",
            "safely": "sewer_safely_pct",
        }

        def _build_ladder_frame(src: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
            if src.empty:
                return pd.DataFrame(columns=["zone"] + list(mapping.keys()))
            records: List[Dict[str, Any]] = []
            for _, row in src.iterrows():
                entry: Dict[str, Any] = {"zone": row.get("zone")}
                for out_col, source_col in mapping.items():
                    entry[out_col] = _to_float(row.get(source_col))
                records.append(entry)
            frame = pd.DataFrame(records)
            if "zone" in frame.columns:
                frame["zone"] = frame["zone"].fillna("Unknown").astype(str)
                frame = frame.groupby("zone", as_index=False).first()
            ordered_cols = ["zone"] + [col for col in mapping.keys() if col in frame.columns]
            return frame[ordered_cols]

        df_water = _build_ladder_frame(water_latest_sel, water_ladder_map)
        df_san = _build_ladder_frame(sewer_latest_sel, sewer_ladder_map)

        _download_button("service-ladder-water.csv", df_water.to_dict(orient="records"))
        _download_button("service-ladder-sanitation.csv", df_san.to_dict(orient="records"))
        st.markdown("</div>", unsafe_allow_html=True)

        fig_w = go.Figure()
        water_order = ["surface", "unimproved", "limited", "basic", "safely"]
        water_colors = {"surface": "#9ca3af", "unimproved": "#a3a3a3", "limited": "#f59e0b", "basic": "#60a5fa", "safely": "#10b981"}
        xw = df_water["zone"].tolist()
        base = [0.0] * len(xw)
        for key in water_order:
            if key in df_water.columns:
                values = df_water[key].fillna(0).tolist()
                fig_w.add_bar(x=xw, y=values, name=key.replace("_", " ").title(), marker_color=water_colors[key], base=base)
                base = [b + v for b, v in zip(base, values)]
        fig_w.update_layout(barmode="stack", margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_w, use_container_width=True, config={"displayModeBar": False}, key="access_water_ladder")
        water_year = None
        if "water_year" in water_latest_sel.columns and not water_latest_sel["water_year"].dropna().empty:
            water_year = int(water_latest_sel["water_year"].dropna().iloc[0])
        st.caption(f"Water ladder • Water Access Data ({water_year})" if water_year else "Water ladder • Water Access Data")

        fig_s = go.Figure()
        san_order = ["open_def", "unimproved", "limited", "basic", "safely"]
        san_colors = {"open_def": "#ef4444", "unimproved": "#a3a3a3", "limited": "#f59e0b", "basic": "#60a5fa", "safely": "#10b981"}
        xs = df_san["zone"].tolist()
        base = [0.0] * len(xs)
        for key in san_order:
            if key in df_san.columns:
                values = df_san[key].fillna(0).tolist()
                fig_s.add_bar(x=xs, y=values, name=key.replace("_", " ").title(), marker_color=san_colors[key], base=base)
                base = [b + v for b, v in zip(base, values)]
        fig_s.update_layout(barmode="stack", margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_s, use_container_width=True, config={"displayModeBar": False}, key="access_san_ladder")
        sewer_year = None
        if "sewer_year" in sewer_latest_sel.columns and not sewer_latest_sel["sewer_year"].dropna().empty:
            sewer_year = int(sewer_latest_sel["sewer_year"].dropna().iloc[0])
        st.caption(f"Sanitation ladder • Sewer Access Data ({sewer_year})" if sewer_year else "Sanitation ladder • Sewer Access Data")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div style='display:flex;align-items:center;justify-content:space-between'><h3>Coverage Dynamics</h3>", unsafe_allow_html=True)
        cols_dyn = st.columns(3)

        water_cov_pct = None
        if "water_municipal_coverage" in water_latest_sel.columns:
            cov_series = water_latest_sel["water_municipal_coverage"].dropna()
            if not cov_series.empty:
                water_cov_pct = float(cov_series.mean())
        if water_cov_pct is None and "water_safely_pct" in water_latest_sel.columns:
            cov_series = water_latest_sel["water_safely_pct"].dropna()
            if not cov_series.empty:
                water_cov_pct = float(cov_series.mean())

        sewered_pct = None
        if "sewer_safely_pct" in sewer_latest_sel.columns:
            sewer_series = sewer_latest_sel["sewer_safely_pct"].dropna()
            if not sewer_series.empty:
                sewered_pct = float(sewer_series.mean())

        if "year" in water_history_sel.columns and "w_safely_managed_pct" in water_history_sel.columns:
            water_timeseries = (
                water_history_sel.dropna(subset=["year"])
                .sort_values("year")
                .groupby("year")["w_safely_managed_pct"]
                .mean()
                .reset_index(name="water_safe_pct")
            )
        else:
            water_timeseries = pd.DataFrame(columns=["year", "water_safe_pct"])

        growth_water_pct: Optional[float] = None
        if not water_timeseries.empty:
            water_timeseries["year"] = water_timeseries["year"].astype(int)
            if len(water_timeseries) >= 2:
                growth_water_pct = float(water_timeseries["water_safe_pct"].iloc[-1] - water_timeseries["water_safe_pct"].iloc[-2])
            else:
                growth_water_pct = 0.0

        cols_dyn[0].metric("Water coverage %", _format_pct(water_cov_pct))
        cols_dyn[1].metric("Sewered %", _format_pct(sewered_pct))
        growth_display = "N/A" if growth_water_pct is None else f"{growth_water_pct:+.1f} pp"
        cols_dyn[2].metric("Growth water %", growth_display)

        fig2 = go.Figure()
        if not water_timeseries.empty:
            fig2.add_trace(
                go.Scatter(
                    x=water_timeseries["year"],
                    y=water_timeseries["water_safe_pct"],
                    mode="lines+markers",
                    name="Safely managed water %",
                    line=dict(color="#0ea5e9", width=2),
                )
            )
        fig2.update_layout(margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Year", yaxis_title="Safely managed water %")
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False}, key="access_coverage_spark")
        st.markdown("</div>", unsafe_allow_html=True)

def scene_quality():
    # Zone filter
    # rely on sidebar zone

    l, r = st.columns(2)
    with l:
        st.markdown("<div class='panel'><h3>Water Quality Compliance</h3>", unsafe_allow_html=True)
        sq = _load_json("service_quality.json") or None
        if sq:
            df = pd.DataFrame({"m": sq["months"], "v": sq["dwq_pct"]})
        else:
            df = pd.DataFrame(WQ_MONTHLY)
        df = _filter_df_by_months(df, "m")
        target = 95
        fig = px.line(df, x="m", y="v")
        fig.add_hline(y=target, line_dash="dot", line_color="#ef4444")
        fig.update_traces(mode="lines+markers")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="quality_wq_line")
        below = df[df["v"] < target]["m"].tolist()
        if below:
            sel = st.selectbox("Below-target month", below, index=0)
            st.info(f"Details for {sel}: DWQ {df.set_index('m').loc[sel, 'v']}% < target {target}% • Root cause placeholder • Actions placeholder")
        st.markdown("</div>", unsafe_allow_html=True)
    with r:
        st.markdown("<div class='panel'><h3>Sewer Blockages</h3>", unsafe_allow_html=True)
        unit_choice = st.session_state.get("blockage_basis", "per 100 km")
        if sq and "blockages_per_100km" in sq and unit_choice == "per 100 km":
            dfb = pd.DataFrame({"m": sq["months"], "v": sq["blockages_per_100km"]})
        elif sq and unit_choice == "per 1000 connections" and "blockages_per_1000conn" in sq:
            dfb = pd.DataFrame({"m": sq["months"], "v": sq["blockages_per_1000conn"]})
        else:
            dfb = pd.DataFrame(BLOCKAGES)
            if unit_choice == "per 1000 connections":
                st.caption("Data not available for per 1000 connections; showing per 100 km")
        dfb = _filter_df_by_months(dfb, "m")
        figb = px.bar(dfb, x="m", y="v", color_discrete_sequence=["#f59e0b"])
        st.plotly_chart(figb, use_container_width=True, config={"displayModeBar": False}, key="quality_blockages")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='panel'><h3>Hours & Consumption</h3>", unsafe_allow_html=True)
    if sq:
        dfh = pd.DataFrame({"m": sq["months"], "hours": sq["hours"], "lcd": sq.get("lcd", [])})
        dfh = _filter_df_by_months(dfh, "m")
        figh = go.Figure()
        figh.add_trace(go.Scatter(x=dfh["m"], y=dfh["hours"], mode="lines", name="Hours/day", line=dict(color="#60a5fa", width=2)))
        if len(dfh.get("lcd", [])) == len(dfh["m"]):
            figh.add_trace(go.Scatter(x=dfh["m"], y=dfh["lcd"], mode="lines", name="l/c/d", yaxis="y2", line=dict(color="#10b981", width=2)))
            figh.update_layout(yaxis2=dict(overlaying='y', side='right'))
        st.plotly_chart(figh, use_container_width=True, config={"displayModeBar": False}, key="quality_hours_lcd")
    else:
        dfs = pd.DataFrame(COMPLAINTS_VS_INTERRUP)
        figs = px.scatter(dfs, x="interruptions", y="complaints", hover_name="zone")
        st.plotly_chart(figs, use_container_width=True, config={"displayModeBar": False}, key="quality_scatter")
    st.markdown("</div>", unsafe_allow_html=True)


def scene_finance():
    """
    Enhanced Financial Dashboard - Comprehensive Financial Analysis

    Features:
    - Import national and financial service data
    - Advanced billing, debt, and financial analysis
    - Interactive filters by country, city, date range
    - Export filtered/analyzed data
    - Upload custom data functionality
    """

    # Custom CSS
    st.markdown("""
    <style>
        .panel {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .metric-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            height: 100%;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }
        .status-good { background: #d1fae5; color: #065f46; }
        .status-warning { background: #fed7aa; color: #92400e; }
        .status-critical { background: #fee2e2; color: #991b1b; }
        .upload-section {
            background: #f9fafb;
            border: 2px dashed #d1d5db;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .filter-section {
            background: #f3f4f6;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }
        .info-box {
            background: #eff6ff;
            border-left: 4px solid #3b82f6;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
        }
        .success-box {
            background: #d1fae5;
            border-left: 4px solid #10b981;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
        }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.title("💰 Water Utility Financial Dashboard - Enhanced")
    st.markdown("**Comprehensive Financial Analysis with Real Data Integration**")

    # ============================================================================
    # DATA IMPORT SECTION
    # ============================================================================

    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.subheader("📁 Data Import")

    # Initialize session state for data
    if 'national_data' not in st.session_state:
        st.session_state.national_data = None
    if 'fin_service_data' not in st.session_state:
        st.session_state.fin_service_data = None

    # Tab for different import methods
    import_tab1, import_tab2 = st.tabs(["📤 Upload Files", "📋 Use Default Data"])

    with import_tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**National Budget Data**")
            national_file = st.file_uploader(
                "Upload National Data CSV", 
                type=['csv', 'xlsx'],
                key="national_upload",
                help="Required columns: country, city, date_YY, budget_allocated, san_allocation, wat_allocation, staff_cost, etc."
            )

            if national_file:
                try:
                    if national_file.name.endswith('.csv'):
                        st.session_state.national_data = pd.read_csv(national_file)
                    else:
                        st.session_state.national_data = pd.read_excel(national_file)
                    st.success(f"✓ Loaded {len(st.session_state.national_data)} national records")
                except Exception as e:
                    st.error(f"Error loading national data: {e}")

        with col2:
            st.markdown("**Financial Service Data**")
            fin_service_file = st.file_uploader(
                "Upload Financial Service CSV",
                type=['csv', 'xlsx'],
                key="fin_service_upload",
                help="Required columns: country, city, date_MMYY, sewer_billed, sewer_revenue, opex, complaints, resolved, etc."
            )

            if fin_service_file:
                try:
                    if fin_service_file.name.endswith('.csv'):
                        st.session_state.fin_service_data = pd.read_csv(fin_service_file)
                    else:
                        st.session_state.fin_service_data = pd.read_excel(fin_service_file)
                    st.success(f"✓ Loaded {len(st.session_state.fin_service_data)} service records")
                except Exception as e:
                    st.error(f"Error loading financial service data: {e}")

    with import_tab2:
        st.info("📌 Using default demonstration data (Cameroon - Yaounde)")
        if st.button("Load Default Data"):
            # Load default data from the provided files
            try:
                st.session_state.national_data = pd.read_csv('Master_Data_DontEdit.xlsx-all_national.csv')
                st.session_state.fin_service_data = pd.read_csv('Master_Data_DontEdit.xlsx-all_fin_service.csv')
                st.success(f"✓ Loaded {len(st.session_state.national_data)} national records and {len(st.session_state.fin_service_data)} service records")
            except Exception as e:
                st.error(f"Error loading default data: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

    # Check if data is loaded
    if st.session_state.national_data is None or st.session_state.fin_service_data is None:
        st.warning("⚠️ Please upload data files or load default data to continue")
        return

    # Get data from session state
    national_df = st.session_state.national_data.copy()
    fin_service_df = st.session_state.fin_service_data.copy()

    # ============================================================================
    # DATA PREPROCESSING
    # ============================================================================

    # Convert date columns
    try:
        fin_service_df['date_parsed'] = pd.to_datetime(fin_service_df['date_MMYY'], format='%b/%y', errors='coerce')
        fin_service_df['year'] = fin_service_df['date_parsed'].dt.year
        fin_service_df['month'] = fin_service_df['date_parsed'].dt.month
        fin_service_df['month_name'] = fin_service_df['date_parsed'].dt.strftime('%B')
    except:
        st.warning("Date parsing issue - some date features may not work")

    # Calculate derived metrics
    fin_service_df['collection_rate'] = (fin_service_df['sewer_revenue'] / fin_service_df['sewer_billed'] * 100).fillna(0)
    fin_service_df['debt'] = fin_service_df['sewer_billed'] - fin_service_df['sewer_revenue']
    fin_service_df['complaint_resolution_rate'] = (fin_service_df['resolved'] / fin_service_df['complaints'] * 100).fillna(0)
    fin_service_df['cost_recovery_ratio'] = (fin_service_df['sewer_revenue'] / fin_service_df['opex'] * 100).fillna(0)
    fin_service_df['total_staff'] = fin_service_df['san_staff'] + fin_service_df['w_staff']
    fin_service_df['revenue_per_staff'] = fin_service_df['sewer_revenue'] / fin_service_df['total_staff']

    # ============================================================================
    # FILTER SECTION
    # ============================================================================

    st.markdown('<div class="filter-section">', unsafe_allow_html=True)
    st.subheader("🔍 Data Filters")

    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

    with filter_col1:
        countries = ['All'] + sorted(national_df['country'].unique().tolist())
        selected_country = st.selectbox("Country", countries)

    with filter_col2:
        if selected_country != 'All':
            cities = ['All'] + sorted(national_df[national_df['country'] == selected_country]['city'].unique().tolist())
        else:
            cities = ['All'] + sorted(national_df['city'].unique().tolist())
        selected_city = st.selectbox("City", cities)

    with filter_col3:
        years = sorted(national_df['date_YY'].unique().tolist())
        year_range = st.select_slider("Year Range", options=years, value=(min(years), max(years)))

    with filter_col4:
        if 'month' in fin_service_df.columns:
            months = ['All'] + list(range(1, 13))
            selected_month = st.selectbox("Month", months, format_func=lambda x: 'All' if x == 'All' else pd.to_datetime(f'2020-{x}-01').strftime('%B'))
        else:
            selected_month = 'All'

    st.markdown('</div>', unsafe_allow_html=True)

    # Apply filters
    national_filtered = national_df.copy()
    fin_service_filtered = fin_service_df.copy()

    if selected_country != 'All':
        national_filtered = national_filtered[national_filtered['country'] == selected_country]
        fin_service_filtered = fin_service_filtered[fin_service_filtered['country'] == selected_country]

    if selected_city != 'All':
        national_filtered = national_filtered[national_filtered['city'] == selected_city]
        fin_service_filtered = fin_service_filtered[fin_service_filtered['city'] == selected_city]

    national_filtered = national_filtered[
        (national_filtered['date_YY'] >= year_range[0]) & 
        (national_filtered['date_YY'] <= year_range[1])
    ]

    if 'year' in fin_service_filtered.columns:
        fin_service_filtered = fin_service_filtered[
            (fin_service_filtered['year'] >= year_range[0]) & 
            (fin_service_filtered['year'] <= year_range[1])
        ]

    if selected_month != 'All' and 'month' in fin_service_filtered.columns:
        fin_service_filtered = fin_service_filtered[fin_service_filtered['month'] == selected_month]

    # Display filter summary
    st.info(f"📊 Viewing: **{len(national_filtered)}** national records, **{len(fin_service_filtered)}** service records")

    # ============================================================================
    # KEY METRICS DASHBOARD
    # ============================================================================

    st.markdown("---")
    st.subheader("📈 Key Financial Metrics")

    # Calculate aggregate metrics
    total_budget = national_filtered['budget_allocated'].sum()
    total_billed = fin_service_filtered['sewer_billed'].sum()
    total_revenue = fin_service_filtered['sewer_revenue'].sum()
    total_debt = fin_service_filtered['debt'].sum()
    avg_collection_rate = fin_service_filtered['collection_rate'].mean()
    total_opex = fin_service_filtered['opex'].sum()

    metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)

    with metric_col1:
        st.metric("Total Budget", f"${total_budget/1e9:.2f}B", help="Total allocated budget")

    with metric_col2:
        st.metric("Total Billed", f"${total_billed/1e9:.2f}B", help="Total amount billed to customers")

    with metric_col3:
        st.metric("Revenue Collected", f"${total_revenue/1e9:.2f}B", help="Total revenue collected")

    with metric_col4:
        collection_status = "🟢" if avg_collection_rate >= 80 else "🟡" if avg_collection_rate >= 60 else "🔴"
        st.metric("Collection Rate", f"{avg_collection_rate:.1f}%", delta=f"{collection_status}")

    with metric_col5:
        st.metric("Outstanding Debt", f"${total_debt/1e9:.2f}B", delta="Monitor", delta_color="inverse")

    # ============================================================================
    # BILLING ANALYSIS
    # ============================================================================

    st.markdown("---")
    st.subheader("💵 Billing Analysis")

    billing_tab1, billing_tab2, billing_tab3 = st.tabs(["📊 Billing Trends", "🏦 Revenue vs Costs", "📉 Collection Performance"])

    with billing_tab1:
        col1, col2 = st.columns(2)

        with col1:
            # Billing and Revenue Trend
            if 'date_parsed' in fin_service_filtered.columns:
                billing_trend = fin_service_filtered.groupby('date_parsed').agg({
                    'sewer_billed': 'sum',
                    'sewer_revenue': 'sum',
                    'debt': 'sum'
                }).reset_index()

                fig_billing = go.Figure()
                fig_billing.add_trace(go.Scatter(
                    x=billing_trend['date_parsed'],
                    y=billing_trend['sewer_billed'],
                    name='Billed Amount',
                    mode='lines+markers',
                    line=dict(color='#3b82f6', width=2)
                ))
                fig_billing.add_trace(go.Scatter(
                    x=billing_trend['date_parsed'],
                    y=billing_trend['sewer_revenue'],
                    name='Revenue Collected',
                    mode='lines+markers',
                    line=dict(color='#10b981', width=2)
                ))
                fig_billing.update_layout(
                    title='Billing vs Revenue Collection Over Time',
                    xaxis_title='Date',
                    yaxis_title='Amount ($)',
                    hovermode='x unified',
                    height=400
                )
                st.plotly_chart(fig_billing, use_container_width=True)

        with col2:
            # Debt Accumulation
            if 'date_parsed' in fin_service_filtered.columns:
                fig_debt = go.Figure()
                fig_debt.add_trace(go.Scatter(
                    x=billing_trend['date_parsed'],
                    y=billing_trend['debt'],
                    name='Outstanding Debt',
                    mode='lines+markers',
                    fill='tozeroy',
                    line=dict(color='#ef4444', width=2)
                ))
                fig_debt.update_layout(
                    title='Debt Accumulation Trend',
                    xaxis_title='Date',
                    yaxis_title='Debt ($)',
                    hovermode='x unified',
                    height=400
                )
                st.plotly_chart(fig_debt, use_container_width=True)

    with billing_tab2:
        col1, col2 = st.columns(2)

        with col1:
            # Revenue vs OPEX
            if 'date_parsed' in fin_service_filtered.columns:
                revenue_opex = fin_service_filtered.groupby('date_parsed').agg({
                    'sewer_revenue': 'sum',
                    'opex': 'sum'
                }).reset_index()

                fig_rev_opex = go.Figure()
                fig_rev_opex.add_trace(go.Bar(
                    x=revenue_opex['date_parsed'],
                    y=revenue_opex['sewer_revenue'],
                    name='Revenue',
                    marker_color='#10b981'
                ))
                fig_rev_opex.add_trace(go.Bar(
                    x=revenue_opex['date_parsed'],
                    y=revenue_opex['opex'],
                    name='Operating Expenses',
                    marker_color='#f59e0b'
                ))
                fig_rev_opex.update_layout(
                    title='Revenue vs Operating Expenses',
                    xaxis_title='Date',
                    yaxis_title='Amount ($)',
                    barmode='group',
                    height=400
                )
                st.plotly_chart(fig_rev_opex, use_container_width=True)

        with col2:
            # Cost Recovery Ratio
            avg_cost_recovery = fin_service_filtered['cost_recovery_ratio'].mean()

            fig_recovery = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=avg_cost_recovery,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Cost Recovery Ratio (%)"},
                delta={'reference': 100},
                gauge={
                    'axis': {'range': [None, 150]},
                    'bar': {'color': "#3b82f6"},
                    'steps': [
                        {'range': [0, 70], 'color': "#fee2e2"},
                        {'range': [70, 100], 'color': "#fed7aa"},
                        {'range': [100, 150], 'color': "#d1fae5"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 100
                    }
                }
            ))
            fig_recovery.update_layout(height=400)
            st.plotly_chart(fig_recovery, use_container_width=True)

    with billing_tab3:
        col1, col2 = st.columns(2)

        with col1:
            # Collection Rate by City
            if 'city' in fin_service_filtered.columns:
                city_collection = fin_service_filtered.groupby('city').agg({
                    'collection_rate': 'mean',
                    'sewer_billed': 'sum',
                    'sewer_revenue': 'sum'
                }).reset_index().sort_values('collection_rate', ascending=False)

                fig_city_col = px.bar(
                    city_collection,
                    x='city',
                    y='collection_rate',
                    title='Average Collection Rate by City',
                    color='collection_rate',
                    color_continuous_scale='RdYlGn',
                    labels={'collection_rate': 'Collection Rate (%)'}
                )
                fig_city_col.update_layout(height=400)
                st.plotly_chart(fig_city_col, use_container_width=True)

        with col2:
            # Monthly Collection Pattern
            if 'month_name' in fin_service_filtered.columns:
                month_collection = fin_service_filtered.groupby('month_name')['collection_rate'].mean().reset_index()

                fig_month = px.line(
                    month_collection,
                    x='month_name',
                    y='collection_rate',
                    title='Collection Rate by Month',
                    markers=True,
                    line_shape='spline'
                )
                fig_month.update_layout(height=400)
                st.plotly_chart(fig_month, use_container_width=True)

    # ============================================================================
    # DEBT ANALYSIS
    # ============================================================================

    st.markdown("---")
    st.subheader("🏦 Debt & Arrears Analysis")

    debt_col1, debt_col2, debt_col3 = st.columns(3)

    with debt_col1:
        avg_debt_per_month = total_debt / len(fin_service_filtered) if len(fin_service_filtered) > 0 else 0
        st.metric("Avg Monthly Debt", f"${avg_debt_per_month/1e6:.2f}M")

    with debt_col2:
        debt_to_billed_ratio = (total_debt / total_billed * 100) if total_billed > 0 else 0
        st.metric("Debt-to-Billed Ratio", f"{debt_to_billed_ratio:.1f}%")

    with debt_col3:
        if 'date_parsed' in fin_service_filtered.columns and len(fin_service_filtered) > 1:
            recent_debt_trend = fin_service_filtered.sort_values('date_parsed')['debt'].iloc[-3:].mean()
            previous_debt_trend = fin_service_filtered.sort_values('date_parsed')['debt'].iloc[-6:-3].mean()
            debt_change = ((recent_debt_trend - previous_debt_trend) / previous_debt_trend * 100) if previous_debt_trend != 0 else 0
            st.metric("Debt Trend (Recent)", f"{debt_change:+.1f}%", delta_color="inverse")

    # Debt Analysis Charts
    debt_chart_col1, debt_chart_col2 = st.columns(2)

    with debt_chart_col1:
        # Debt Aging Analysis
        if 'year' in fin_service_filtered.columns:
            debt_by_year = fin_service_filtered.groupby('year')['debt'].sum().reset_index()
            fig_debt_year = px.bar(
                debt_by_year,
                x='year',
                y='debt',
                title='Total Debt by Year',
                color='debt',
                color_continuous_scale='Reds'
            )
            fig_debt_year.update_layout(height=400)
            st.plotly_chart(fig_debt_year, use_container_width=True)

    with debt_chart_col2:
        # Top Debtors (by city)
        if 'city' in fin_service_filtered.columns:
            city_debt = fin_service_filtered.groupby('city')['debt'].sum().reset_index().sort_values('debt', ascending=False).head(10)
            fig_top_debt = px.bar(
                city_debt,
                y='city',
                x='debt',
                orientation='h',
                title='Top 10 Cities by Outstanding Debt',
                color='debt',
                color_continuous_scale='Reds'
            )
            fig_top_debt.update_layout(height=400)
            st.plotly_chart(fig_top_debt, use_container_width=True)

    # ============================================================================
    # FINANCIAL HEALTH ANALYSIS
    # ============================================================================

    st.markdown("---")
    st.subheader("📊 Financial Health Indicators")

    health_tab1, health_tab2, health_tab3 = st.tabs(["💰 Budget Analysis", "⚡ Efficiency Metrics", "👥 Staffing Costs"])

    with health_tab1:
        col1, col2 = st.columns(2)

        with col1:
            # Budget Allocation Breakdown
            if len(national_filtered) > 0:
                latest_year = national_filtered['date_YY'].max()
                latest_budget = national_filtered[national_filtered['date_YY'] == latest_year]

                budget_breakdown = pd.DataFrame({
                    'Category': ['Sanitation', 'Water', 'Staff', 'Training'],
                    'Amount': [
                        latest_budget['san_allocation'].sum(),
                        latest_budget['wat_allocation'].sum(),
                        latest_budget['staff_cost'].sum(),
                        latest_budget['staff_training_budget'].sum()
                    ]
                })

                fig_budget = px.pie(
                    budget_breakdown,
                    values='Amount',
                    names='Category',
                    title=f'Budget Allocation Breakdown ({latest_year})',
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_budget.update_layout(height=400)
                st.plotly_chart(fig_budget, use_container_width=True)

        with col2:
            # Budget Trend Over Years
            if len(national_filtered) > 1:
                budget_trend = national_filtered.groupby('date_YY').agg({
                    'budget_allocated': 'sum',
                    'san_allocation': 'sum',
                    'wat_allocation': 'sum'
                }).reset_index()

                fig_budget_trend = go.Figure()
                fig_budget_trend.add_trace(go.Scatter(
                    x=budget_trend['date_YY'],
                    y=budget_trend['budget_allocated'],
                    name='Total Budget',
                    mode='lines+markers',
                    line=dict(width=3)
                ))
                fig_budget_trend.add_trace(go.Scatter(
                    x=budget_trend['date_YY'],
                    y=budget_trend['san_allocation'],
                    name='Sanitation',
                    mode='lines+markers'
                ))
                fig_budget_trend.add_trace(go.Scatter(
                    x=budget_trend['date_YY'],
                    y=budget_trend['wat_allocation'],
                    name='Water',
                    mode='lines+markers'
                ))
                fig_budget_trend.update_layout(
                    title='Budget Allocation Trends',
                    xaxis_title='Year',
                    yaxis_title='Amount ($)',
                    height=400
                )
                st.plotly_chart(fig_budget_trend, use_container_width=True)

    with health_tab2:
        col1, col2 = st.columns(2)

        with col1:
            # Revenue per Staff
            if 'revenue_per_staff' in fin_service_filtered.columns:
                avg_rev_per_staff = fin_service_filtered['revenue_per_staff'].mean()

                fig_rev_staff = go.Figure(go.Indicator(
                    mode="number+delta",
                    value=avg_rev_per_staff,
                    title={'text': "Avg Revenue per Staff ($)"},
                    number={'prefix': "$", 'valueformat': ",.0f"},
                    delta={'reference': avg_rev_per_staff * 0.9, 'relative': True}
                ))
                fig_rev_staff.update_layout(height=300)
                st.plotly_chart(fig_rev_staff, use_container_width=True)

                # Revenue per staff trend
                if 'date_parsed' in fin_service_filtered.columns:
                    rev_staff_trend = fin_service_filtered.groupby('date_parsed')['revenue_per_staff'].mean().reset_index()
                    fig_rev_staff_trend = px.line(
                        rev_staff_trend,
                        x='date_parsed',
                        y='revenue_per_staff',
                        title='Revenue per Staff Trend',
                        markers=True
                    )
                    st.plotly_chart(fig_rev_staff_trend, use_container_width=True)

        with col2:
            # Complaint Resolution Efficiency
            avg_resolution = fin_service_filtered['complaint_resolution_rate'].mean()

            fig_complaint = go.Figure(go.Indicator(
                mode="gauge+number",
                value=avg_resolution,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Complaint Resolution Rate (%)"},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "#10b981"},
                    'steps': [
                        {'range': [0, 60], 'color': "#fee2e2"},
                        {'range': [60, 80], 'color': "#fed7aa"},
                        {'range': [80, 100], 'color': "#d1fae5"}
                    ]
                }
            ))
            fig_complaint.update_layout(height=300)
            st.plotly_chart(fig_complaint, use_container_width=True)

            # Complaint statistics
            total_complaints = fin_service_filtered['complaints'].sum()
            total_resolved = fin_service_filtered['resolved'].sum()
            unresolved = total_complaints - total_resolved

            st.metric("Total Complaints", f"{total_complaints:,.0f}")
            st.metric("Resolved", f"{total_resolved:,.0f}")
            st.metric("Unresolved", f"{unresolved:,.0f}", delta_color="inverse")

    with health_tab3:
        col1, col2 = st.columns(2)

        with col1:
            # Staff Composition
            total_san_staff = fin_service_filtered['san_staff'].sum()
            total_wat_staff = fin_service_filtered['w_staff'].sum()

            staff_comp = pd.DataFrame({
                'Department': ['Sanitation', 'Water'],
                'Staff Count': [total_san_staff, total_wat_staff]
            })

            fig_staff = px.pie(
                staff_comp,
                values='Staff Count',
                names='Department',
                title='Staff Distribution',
                color_discrete_sequence=['#3b82f6', '#10b981']
            )
            st.plotly_chart(fig_staff, use_container_width=True)

        with col2:
            # Staff Cost Analysis
            if len(national_filtered) > 0:
                staff_cost_trend = national_filtered.groupby('date_YY').agg({
                    'staff_cost': 'sum',
                    'trained_staff': 'sum',
                    'staff_training_budget': 'sum'
                }).reset_index()

                fig_staff_cost = go.Figure()
                fig_staff_cost.add_trace(go.Bar(
                    x=staff_cost_trend['date_YY'],
                    y=staff_cost_trend['staff_cost'],
                    name='Staff Cost',
                    marker_color='#3b82f6'
                ))
                fig_staff_cost.add_trace(go.Bar(
                    x=staff_cost_trend['date_YY'],
                    y=staff_cost_trend['staff_training_budget'],
                    name='Training Budget',
                    marker_color='#10b981'
                ))
                fig_staff_cost.update_layout(
                    title='Staff Cost & Training Budget Trend',
                    xaxis_title='Year',
                    yaxis_title='Amount ($)',
                    barmode='stack',
                    height=400
                )
                st.plotly_chart(fig_staff_cost, use_container_width=True)

    # ============================================================================
    # DATA TABLE & EXPORT
    # ============================================================================

    st.markdown("---")
    st.subheader("📋 Detailed Data View & Export")

    export_tab1, export_tab2 = st.tabs(["📊 Financial Service Data", "🏛️ National Budget Data"])

    with export_tab1:
        st.markdown(f"**{len(fin_service_filtered)} records displayed**")

        # Display options
        show_all_cols = st.checkbox("Show all columns", value=False, key="show_all_fin")

        if show_all_cols:
            display_df = fin_service_filtered
        else:
            key_columns = ['country', 'city', 'date_MMYY', 'sewer_billed', 'sewer_revenue', 
                          'debt', 'collection_rate', 'opex', 'cost_recovery_ratio', 
                          'complaints', 'resolved', 'complaint_resolution_rate']
            display_df = fin_service_filtered[[col for col in key_columns if col in fin_service_filtered.columns]]

        st.dataframe(display_df, use_container_width=True, height=400)

        # Export options
        export_col1, export_col2, export_col3 = st.columns(3)

        with export_col1:
            csv = fin_service_filtered.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"financial_service_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

        with export_col2:
            # Excel export
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                fin_service_filtered.to_excel(writer, sheet_name='Financial Service', index=False)
            buffer.seek(0)

            st.download_button(
                label="📥 Download as Excel",
                data=buffer,
                file_name=f"financial_service_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        with export_col3:
            # JSON export
            json_str = fin_service_filtered.to_json(orient='records', indent=2)
            st.download_button(
                label="📥 Download as JSON",
                data=json_str,
                file_name=f"financial_service_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

    with export_tab2:
        st.markdown(f"**{len(national_filtered)} records displayed**")

        # Display options
        show_all_cols_nat = st.checkbox("Show all columns", value=False, key="show_all_nat")

        if show_all_cols_nat:
            display_df_nat = national_filtered
        else:
            key_columns_nat = ['country', 'city', 'date_YY', 'budget_allocated', 
                              'san_allocation', 'wat_allocation', 'staff_cost', 
                              'trained_staff', 'asset_health']
            display_df_nat = national_filtered[[col for col in key_columns_nat if col in national_filtered.columns]]

        st.dataframe(display_df_nat, use_container_width=True, height=400)

        # Export options
        export_col1, export_col2, export_col3 = st.columns(3)

        with export_col1:
            csv_nat = national_filtered.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download as CSV",
                data=csv_nat,
                file_name=f"national_budget_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

        with export_col2:
            # Excel export
            buffer_nat = io.BytesIO()
            with pd.ExcelWriter(buffer_nat, engine='openpyxl') as writer:
                national_filtered.to_excel(writer, sheet_name='National Budget', index=False)
            buffer_nat.seek(0)

            st.download_button(
                label="📥 Download as Excel",
                data=buffer_nat,
                file_name=f"national_budget_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        with export_col3:
            # JSON export
            json_str_nat = national_filtered.to_json(orient='records', indent=2)
            st.download_button(
                label="📥 Download as JSON",
                data=json_str_nat,
                file_name=f"national_budget_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

    # ============================================================================
    # SUMMARY INSIGHTS
    # ============================================================================

    st.markdown("---")
    st.subheader("💡 Key Insights & Recommendations")

    # Generate automated insights
    insights = []

    # Collection rate insight
    if avg_collection_rate < 70:
        insights.append(("🔴 Critical", f"Collection rate is low at {avg_collection_rate:.1f}%. Consider implementing stricter collection policies and incentive programs."))
    elif avg_collection_rate < 85:
        insights.append(("🟡 Warning", f"Collection rate at {avg_collection_rate:.1f}% needs improvement. Review billing processes and customer engagement strategies."))
    else:
        insights.append(("🟢 Good", f"Collection rate is healthy at {avg_collection_rate:.1f}%. Maintain current practices."))

    # Debt insight
    if debt_to_billed_ratio > 20:
        insights.append(("🔴 Critical", f"Debt-to-billed ratio is {debt_to_billed_ratio:.1f}%, indicating significant arrears. Implement aggressive debt recovery measures."))
    elif debt_to_billed_ratio > 10:
        insights.append(("🟡 Warning", f"Debt-to-billed ratio at {debt_to_billed_ratio:.1f}% requires attention. Consider debt restructuring options."))

    # Cost recovery insight
    avg_cost_recovery = fin_service_filtered['cost_recovery_ratio'].mean()
    if avg_cost_recovery < 80:
        insights.append(("🔴 Critical", f"Cost recovery ratio is only {avg_cost_recovery:.1f}%. Revenue doesn't cover operational costs. Review tariff structure."))
    elif avg_cost_recovery < 100:
        insights.append(("🟡 Warning", f"Cost recovery ratio at {avg_cost_recovery:.1f}% needs improvement to achieve financial sustainability."))
    else:
        insights.append(("🟢 Good", f"Cost recovery ratio is {avg_cost_recovery:.1f}%, indicating financial sustainability."))

    # Display insights
    for status, insight in insights:
        if "Critical" in status:
            st.error(f"{status}: {insight}")
        elif "Warning" in status:
            st.warning(f"{status}: {insight}")
        else:
            st.success(f"{status}: {insight}")

    # Footer
    st.markdown("---")
    st.caption(f"Dashboard generated on {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ----------------------------- Additional Scenes -----------------------------

def scene_production():
    st.markdown("<div class='panel'><h3>Sanitation & Reuse Chain</h3>", unsafe_allow_html=True)
    sc = _load_json("sanitation_chain.json") or {
        "month": "2025-03", "collected_mld": 68, "treated_mld": 43, "ww_reused_mld": 12,
        "fs_treated_tpd": 120, "fs_reused_tpd": 34, "households_non_sewered": 48000, "households_emptied": 16400,
        "public_toilets_functional_pct": 74,
    }
    c1 = (sc["treated_mld"] / max(1, sc["collected_mld"])) * 100
    c2 = (sc["ww_reused_mld"] / max(1, sc["collected_mld"])) * 100
    c3 = (sc["households_emptied"] / max(1, sc["households_non_sewered"])) * 100
    c4 = (sc["fs_reused_tpd"] / max(1, sc["fs_treated_tpd"])) * 100
    tiles = st.columns(5)
    tiles[0].metric("Collected→Treated %", f"{c1:.1f}")
    tiles[1].metric("WW reused / supplied %", f"{c2:.1f}")
    tiles[2].metric("FS emptied %", f"{c3:.1f}")
    tiles[3].metric("Treated FS reused %", f"{c4:.1f}")
    tiles[4].metric("Public toilets functional %", f"{sc['public_toilets_functional_pct']}")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='panel'><h3>Flows</h3>", unsafe_allow_html=True)
    stages = ["Collected", "Treated", "Reused"]
    ww_vals = [sc["collected_mld"], sc["treated_mld"], sc["ww_reused_mld"]]
    fs_vals = [sc["households_non_sewered"], sc["households_emptied"], round(sc["households_non_sewered"] * (c4/100))]
    df_flow = pd.DataFrame({"stage": stages*2, "value": ww_vals+fs_vals, "stream": ["Wastewater"]*3 + ["Faecal Sludge"]*3})
    fig = px.bar(df_flow, x="stage", y="value", color="stream", barmode="group")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="sanitation_flows")
    st.markdown("</div>", unsafe_allow_html=True)


def scene_governance():
    st.markdown("<div class='panel'><h3>Compliance & Providers</h3>", unsafe_allow_html=True)
    gov = _load_json("governance.json") or {
        "active_providers": 42, "total_providers": 50, "active_licensed": 36, "total_licensed": 40,
        "wtp_inspected_count": 18, "invest_in_hc_pct": 2.6,
        "trained": {"male": 120, "female": 86}, "staff_total": 512,
        "compliance": {"license": True, "tariff": True, "levy": False, "reporting": True},
    }
    comp = gov.get("compliance", {})
    cols = st.columns(4)
    cols[0].metric("License valid", "Yes" if comp.get("license") else "No")
    cols[1].metric("Tariff valid", "Yes" if comp.get("tariff") else "No")
    cols[2].metric("Levy paid", "Yes" if comp.get("levy") else "No")
    cols[3].metric("Reporting on time", "Yes" if comp.get("reporting") else "No")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='panel'><h3>Providers & Inspections</h3>", unsafe_allow_html=True)
    pcols = st.columns(3)
    pcols[0].metric("Active providers %", f"{(gov['active_providers']/max(1,gov['total_providers']))*100:.1f}")
    pcols[1].metric("Active licensed %", f"{(gov['active_licensed']/max(1,gov['total_licensed']))*100:.1f}")
    pcols[2].metric("WTP inspected", gov["wtp_inspected_count"])
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='panel'><h3>Human Capital</h3>", unsafe_allow_html=True)
    hcols = st.columns(3)
    hcols[0].metric("Invest in HC %", gov["invest_in_hc_pct"])
    hcols[1].metric("Staff trained (M/F)", f"{gov['trained']['male']}/{gov['trained']['female']}")
    hcols[2].metric("Staff total", gov["staff_total"])
    st.markdown("</div>", unsafe_allow_html=True)


def scene_sector():
    st.markdown("<div class='panel'><h3>Sector Budget</h3>", unsafe_allow_html=True)
    se = _load_json("sector_environment.json") or {
        "year": 2024,
        "budget": {"water_pct": 1.9, "sanitation_pct": 1.1, "wash_disbursed_pct": 72},
        "water_stress_pct": 54,
        "water_use_efficiency": {"agri_usd_per_m3": 1.8, "manufacturing_usd_per_m3": 14.2},
        "disaster_loss_usd_m": 63.5,
    }
    b = se["budget"]
    dfb = pd.DataFrame({"metric": ["Water budget %", "Sanitation budget %", "WASH disbursed %"], "value": [b["water_pct"], b["sanitation_pct"], b["wash_disbursed_pct"]]})
    figb = px.bar(dfb, x="metric", y="value", color="metric")
    st.plotly_chart(figb, use_container_width=True, config={"displayModeBar": False}, key="sector_budget")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='panel'><h3>Environment</h3>", unsafe_allow_html=True)
    ecols = st.columns(3)
    ecols[0].metric("Water stress % (↓)", se["water_stress_pct"])
    ecols[1].metric("WUE Agri $/m³", se["water_use_efficiency"]["agri_usd_per_m3"])
    ecols[2].metric("WUE Mfg $/m³", se["water_use_efficiency"]["manufacturing_usd_per_m3"])
    st.metric("Disaster loss (USD m)", se["disaster_loss_usd_m"])
    st.markdown("</div>", unsafe_allow_html=True)


# ----------------------------- App entry -----------------------------

def render_uhn_dashboard():
    st.set_page_config(page_title="Utility Health Navigator", page_icon="💧", layout="wide")
    _inject_styles()
    _shell_topbar()

    # Sidebar filters
    st.sidebar.title("Filters")
    zone_names = ["All"] + [z["name"] for z in ZONES]
    sel_zone = st.sidebar.selectbox("Zone", zone_names, index=0, key="global_zone")
    if sel_zone == "All":
        st.session_state["selected_zone"] = None
    else:
        st.session_state["selected_zone"] = next((z for z in ZONES if z["name"] == sel_zone), None)

    st.sidebar.markdown("Month range (YYYY-MM)")
    start_month = st.sidebar.text_input("Start", value=st.session_state.get("start_month", ""), key="start_month")
    end_month = st.sidebar.text_input("End", value=st.session_state.get("end_month", ""), key="end_month")

    st.sidebar.radio("Blockages rate basis", ["per 100 km", "per 1000 connections"], index=0, key="blockage_basis")
    if st.sidebar.button("Reset filters"):
        for k in ["global_zone", "selected_zone", "start_month", "end_month", "blockage_basis"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()

    # Top navigation styled as tabs via buttons
    st.markdown("<div class='shell'>", unsafe_allow_html=True)
    scene_labels = [
        ("exec", "Executive Summary"),
        ("access", "Access & Coverage"),
        ("quality", "Service Quality & Reliability"),
        ("finance", "Financial Health"),
        ("production", "Production"),
    ]

    valid_scene_keys = {key for key, _ in scene_labels}
    active = st.session_state.get("active_scene", "exec")
    if active not in valid_scene_keys:
        active = "exec"
        st.session_state["active_scene"] = active
    cols = st.columns(len(scene_labels))
    for (key, label), col in zip(scene_labels, cols):
        with col:
            is_active = active == key
            btn_label = ("● " if is_active else "○ ") + label
            if st.button(btn_label, key=f"tab_{key}"):
                st.session_state["active_scene"] = key
                st.rerun()

    def go_to(scene_key: str):
        if scene_key in valid_scene_keys:
            st.session_state["active_scene"] = scene_key
            st.rerun()

    # Render active scene
    if active == "exec":
        scene_executive(go_to)
    elif active == "access":
        scene_access()
    elif active == "quality":
        scene_quality()
    elif active == "finance":
        scene_finance()
    elif active == "production":
        scene_production()
    else:
        scene_executive(go_to)

    st.markdown("</div>", unsafe_allow_html=True)


def _sidebar_filters():
    st.sidebar.title("Filters")
    zone_names = ["All"] + [z["name"] for z in ZONES]
    sel_zone = st.sidebar.selectbox("Zone", zone_names, index=0, key="global_zone")
    if sel_zone == "All":
        st.session_state["selected_zone"] = None
    else:
        st.session_state["selected_zone"] = next((z for z in ZONES if z["name"] == sel_zone), None)

    st.sidebar.markdown("Month range (YYYY-MM)")
    st.sidebar.text_input("Start", value=st.session_state.get("start_month", ""), key="start_month")
    st.sidebar.text_input("End", value=st.session_state.get("end_month", ""), key="end_month")

    st.sidebar.radio("Blockages rate basis", ["per 100 km", "per 1000 connections"], index=0, key="blockage_basis")
    if st.sidebar.button("Reset filters"):
        for k in ["global_zone", "selected_zone", "start_month", "end_month", "blockage_basis"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()

def render_scene_page(scene_key: str):
    st.set_page_config(page_title="Utility Health Navigator", page_icon="💧", layout="wide")
    _inject_styles()
    _shell_topbar()
    _sidebar_filters()
    st.markdown("<div class='shell'>", unsafe_allow_html=True)
    if scene_key == "exec":
        scene_executive(lambda key: None)
    elif scene_key == "access":
        scene_access()
    elif scene_key == "quality":
        scene_quality()
    elif scene_key == "finance":
        scene_finance()
    elif scene_key == "production":
        scene_production()
    else:
        scene_executive(lambda key: None)
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    render_uhn_dashboard()


# ----------------------------- Map helper -----------------------------

def _render_zone_map_overlay(
    *,
    geojson_path: str,
    id_property: str = "id",
    name_property: str = "name",
    metric_property: str = "safeAccess",
    key: str = "zones_map",
) -> Optional[str]:
    """
    Render a Folium map with zone polygons and return the clicked zone name.
    - Colors polygons by metric_property (expects percentage 0-100).
    - Uses popup to capture selection via streamlit-folium's last_object_clicked_popup.
    Returns selected zone name or None.
    """
    if not HAS_FOLIUM:
        return None
    try:
        path = Path(geojson_path)
        if not path.exists():
            # Try relative to repo root one level up
            alt = Path(__file__).resolve().parents[1] / geojson_path
            path = alt if alt.exists() else path
        with path.open("r", encoding="utf-8") as f:
            gj = json.load(f)
    except Exception:
        st.info("Zones GeoJSON not found (Data/zones.geojson). Falling back to simple grid.")
        return None

    # Compute map center
    def _bounds(feature) -> Tuple[float, float, float, float]:
        coords = feature["geometry"]["coordinates"]
        def iter_coords(c):
            if isinstance(c[0], (float, int)):
                yield c
            else:
                for cc in c:
                    yield from iter_coords(cc)
        lats, lngs = [], []
        for lon, lat in iter_coords(coords):
            lats.append(lat)
            lngs.append(lon)
        return min(lats), min(lngs), max(lats), max(lngs)

    try:
        b = [_bounds(f) for f in gj.get("features", []) if f.get("geometry")]
        lat_c = (min(bb[0] for bb in b) + max(bb[2] for bb in b)) / 2
        lon_c = (min(bb[1] for bb in b) + max(bb[3] for bb in b)) / 2
    except Exception:
        lat_c, lon_c = 0.0, 0.0

    m = folium.Map(location=[lat_c, lon_c], zoom_start=10, tiles="CartoDB positron")

    def color_for(v: Optional[float]) -> str:
        if v is None:
            return "#94a3b8"
        try:
            v = float(v)
        except Exception:
            return "#94a3b8"
        if v >= 80:
            return "#10b981"
        if v >= 60:
            return "#f59e0b"
        return "#ef4444"

    def style_fn(feature: Dict[str, Any]):
        props = feature.get("properties", {})
        v = props.get(metric_property)
        return {
            "fillColor": color_for(v),
            "color": "#334155",
            "weight": 1,
            "fillOpacity": 0.55,
        }

    def highlight_fn(feature):
        return {"weight": 2, "color": "#0ea5e9"}

    tooltip = folium.GeoJsonTooltip(
        fields=[name_property, metric_property],
        aliases=["Zone", "Safe access %"],
        sticky=True,
    )

    # Popup carries clicked zone name
    def _popup_html(feature):
        props = feature.get("properties", {})
        nm = props.get(name_property, "")
        return folium.Popup(html=f"<b>{nm}</b>", max_width=200)

    gj_layer = folium.GeoJson(
        gj,
        name="Zones",
        style_function=style_fn,
        highlight_function=highlight_fn,
        tooltip=tooltip,
        popup=_popup_html,
    )
    gj_layer.add_to(m)

    legend_html = """
    <div style='position: absolute; bottom: 18px; left: 18px; z-index: 9999; background: white; border: 1px solid #e5e7eb; padding: 8px 10px; border-radius: 8px; font: 12px Inter'>
      <div style='margin-bottom: 4px; font-weight: 600; color: #0f172a'>Safe access</div>
      <div><span style='display:inline-block;width:10px;height:10px;background:#10b981;border-radius:3px;margin-right:6px'></span> ≥ 80%</div>
      <div><span style='display:inline-block;width:10px;height:10px;background:#f59e0b;border-radius:3px;margin-right:6px'></span> 60–79%</div>
      <div><span style='display:inline-block;width:10px;height:10px;background:#ef4444;border-radius:3px;margin-right:6px'></span> < 60%</div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    out = st_folium(m, width=None, height=380, returned_objects=["last_object_clicked_popup"], key=key)
    popup_text = out.get("last_object_clicked_popup") if isinstance(out, dict) else None
    if popup_text:
        nm = str(popup_text).replace("<b>", "").replace("</b>", "")
        return nm
    return None