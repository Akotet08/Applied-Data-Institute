from __future__ import annotations

import io
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
import json
from pathlib import Path

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

import numpy as np 

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
def _prepare_service_data() -> Dict[str, Any]:
    """
    Prepare service quality data for visualization.
    Returns a dictionary containing processed service data including:
    - Full service data DataFrame
    - Latest snapshots by zone
    - Aggregated time series for key metrics
    """
    # Load service data
    service_path = DATA_DIR / "Service_data.csv"
    if not service_path.exists():
        raise FileNotFoundError(f"Service data file not found: {service_path}")
    
    df = pd.read_csv(service_path)
    
    # Clean and process data
    # Convert month and year to datetime
    df['date'] = pd.to_datetime(df['year'].astype(str) + '-' + df['month'].astype(str).str.zfill(2) + '-01')
    df = df.sort_values('date')
    
    # Calculate derived metrics
    df['water_quality_rate'] = ((df['test_passed_chlorine'] / df['tests_conducted_chlorine'] * 100 +
                                df['tests_passed_ecoli'] / df['test_conducted_ecoli'] * 100) / 2)
    df['complaint_resolution_rate'] = (df['resolved'] / df['complaints'] * 100)
    df['nrw_rate'] = ((df['w_supplied'] - df['total_consumption']) / df['w_supplied'] * 100)
    df['sewer_coverage_rate'] = (df['sewer_connections'] / df['households'] * 100)
    
    # Get latest snapshot
    latest_by_zone = df.sort_values('date').groupby(['country', 'city', 'zone']).last().reset_index()
    
    # Aggregate time series
    time_series = df.groupby('date').agg({
        'w_supplied': 'sum',
        'total_consumption': 'sum',
        'metered': 'sum',
        'water_quality_rate': 'mean',
        'complaint_resolution_rate': 'mean',
        'nrw_rate': 'mean',
        'sewer_coverage_rate': 'mean',
        'public_toilets': 'sum'
    }).reset_index()
    
    return {
        "full_data": df,
        "latest_by_zone": latest_by_zone,
        "time_series": time_series,
        "zones": sorted(df['zone'].unique()),
        "cities": sorted(df['city'].unique()),
        "countries": sorted(df['country'].unique())
    }

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
def _prepare_service_data() -> Dict[str, Any]:
    """
    Prepare service quality data for visualization.
    Returns a dictionary containing processed service data including:
    - Full service data DataFrame
    - Latest snapshots by zone
    - Aggregated time series for key metrics
    """
    # Load service data
    service_path = DATA_DIR / "Service_data.csv"
    if not service_path.exists():
        raise FileNotFoundError(f"Service data file not found: {service_path}")
    
    df = pd.read_csv(service_path)
    
    # Clean and process data
    # Convert month and year to datetime
    df['date'] = pd.to_datetime(df['year'].astype(str) + '-' + df['month'].astype(str).str.zfill(2) + '-01')
    df = df.sort_values('date')
    
    # Calculate derived metrics
    df['water_quality_rate'] = ((df['test_passed_chlorine'] / df['tests_conducted_chlorine'] * 100 +
                                df['tests_passed_ecoli'] / df['test_conducted_ecoli'] * 100) / 2)
    df['complaint_resolution_rate'] = (df['resolved'] / df['complaints'] * 100)
    df['nrw_rate'] = ((df['w_supplied'] - df['total_consumption']) / df['w_supplied'] * 100)
    df['sewer_coverage_rate'] = (df['sewer_connections'] / df['households'] * 100)
    
    # Get latest snapshot
    latest_by_zone = df.sort_values('date').groupby(['country', 'city', 'zone']).last().reset_index()
    
    # Aggregate time series
    time_series = df.groupby('date').agg({
        'w_supplied': 'sum',
        'total_consumption': 'sum',
        'metered': 'sum',
        'water_quality_rate': 'mean',
        'complaint_resolution_rate': 'mean',
        'nrw_rate': 'mean',
        'sewer_coverage_rate': 'mean',
        'public_toilets': 'sum'
    }).reset_index()
    
    return {
        "full_data": df,
        "latest_by_zone": latest_by_zone,
        "time_series": time_series,
        "zones": sorted(df['zone'].unique()),
        "cities": sorted(df['city'].unique()),
        "countries": sorted(df['country'].unique())
    }

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


ACCESS_WATER_FILE = DATA_DIR / "Water Access Data.csv"
ACCESS_SEWER_FILE = DATA_DIR / "Sewer Access Data.csv"


@st.cache_data
def _load_access_kpi_data() -> pd.DataFrame:
    """
    Combine the water and sewer access CSVs into a tidy structure.
    """
    frames: List[pd.DataFrame] = []
    for path in (ACCESS_WATER_FILE, ACCESS_SEWER_FILE):
        if not path.exists():
            continue
        try:
            frame = pd.read_csv(path)
        except Exception:
            continue
        frame.columns = frame.columns.str.replace(r"^(w_|s_)", "", regex=True)
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df.columns = df.columns.str.replace(r"^(w_|s_)", "", regex=True)
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    for col in ("zone", "country", "type"):
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()
    if "type" in df.columns:
        df["type"] = (
            df["type"]
            .astype("string")
            .str.strip()
            .str.lower()
            .replace({"w_access": "water", "s_access": "sewer"})
        )
    numeric_cols = {col for col in df.columns if col.endswith("_pct")}
    numeric_cols.update({"popn_total", "surface_water", "safely_managed", "open_def", "unimproved"})
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _ensure_year_int(df: pd.DataFrame) -> pd.DataFrame:
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    return df


def _country_summary_2024(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate 2024 safely managed metrics per (country, type).
    """
    d = df.copy()
    d = d[d["year"] == 2024]
    if d.empty:
        return d
    if "type" not in d.columns:
        d["type"] = "unknown"
    d["sewer_gap_pct"] = d.get("unimproved_pct", np.nan) + d.get("open_def_pct", np.nan)
    agg = (
        d.groupby(["country", "type"])
        .agg(
            safely_min=("safely_managed_pct", "min"),
            safely_med=("safely_managed_pct", "median"),
            safely_max=("safely_managed_pct", "max"),
            open_def_min=("open_def_pct", "min"),
            open_def_med=("open_def_pct", "median"),
            open_def_max=("open_def_pct", "max"),
            unimproved_min=("unimproved_pct", "min"),
            unimproved_med=("unimproved_pct", "median"),
            unimproved_max=("unimproved_pct", "max"),
            sewer_gap_min=("sewer_gap_pct", "min"),
            sewer_gap_med=("sewer_gap_pct", "median"),
            sewer_gap_max=("sewer_gap_pct", "max"),
            zones=("zone", "nunique"),
            popn_sum=("popn_total", "sum"),
        )
        .reset_index()
    )
    return agg


def _surface_water_2024(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    For 2024 water records, return per-zone exposure and per-country ranges.
    """
    d = df.copy()
    d = d[(d["year"] == 2024) & (d.get("type") == "water")]
    if d.empty:
        return d, pd.DataFrame()
    if "surface_water_pct" not in d.columns:
        d["surface_water_pct"] = np.nan
    if "popn_total" not in d.columns:
        d["popn_total"] = np.nan
    d = d.dropna(subset=["surface_water_pct", "popn_total"]).copy()
    if d.empty:
        return d, pd.DataFrame()
    d["surface_users_est"] = (d["surface_water_pct"] / 100.0) * d["popn_total"]
    rng = (
        d.groupby("country")
        .agg(
            pct_min=("surface_water_pct", "min"),
            pct_med=("surface_water_pct", "median"),
            pct_max=("surface_water_pct", "max"),
            users_min=("surface_users_est", "min"),
            users_med=("surface_users_est", "median"),
            users_max=("surface_users_est", "max"),
        )
        .reset_index()
    )
    return d, rng


def _trend_series(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return rows between 2020 and 2024 for time-series visualisations.
    """
    if "year" not in df.columns:
        return pd.DataFrame()
    return df[(df["year"] >= 2020) & (df["year"] <= 2024)].copy()


def _urban_rural_tag(zone: Any) -> str:
    if pd.isna(zone):
        return "unknown"
    z = str(zone).lower()
    if "rural" in z:
        return "rural"
    if "urban" in z:
        return "urban"
    if any(k in z for k in ["yaounde", "douala", "kawempe", "kampala", "maseru", "lilongwe", "blantyre"]):
        return "urban"
    return "other"


def scene_access():
    df = _load_access_kpi_data()
    if df.empty:
        st.info("Access datasets not available. Ensure the Water and Sewer access CSVs are in the Data directory.")
        return

    df = _ensure_year_int(df)
    summary_2024 = _country_summary_2024(df)

    st.markdown("<div class='panel'><h3>2024 Safely Managed Coverage by Country</h3>", unsafe_allow_html=True)
    safely_med = summary_2024.dropna(subset=["safely_med"]).copy() if not summary_2024.empty else pd.DataFrame()
    if safely_med.empty:
        st.info("No safely managed coverage records found for 2024.")
    else:
        fig_overall = px.bar(
            safely_med,
            x="country",
            y="safely_med",
            color="type",
            barmode="group",
            hover_data={
                "safely_med": ":.1f",
                "safely_min": ":.1f",
                "safely_max": ":.1f",
                "open_def_med": ":.1f",
                "unimproved_med": ":.1f",
                "zones": True,
                "popn_sum": True,
            },
        )
        fig_overall.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis_title="Safely managed % (median)",
            legend_title="Service",
        )
        st.plotly_chart(fig_overall, width="stretch", config={"displayModeBar": False})
        st.caption("Hover for min/max ranges, open defecation, unimproved shares, zone counts, and population totals.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='panel'><h3>2024 Sewer Access Gap (Unimproved + Open Defecation)</h3>", unsafe_allow_html=True)
    sewer_gap = summary_2024[summary_2024["type"] == "sewer"].dropna(subset=["sewer_gap_med"]).copy() if not summary_2024.empty else pd.DataFrame()
    if sewer_gap.empty:
        st.info("No sewer access gap data available for 2024.")
    else:
        fig_gap = px.bar(
            sewer_gap,
            x="country",
            y="sewer_gap_med",
            hover_data={"sewer_gap_min": ":.1f", "sewer_gap_max": ":.1f"},
        )
        fig_gap.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis_title="Gap % (median)",
            showlegend=False,
        )
        st.plotly_chart(fig_gap, width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='panel'><h3>Surface Water Exposure (Water type, 2024)</h3>", unsafe_allow_html=True)
    sw_2024, sw_ranges = _surface_water_2024(df)
    if sw_2024.empty:
        st.info("No surface water metrics recorded for 2024.")
    else:
        left, right = st.columns(2)
        fig_surface_pct = px.strip(
            sw_2024,
            x="country",
            y="surface_water_pct",
            hover_data=["zone", "surface_water_pct", "popn_total", "surface_users_est"],
        )
        fig_surface_pct.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis_title="Surface water users (%)",
            xaxis_title=None,
        )
        fig_surface_cnt = px.scatter(
            sw_2024,
            x="country",
            y="surface_users_est",
            size="popn_total",
            size_max=45,
            hover_data=["zone", "surface_water_pct", "popn_total", "surface_users_est"],
        )
        fig_surface_cnt.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis_title="Estimated users",
            xaxis_title=None,
        )
        with left:
            st.plotly_chart(fig_surface_pct, width="stretch", config={"displayModeBar": False})
        with right:
            st.plotly_chart(fig_surface_cnt, width="stretch", config={"displayModeBar": False})
        if not sw_ranges.empty:
            st.caption("Per-country surface water exposure ranges (2024).")
            st.dataframe(sw_ranges.round(1), width="stretch")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='panel'><h3>Population Coverage Trend (2020–2024)</h3>", unsafe_allow_html=True)
    ts = _trend_series(df)
    if ts.empty or "popn_total" not in ts.columns or ts["popn_total"].dropna().empty:
        st.info("Population totals unavailable for the requested period.")
    else:
        pop_trend = ts.groupby(["country", "year"], as_index=False)["popn_total"].sum()
        fig_pop_trend = px.line(
            pop_trend,
            x="year",
            y="popn_total",
            color="country",
            markers=True,
        )
        fig_pop_trend.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis_title="Population",
            legend_title="Country",
        )
        st.plotly_chart(fig_pop_trend, width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='panel'><h3>Urban vs Rural Disparities (2024)</h3>", unsafe_allow_html=True)
    ur = df[df["year"] == 2024].copy()
    if ur.empty or "country" not in ur.columns:
        st.info("No 2024 records available to compare urban and rural zones.")
    else:
        ur["ur_tag"] = ur["zone"].map(_urban_rural_tag)
        ur["country"] = ur["country"].astype("string")
        les = ur[ur["country"].str.upper() == "LESOTHO"].copy()
        mw = ur[ur["country"].str.upper() == "MALAWI"].copy()
        col1, col2 = st.columns(2)
        if not les.empty:
            fig_les = px.bar(
                les,
                x="zone",
                y="safely_managed_pct",
                color="type",
                hover_data=["ur_tag", "open_def_pct", "unimproved_pct"],
            )
            fig_les.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_tickangle=-30,
                yaxis_title="Safely managed %",
                legend_title="Service",
            )
            with col1:
                st.plotly_chart(fig_les, width="stretch", config={"displayModeBar": False})
        else:
            col1.info("No Lesotho records found for 2024.")
        if not mw.empty:
            fig_mw = px.bar(
                mw,
                x="zone",
                y="safely_managed_pct",
                color="type",
                hover_data=["ur_tag", "open_def_pct", "unimproved_pct"],
            )
            fig_mw.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_tickangle=-30,
                yaxis_title="Safely managed %",
                legend_title="Service",
            )
            with col2:
                st.plotly_chart(fig_mw, width="stretch", config={"displayModeBar": False})
        else:
            col2.info("No Malawi records found for 2024.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='panel'><h3>Focused Zone Trends (2020–2024)</h3>", unsafe_allow_html=True)
    if ts.empty or "zone" not in ts.columns or "country" not in ts.columns:
        st.info("Time series data unavailable for the 2020–2024 window.")
    else:
        focus_mask = ts["zone"].str.contains("yaounde|maseru|kawempe", case=False, na=False) | ts["country"].astype("string").str.upper().isin(["MALAWI"])
        focus_zones = ts[focus_mask].copy()
        if focus_zones.empty:
            st.info("No focus zones matched the current filters.")
        else:
            fig_yoy = px.line(
                focus_zones,
                x="year",
                y="safely_managed_pct",
                color="zone",
                facet_row="country",
                facet_col="type",
                markers=True,
                hover_data=["country", "zone", "type"],
            )
            fig_yoy.update_layout(
                margin=dict(l=10, r=10, t=40, b=10),
                yaxis_title="Safely managed %",
            )
            st.plotly_chart(fig_yoy, width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='panel'><h3>Priority Zones (2024 snapshot)</h3>", unsafe_allow_html=True)
    if ur.empty or "country" not in ur.columns or "zone" not in ur.columns:
        st.info("Priority ranking unavailable without 2024 records.")
    else:
        priority = (
            ur.assign(sewer_gap_pct=lambda x: x.get("unimproved_pct", np.nan) + x.get("open_def_pct", np.nan))
            .loc[
                lambda x: (
                    (x["country"].str.upper() == "MALAWI")
                    | (x["zone"].str.contains("kawempe", case=False, na=False))
                    | (x["zone"].str.contains("yaounde 1", case=False, na=False))
                    | ((x["country"].str.upper() == "LESOTHO") & (x["zone"].str.contains("rural", case=False, na=False)))
                )
            ][
                ["country", "zone", "type", "popn_total", "safely_managed_pct", "open_def_pct", "unimproved_pct", "sewer_gap_pct"]
            ]
            .sort_values(["country", "zone", "type"])
        )
        if priority.empty:
            st.info("Priority filter returned no rows.")
        else:
            priority_display = priority.rename(
                columns={
                    "popn_total": "population",
                    "safely_managed_pct": "safely_managed_%",
                    "open_def_pct": "open_def_%",
                    "unimproved_pct": "unimproved_%",
                    "sewer_gap_pct": "sewer_gap_%",
                }
            ).copy()
            percent_cols = [col for col in priority_display.columns if col.endswith("%")]
            for col in percent_cols:
                priority_display[col] = priority_display[col].round(1)
            if "population" in priority_display.columns:
                priority_display["population"] = pd.to_numeric(priority_display["population"], errors="coerce").round(0).astype("Int64")
            st.dataframe(priority_display, width="stretch")
            st.caption("Sewer gap = unimproved % + open defecation % (sewer).")
    st.markdown("</div>", unsafe_allow_html=True)

def scene_quality():
    # Load and process service data
    service_data = _prepare_service_data()
    df = service_data["full_data"]
    
    # Add filters in a clean layout with better styling
    st.markdown("""
        <div class='panel' style='margin-bottom: 20px'>
            <h3 style='font-family: Inter, ui-sans-serif; margin-bottom: 15px; color: #0f172a'>
                Service Area Filter
            </h3>
        </div>
    """, unsafe_allow_html=True)
    
    filter_cols = st.columns([1, 1, 1])
    
    with filter_cols[0]:
        countries = ['All'] + service_data["countries"]
        selected_country = st.selectbox(
            'Country',
            countries,
            key='quality_country',
            help="Filter data by country"
        )
        
    with filter_cols[1]:
        if selected_country != 'All':
            cities = ['All'] + sorted(df[df['country'] == selected_country]['city'].unique().tolist())
        else:
            cities = ['All'] + service_data["cities"]
        selected_city = st.selectbox(
            'City',
            cities,
            key='quality_city',
            help="Filter data by city"
        )
        
    with filter_cols[2]:
        if selected_city != 'All':
            zones = ['All'] + sorted(df[df['city'] == selected_city]['zone'].unique().tolist())
        else:
            zones = ['All'] + service_data["zones"]
        selected_zone = st.selectbox(
            'Zone',
            zones,
            key='quality_zone',
            help="Filter data by zone"
        )
    
    # Apply filters to raw data
    filtered_df = df.copy()
    if selected_country != 'All':
        filtered_df = filtered_df[filtered_df['country'] == selected_country]
    if selected_city != 'All':
        filtered_df = filtered_df[filtered_df['city'] == selected_city]
    if selected_zone != 'All':
        filtered_df = filtered_df[filtered_df['zone'] == selected_zone]
    
    # Add filter status indicator
    filter_status = []
    if selected_country != 'All':
        filter_status.append(f"Country: {selected_country}")
    if selected_city != 'All':
        filter_status.append(f"City: {selected_city}")
    if selected_zone != 'All':
        filter_status.append(f"Zone: {selected_zone}")
    if filter_status:
        st.markdown(
            f"""
            <div style='background:#f0f9ff;border:1px solid #93c5fd;padding:8px 12px;border-radius:8px;margin:12px 0'>
                <span style='font-weight:500'>Active Filters:</span> {' • '.join(filter_status)}
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Recalculate time series with filtered data
    time_series = filtered_df.groupby('date').agg({
        'w_supplied': 'sum',
        'total_consumption': 'sum',
        'metered': 'sum',
        'water_quality_rate': 'mean',
        'complaint_resolution_rate': 'mean',
        'nrw_rate': 'mean',
        'sewer_coverage_rate': 'mean',
        'public_toilets': 'sum'
    }).reset_index()
    
    # Calculate latest metrics for KPIs from filtered data
    latest_data = filtered_df.sort_values('date').groupby(['country', 'city', 'zone']).last().reset_index()
    
    # Top KPI Section with improved styling
    st.markdown("""
        <div class='panel' style='margin-bottom: 20px'>
            <h3 style='font-family: Inter, ui-sans-serif; margin-bottom: 15px; color: #0f172a'>
                Key Performance Indicators
            </h3>
    """, unsafe_allow_html=True)
    
    # Calculate KPIs from filtered data
    nrw = latest_data['nrw_rate'].mean()
    water_quality = latest_data['water_quality_rate'].mean()
    resolution_rate = latest_data['complaint_resolution_rate'].mean()
    ww_treatment = latest_data['sewer_coverage_rate'].mean()  # Using sewer coverage as a proxy for treatment
    
    # KPI data with consistent styling
    kpi_data = [
        {
            "label": "Non-Revenue Water",
            "value": nrw,
            "target": 25,
            "color": "#ef4444" if nrw > 25 else "#10b981",
            "icon": "💧"
        },
        {
            "label": "Water Quality",
            "value": water_quality,
            "target": 95,
            "color": "#10b981" if water_quality >= 95 else "#f59e0b",
            "icon": "🧪"
        },
        {
            "label": "Wastewater Treatment",
            "value": ww_treatment,
            "target": 80,
            "color": "#10b981" if ww_treatment >= 80 else "#f59e0b",
            "icon": "♻️"
        },
        {
            "label": "Complaint Resolution",
            "value": resolution_rate,
            "target": 90,
            "color": "#10b981" if resolution_rate >= 90 else "#f59e0b",
            "icon": "✅"
        }
    ]
    
    # Display KPIs in a grid
    cols = st.columns(4)
    for i, kpi in enumerate(kpi_data):
        with cols[i]:
            gauge_style = _conic_css(kpi["value"], kpi["color"])
            st.markdown(
                f"""
                <div class='scorecard' style='font-family: Inter, ui-sans-serif'>
                    <div style='display: flex; align-items: center; margin-bottom: 8px'>
                        <span style='font-size: 20px; margin-right: 8px'>{kpi['icon']}</span>
                        <span style='font-size: 14px; font-weight: 600; color: #0f172a'>{kpi['label']}</span>
                    </div>
                    <div class='gauge-wrap'>
                        <div class='gauge' style="{gauge_style}">
                            <div class='gauge-inner' style='font-family: Inter, ui-sans-serif'>
                                {kpi['value']:.1f}%
                            </div>
                        </div>
                        <div class='meta' style='font-family: Inter, ui-sans-serif'>
                            Target: {kpi['target']}%
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Charts Section - Full width plots using time series data
    # Water Supply vs Consumption Chart
    st.markdown("<div class='panel'><h3>Water Supply vs Consumption</h3>", unsafe_allow_html=True)
    
    # Use the filtered time series data
    fig_supply = go.Figure()
    fig_supply.add_trace(go.Scatter(x=time_series['date'], y=time_series['w_supplied'],
                                  name='Water Supplied', mode='lines+markers',
                                  line=dict(color='#0ea5e9', shape='linear')))
    fig_supply.add_trace(go.Scatter(x=time_series['date'], y=time_series['total_consumption'],
                                  name='Total Consumption', mode='lines+markers',
                                  line=dict(color='#10b981', shape='linear')))
    fig_supply.add_trace(go.Scatter(x=time_series['date'], y=time_series['metered'],
                                  name='Metered Consumption', mode='lines+markers',
                                  line=dict(color='#f59e0b', shape='linear')))
    # Calculate dynamic y-axis range for supply chart
    y_max = max(
        time_series['w_supplied'].max(),
        time_series['total_consumption'].max(),
        time_series['metered'].max()
    )
    y_min = min(
        time_series['w_supplied'].min(),
        time_series['total_consumption'].min(),
        time_series['metered'].min()
    )
    y_padding = (y_max - y_min) * 0.1
    
    fig_supply.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=400,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(
            range=[max(0, y_min - y_padding), y_max + y_padding],
            title="Volume"
        ),
        xaxis=dict(title="Date")
    )
    st.plotly_chart(fig_supply, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Water Quality Tests Chart
    st.markdown("<div class='panel'><h3>Water Quality Tests</h3>", unsafe_allow_html=True)
    fig_quality = go.Figure()
    fig_quality.add_trace(go.Scatter(x=time_series['date'], 
                                   y=time_series['water_quality_rate'],
                                   name='Water Quality Rate',
                                   mode='lines+markers',
                                   line=dict(color='#10b981', shape='linear')))
    target = 95
    fig_quality.add_hline(y=target, line_dash="dot", 
                        line_color="#ef4444",
                        annotation_text="Target")
    fig_quality.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=400,
        yaxis_range=[60, 100],
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_quality, use_container_width=True,
                   config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    # Customer Complaints Chart
    st.markdown("<div class='panel'><h3>Customer Complaints</h3>", unsafe_allow_html=True)
    complaint_resolution = time_series[['date', 'complaint_resolution_rate']].copy()
    
    fig_complaints = go.Figure()
    fig_complaints.add_trace(go.Scatter(x=complaint_resolution['date'], 
                                      y=complaint_resolution['complaint_resolution_rate'],
                                      name='Resolution Rate',
                                      mode='lines+markers',
                                      line=dict(color='#0ea5e9', shape='linear')))
    fig_complaints.update_layout(
        barmode='overlay',
        margin=dict(l=10, r=10, t=10, b=10),
        height=400,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_complaints, use_container_width=True, 
                   config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    # Sanitation Services Chart
    st.markdown("<div class='panel'><h3>Sanitation Services</h3>", unsafe_allow_html=True)
    # Use pre-calculated sewer coverage rate from time series
    fig_sanitation = go.Figure()
    fig_sanitation.add_trace(go.Scatter(x=time_series['date'],
                                      y=time_series['sewer_coverage_rate'],
                                      name='Sewer Coverage %',
                                      mode='lines+markers',
                                      line=dict(color='#10b981', shape='linear')))
    fig_sanitation.add_trace(go.Bar(x=time_series['date'],
                                  y=time_series['public_toilets'],
                                  name='Public Toilets',
                                  marker_color='#0ea5e9'))
    fig_sanitation.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=400,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_sanitation, use_container_width=True,
                   config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)


def scene_finance():
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
    </style>
    """, unsafe_allow_html=True)

    # Financial data structure
    financial_data = {
        "uganda": {
            "staffCostAllocation": {
                "staffCosts": 450000,
                "totalBudget": 2100000,
                "percentage": 21.4
            },
            "nrw": {
                "percentage": 32,
                "volumeLost": 2840000,
                "estimatedRevenueLoss": 890000
            },
            "debt": {
                "totalDebt": 1250000,
                "collectionRate": 78,
                "outstandingBills": 320000
            },
            "billing": {
                "totalBilled": 1850000,
                "collected": 1443000,
                "efficiency": 78
            }
        }
    }

    # Production summary
    production_summary = {
        '2024': {
            'victoria': {'total': 2645143, 'avgDaily': 7234},
            'kyoga': {'total': 2583427, 'avgDaily': 7066}
        },
        '2023': {
            'victoria': {'total': 2589428, 'avgDaily': 7093},
            'kyoga': {'total': 2673284, 'avgDaily': 7324}
        }
    }

    # Header
    st.title("Water Utility Financial Dashboard - Uganda")
    st.markdown("**Financial Plan & Billing KPIs | Sources: Victoria & Kyoga**")

    # Warning banner
    st.warning("⚠️ **Note:** Financial data shown is placeholder structure. Actual production data available: 2020-2024. Awaiting Lesotho billing data.")

    # Year selector
    selected_year = st.selectbox("Select Year", ['2024', '2023', '2022'], index=0)

    st.markdown("---")

    # KPI Cards
    data = financial_data['uganda']
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
        <div class='metric-card'>
            <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:12px'>
                <div style='background:#3b82f6;padding:12px;border-radius:8px'>
                    <span style='color:white;font-size:20px'>💰</span>
                </div>
                <span class='status-badge status-good'>good</span>
            </div>
            <div style='color:#6b7280;font-size:12px;margin-bottom:4px'>Staff Cost Allocation</div>
            <div style='font-size:24px;font-weight:bold;margin-bottom:4px'>{:.1f}%</div>
            <div style='font-size:14px;color:#374151'>${:,.0f}K</div>
            <div style='font-size:11px;color:#9ca3af;margin-top:4px'>of ${:,.0f}K</div>
        </div>
        """.format(
            data['staffCostAllocation']['percentage'],
            data['staffCostAllocation']['staffCosts'] / 1000,
            data['staffCostAllocation']['totalBudget'] / 1000
        ), unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class='metric-card'>
            <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:12px'>
                <div style='background:#f59e0b;padding:12px;border-radius:8px'>
                    <span style='color:white;font-size:20px'>💧</span>
                </div>
                <span class='status-badge status-warning'>warning</span>
            </div>
            <div style='color:#6b7280;font-size:12px;margin-bottom:4px'>Non-Revenue Water</div>
            <div style='font-size:24px;font-weight:bold;margin-bottom:4px'>{}%</div>
            <div style='font-size:14px;color:#374151'>{:.2f}M m³</div>
            <div style='font-size:11px;color:#9ca3af;margin-top:4px'>Loss: ${:,.0f}K</div>
        </div>
        """.format(
            data['nrw']['percentage'],
            data['nrw']['volumeLost'] / 1000000,
            data['nrw']['estimatedRevenueLoss'] / 1000
        ), unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class='metric-card'>
            <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:12px'>
                <div style='background:#10b981;padding:12px;border-radius:8px'>
                    <span style='color:white;font-size:20px'>📈</span>
                </div>
                <span class='status-badge status-good'>good</span>
            </div>
            <div style='color:#6b7280;font-size:12px;margin-bottom:4px'>Collection Rate</div>
            <div style='font-size:24px;font-weight:bold;margin-bottom:4px'>{}%</div>
            <div style='font-size:14px;color:#374151'>${:,.0f}K</div>
            <div style='font-size:11px;color:#9ca3af;margin-top:4px'>of ${:,.0f}K</div>
        </div>
        """.format(
            data['billing']['efficiency'],
            data['billing']['collected'] / 1000,
            data['billing']['totalBilled'] / 1000
        ), unsafe_allow_html=True)

    with col4:
        st.markdown("""
        <div class='metric-card'>
            <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:12px'>
                <div style='background:#ef4444;padding:12px;border-radius:8px'>
                    <span style='color:white;font-size:20px'>⚠️</span>
                </div>
                <span class='status-badge status-critical'>critical</span>
            </div>
            <div style='color:#6b7280;font-size:12px;margin-bottom:4px'>Outstanding Debt</div>
            <div style='font-size:24px;font-weight:bold;margin-bottom:4px'>${:,.0f}K</div>
            <div style='font-size:14px;color:#374151'>${:,.0f}K</div>
            <div style='font-size:11px;color:#9ca3af;margin-top:4px'>Current unpaid bills</div>
        </div>
        """.format(
            data['debt']['totalDebt'] / 1000,
            data['debt']['outstandingBills'] / 1000
        ), unsafe_allow_html=True)

    st.markdown("---")

    # Charts section
    row1_col1, row1_col2 = st.columns(2)

    # Budget Allocation Pie Chart
    with row1_col1:
        st.markdown("<div class='panel'><h3>Budget Allocation Breakdown</h3>", unsafe_allow_html=True)
        
        budget_data = pd.DataFrame([
            {'category': 'Staff Costs', 'value': 21.4, 'amount': 450000},
            {'category': 'Operations', 'value': 35.2, 'amount': 739200},
            {'category': 'Maintenance', 'value': 18.5, 'amount': 388500},
            {'category': 'Infrastructure', 'value': 15.3, 'amount': 321300},
            {'category': 'Other', 'value': 9.6, 'amount': 201600}
        ])
        
        colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
        
        fig1 = go.Figure(data=[go.Pie(
            labels=budget_data['category'],
            values=budget_data['value'],
            marker=dict(colors=colors),
            textinfo='label+percent',
            textposition='outside',
            hovertemplate='<b>%{label}</b><br>%{value}% ($%{customdata}K)<extra></extra>',
            customdata=budget_data['amount'] / 1000
        )])
        
        fig1.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=350,
            showlegend=False
        )
        
        st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})
        
        st.markdown("""
        <div style='border-top:1px solid #e5e7eb;padding-top:12px;margin-top:12px'>
            <div style='display:flex;justify-content:space-between;font-size:13px'>
                <span style='color:#6b7280'>Staff Cost Highlight:</span>
                <span style='font-weight:600;color:#3b82f6'>21.4% - Within Acceptable Range</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # NRW Trend Line Chart
    with row1_col2:
        st.markdown("<div class='panel'><h3>Non-Revenue Water Trend</h3>", unsafe_allow_html=True)
        
        nrw_data = pd.DataFrame([
            {'month': 'Jan', 'nrw': 34, 'target': 25},
            {'month': 'Feb', 'nrw': 33, 'target': 25},
            {'month': 'Mar', 'nrw': 35, 'target': 25},
            {'month': 'Apr', 'nrw': 32, 'target': 25},
            {'month': 'May', 'nrw': 31, 'target': 25},
            {'month': 'Jun', 'nrw': 32, 'target': 25}
        ])
        
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=nrw_data['month'], y=nrw_data['nrw'],
            mode='lines+markers',
            name='Actual NRW',
            line=dict(color='#f59e0b', width=3),
            marker=dict(size=8)
        ))
        fig2.add_trace(go.Scatter(
            x=nrw_data['month'], y=nrw_data['target'],
            mode='lines',
            name='Target',
            line=dict(color='#10b981', width=2, dash='dash')
        ))
        
        fig2.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=350,
            yaxis_title='NRW %',
            xaxis_title='',
            hovermode='x unified'
        )
        
        st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})
        
        st.markdown("""
        <div style='border-top:1px solid #e5e7eb;padding-top:12px;margin-top:12px'>
            <div style='display:flex;justify-content:space-between;font-size:13px'>
                <span style='color:#6b7280'>Current Status:</span>
                <span style='font-weight:600;color:#f59e0b'>32% - Above 25% Target</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Second row of charts
    row2_col1, row2_col2 = st.columns(2)

    # Debt Aging Bar Chart
    with row2_col1:
        st.markdown("<div class='panel'><h3>Debt Aging Analysis</h3>", unsafe_allow_html=True)
        
        debt_data = pd.DataFrame([
            {'category': '0-30 days', 'amount': 120000},
            {'category': '31-60 days', 'amount': 85000},
            {'category': '61-90 days', 'amount': 65000},
            {'category': '90+ days', 'amount': 50000}
        ])
        
        fig3 = go.Figure(data=[go.Bar(
            x=debt_data['category'],
            y=debt_data['amount'],
            marker_color='#ef4444',
            text=debt_data['amount'].apply(lambda x: f'${x/1000:.0f}K'),
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>$%{y:,.0f}<extra></extra>'
        )])
        
        fig3.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=350,
            yaxis_title='Amount ($)',
            xaxis_title='',
            showlegend=False
        )
        
        st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False})
        
        st.markdown("""
        <div style='border-top:1px solid #e5e7eb;padding-top:12px;margin-top:12px'>
            <div style='display:flex;justify-content:space-between;font-size:13px;margin-bottom:8px'>
                <span style='color:#6b7280'>Total Outstanding:</span>
                <span style='font-weight:600;color:#ef4444'>$320K</span>
            </div>
            <div style='display:flex;justify-content:space-between;font-size:13px'>
                <span style='color:#6b7280'>Over 90 days:</span>
                <span style='font-weight:600;color:#ef4444'>$50K (15.6%)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Billing & Collection Summary
    with row2_col2:
        st.markdown("<div class='panel'><h3>Billing & Collection Summary</h3>", unsafe_allow_html=True)
        
        st.markdown("""
        <div style='border-bottom:1px solid #e5e7eb;padding-bottom:16px;margin-bottom:16px'>
            <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'>
                <span style='font-size:13px;color:#6b7280'>Total Billed</span>
                <span style='font-size:18px;font-weight:600'>$1,850K</span>
            </div>
            <div style='width:100%;height:8px;background:#e5e7eb;border-radius:4px'>
                <div style='width:100%;height:8px;background:#3b82f6;border-radius:4px'></div>
            </div>
        </div>
        
        <div style='border-bottom:1px solid #e5e7eb;padding-bottom:16px;margin-bottom:16px'>
            <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'>
                <span style='font-size:13px;color:#6b7280'>Collected</span>
                <span style='font-size:18px;font-weight:600;color:#10b981'>$1,443K</span>
            </div>
            <div style='width:100%;height:8px;background:#e5e7eb;border-radius:4px'>
                <div style='width:78%;height:8px;background:#10b981;border-radius:4px'></div>
            </div>
            <div style='font-size:11px;color:#9ca3af;margin-top:4px'>78% Collection Rate</div>
        </div>
        
        <div style='border-bottom:1px solid #e5e7eb;padding-bottom:16px'>
            <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'>
                <span style='font-size:13px;color:#6b7280'>Outstanding</span>
                <span style='font-size:18px;font-weight:600;color:#f59e0b'>$407K</span>
            </div>
            <div style='width:100%;height:8px;background:#e5e7eb;border-radius:4px'>
                <div style='width:22%;height:8px;background:#f59e0b;border-radius:4px'></div>
            </div>
            <div style='font-size:11px;color:#9ca3af;margin-top:4px'>22% Uncollected</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # Key Financial Highlights
    st.markdown("<div class='panel'><h3>Key Financial Highlights</h3>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div style='border-left:4px solid #3b82f6;padding-left:16px'>
            <h4 style='font-size:16px;font-weight:600;margin-bottom:12px'>Staff Cost Allocation</h4>
            <ul style='font-size:13px;color:#6b7280;line-height:1.8;list-style:none;padding:0'>
                <li>• 21.4% of total budget allocated to staff</li>
                <li>• $450K annual staff costs</li>
                <li>• Within industry benchmark (20-25%)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style='border-left:4px solid #f59e0b;padding-left:16px'>
            <h4 style='font-size:16px;font-weight:600;margin-bottom:12px'>Non-Revenue Water</h4>
            <ul style='font-size:13px;color:#6b7280;line-height:1.8;list-style:none;padding:0'>
                <li>• Current NRW at 32% (Target: 25%)</li>
                <li>• 2.84M m³ water lost annually</li>
                <li>• Estimated revenue loss: $890K</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div style='border-left:4px solid #ef4444;padding-left:16px'>
            <h4 style='font-size:16px;font-weight:600;margin-bottom:12px'>Debt Management</h4>
            <ul style='font-size:13px;color:#6b7280;line-height:1.8;list-style:none;padding:0'>
                <li>• 78% collection efficiency</li>
                <li>• $320K in outstanding bills</li>
                <li>• 15.6% debt over 90 days old</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


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