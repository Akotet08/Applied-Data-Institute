from __future__ import annotations

import io
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
        "sanitation": "pages/5_♻️_Sanitation_&_Reuse_Chain.py",
        "governance": "pages/6_🏛️_Governance_&_Compliance.py",
        "sector": "pages/7_🌍_Sector_&_Environment.py",
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
        {"label": "Asset Health Index", "value": es["asset_health_idx"], "target": 80, "scene": "governance"},
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


def scene_access():
    # Left column: zones and gap panel
    l, r = st.columns([1, 2])

    with l:
        st.markdown("<div class='panel'><h3>Zones Map</h3>", unsafe_allow_html=True)
        # Try interactive map overlay; falls back to grid if geojson or folium not available
        if HAS_FOLIUM:
            selected_name = _render_zone_map_overlay(
                geojson_path="Data/zones.geojson",
                id_property="id",
                name_property="name",
                metric_property="safeAccess",
                key="zones_map_access",
            )
            if selected_name:
                st.session_state["selected_zone"] = next((z for z in ZONES if z["name"] == selected_name), None)

        # Zone grid (fallback + visual)
        st.markdown("<div class='zonegrid'>", unsafe_allow_html=True)
        cols = st.columns(2)
        for i, z in enumerate(ZONES):
            with cols[i % 2]:
                color = "#10b981" if z["safeAccess"] >= 80 else ("#f59e0b" if z["safeAccess"] >= 60 else "#ef4444")
                st.markdown(
                    f"<div class='zonecard'><div style='display:flex;justify-content:space-between;align-items:center'><span style='font:600 12px Inter'>{z['name']}</span><span class='dot' style='background:{color}'></span></div><div style='height:8px;background:#f1f5f9;border-radius:6px;margin-top:8px'><div style='height:8px;width:{z['safeAccess']}%;background:{color};border-radius:6px'></div></div><div class='meta'>Safe access: {z['safeAccess']}%</div></div>",
                    unsafe_allow_html=True,
                )
                st.button("Select", key=f"select_zone_{z['id']}", on_click=lambda zz=z: st.session_state.update({"selected_zone": zz}), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Gap panel
        st.markdown("<div class='panel'><h3>Gap to Target</h3>", unsafe_allow_html=True)
        current = (st.session_state.get("selected_zone") or {"safeAccess": round(sum(z["safeAccess"] for z in ZONES)/len(ZONES))})["safeAccess"]
        target = 80
        st.metric("Current", f"{current}%")
        st.metric("Target", f"{target}%")
        st.metric("Gap", f"{max(0, target-current)}%")
        proj = st.slider("Projection (+% over next 12 months)", 0, 10, 0)
        st.caption(f"Projected safely managed: {min(100, current + proj)}%")
        st.markdown("</div>", unsafe_allow_html=True)

    with r:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div style='display:flex;align-items:center;justify-content:space-between'><h3>Service Ladders</h3>", unsafe_allow_html=True)
        ac = _load_json("access_coverage.json")
        if ac and "zones" in ac:
            df_water = pd.DataFrame([{**{"zone": z["zone"]}, **z.get("water_ladder", {})} for z in ac["zones"]])
            df_san = pd.DataFrame([{**{"zone": z["zone"]}, **z.get("san_ladder", {})} for z in ac["zones"]])
        else:
            df = pd.DataFrame(SERVICE_LADDER)
            df_water = df.rename(columns={"safely_managed": "safely"})[["zone", "basic", "limited", "unimproved", "safely"]]
            df_water.insert(0, "surface", [5,4,3,8,2][: len(df_water)])
            df_san = df.rename(columns={"safely_managed": "safely", "open_defecation": "open_def"})[["zone", "open_def", "unimproved", "limited", "basic", "safely"]]
        if st.session_state.get("selected_zone"):
            name = st.session_state["selected_zone"]["name"].lower()
            df_water = df_water[df_water["zone"].str.lower().str.contains(name)]
            df_san = df_san[df_san["zone"].str.lower().str.contains(name)]
        _download_button("service-ladder-water.csv", df_water.to_dict(orient="records"))
        _download_button("service-ladder-sanitation.csv", df_san.to_dict(orient="records"))
        st.markdown("</div>", unsafe_allow_html=True)
        # Water ladder stacked bar
        fig_w = go.Figure()
        water_order = ["surface", "unimproved", "limited", "basic", "safely"]
        water_colors = {"surface": "#9ca3af", "unimproved": "#a3a3a3", "limited": "#f59e0b", "basic": "#60a5fa", "safely": "#10b981"}
        xw = df_water["zone"].tolist()
        base = [0] * len(xw)
        for key in water_order:
            if key in df_water.columns:
                fig_w.add_bar(x=xw, y=df_water[key], name=key.replace("_", " ").title(), marker_color=water_colors[key], base=base)
                base = [b + v for b, v in zip(base, df_water[key].tolist())]
        fig_w.update_layout(barmode="stack", margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_w, use_container_width=True, config={"displayModeBar": False}, key="access_water_ladder")
        st.caption("Water ladder • household_survey + lab_results")

        # Sanitation ladder stacked bar
        fig_s = go.Figure()
        san_order = ["open_def", "unimproved", "limited", "basic", "safely"]
        san_colors = {"open_def": "#ef4444", "unimproved": "#a3a3a3", "limited": "#f59e0b", "basic": "#60a5fa", "safely": "#10b981"}
        xs = df_san["zone"].tolist()
        base = [0] * len(xs)
        for key in san_order:
            if key in df_san.columns:
                fig_s.add_bar(x=xs, y=df_san[key], name=key.replace("_", " ").title(), marker_color=san_colors[key], base=base)
                base = [b + v for b, v in zip(base, df_san[key].tolist())]
        fig_s.update_layout(barmode="stack", margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_s, use_container_width=True, config={"displayModeBar": False}, key="access_san_ladder")
        st.caption("Sanitation ladder • household_survey")
        st.markdown("</div>", unsafe_allow_html=True)

        # Coverage dynamics + sparkline
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div style='display:flex;align-items:center;justify-content:space-between'><h3>Coverage Dynamics</h3>", unsafe_allow_html=True)
        dynamics = (ac or {}).get("dynamics") if ac else None
        coverage = (ac or {}).get("coverage") if ac else None
        cols_dyn = st.columns(3)
        cols_dyn[0].metric("Water coverage %", (coverage or {}).get("pct_water", 68))
        cols_dyn[1].metric("Sewered %", (coverage or {}).get("pct_sewered", 22))
        cols_dyn[2].metric("Growth water %", (dynamics or {}).get("pct_water_growth", 3.1))
        df_prog = pd.DataFrame(PROGRESS)
        fig2 = px.line(df_prog, x="m", y="v", markers=False)
        fig2.update_layout(margin=dict(l=10, r=10, t=10, b=10))
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
    l, r = st.columns([7, 5])
    with l:
        st.markdown("<div class='panel'><h3>Revenue vs Opex + Coverage</h3>", unsafe_allow_html=True)
        fin = _load_json("finance.json") or None
        if fin and "months" in fin:
            df = pd.DataFrame({"m": fin["months"], "revenue": fin["revenue"], "opex": fin["opex"]})
            df = _filter_df_by_months(df, "m")
            df["coverage"] = (df["revenue"] / df["opex"]).replace([float("inf"), -float("inf")], pd.NA) * 100
            x = df["m"]
        else:
            df = pd.DataFrame(REVENUE_OPEX)
            x = df["year"]
        fig = go.Figure()
        fig.add_bar(x=x, y=df["revenue"], name="Revenue", marker_color="#34d399")
        fig.add_bar(x=x, y=df["opex"], name="Opex", marker_color="#f59e0b")
        fig.add_trace(go.Scatter(x=x, y=df["coverage"], mode="lines", name="Coverage %", line=dict(color="#0ea5e9", width=2)))
        fig.update_layout(barmode="group", margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="finance_composed")
        st.markdown("</div>", unsafe_allow_html=True)

    with r:
        st.markdown("<div class='panel'><h3>NRW & Collection Efficiency</h3>", unsafe_allow_html=True)
        if fin and "months" in fin:
            dfl = pd.DataFrame({
                "m": fin["months"],
                "nrw": (pd.Series(fin["produced_m3"]) - pd.Series(fin["billed_m3"])) / pd.Series(fin["produced_m3"]) * 100,
                "collection": (pd.Series(fin["revenue"]) / pd.Series(fin["billed"])) * 100 if "billed" in fin else pd.Series([pd.NA]*len(fin["months"]))
            })
            dfl = _filter_df_by_months(dfl, "m")
            x2 = dfl["m"]
        else:
            dfl = pd.DataFrame(NRW_COLLECTION)
            x2 = dfl["year"]
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=x2, y=dfl["nrw"], mode="lines", name="NRW %", line=dict(color="#ef4444", width=2)))
        fig2.add_trace(go.Scatter(x=x2, y=dfl["collection"], mode="lines", name="Collection %", line=dict(color="#10b981", width=2)))
        fig2.update_layout(margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False}, key="finance_dual_line")
        st.markdown("</div>", unsafe_allow_html=True)

    zc, tc = st.columns([1, 1])
    with zc:
        st.markdown("<div class='panel'><h3>Zones</h3>", unsafe_allow_html=True)
        if HAS_FOLIUM:
            selected_name = _render_zone_map_overlay(
                geojson_path="Data/zones.geojson",
                id_property="id",
                name_property="name",
                metric_property="safeAccess",
                key="zones_map_finance",
            )
            if selected_name:
                st.session_state["selected_zone"] = next((z for z in ZONES if z["name"] == selected_name), None)
        # reuse zone grid visual
        cols = st.columns(2)
        for i, z in enumerate(ZONES):
            with cols[i % 2]:
                color = "#10b981" if z["safeAccess"] >= 80 else ("#f59e0b" if z["safeAccess"] >= 60 else "#ef4444")
                st.markdown(
                    f"<div class='zonecard'><div style='display:flex;justify-content:space-between;align-items:center'><span style='font:600 12px Inter'>{z['name']}</span><span class='dot' style='background:{color}'></span></div><div style='height:8px;background:#f1f5f9;border-radius:6px;margin-top:8px'><div style='height:8px;width:{z['safeAccess']}%;background:{color};border-radius:6px'></div></div><div class='meta'>Safe access: {z['safeAccess']}%</div></div>",
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)

    with tc:
        st.markdown("<div class='panel'><h3>Key Financials</h3>", unsafe_allow_html=True)
        zone_name = st.session_state.get("selected_zone", {}).get("name") if st.session_state.get("selected_zone") else "All"
        if fin:
            staff_eff = (fin.get("staff", 0) / max(1, fin.get("active_connections", 1))) * 1000
            staff_cost_pct = (fin.get("staff_cost", 0) / max(1e-9, pd.Series(fin.get("opex", [])).mean())) * 100 if isinstance(fin.get("opex"), list) else fin.get("staff_cost", 0)
            metered_pct = (fin.get("active_metered", 0) / max(1, fin.get("active_connections", 1))) * 100
            rows = pd.DataFrame([
                {"metric": "Staff efficiency (per 1k conns)", "value": round(staff_eff, 2)},
                {"metric": "% Staff cost", "value": round(staff_cost_pct, 1)},
                {"metric": "% Metered connections", "value": round(metered_pct, 1)},
                {"metric": "% Utilisation of WTP", "value": round((fin.get("wtp", {}).get("used_mld", 0) / max(1, fin.get("wtp", {}).get("design_mld", 1))) * 100, 1)},
                {"metric": "% Utilisation of STP", "value": round((fin.get("stp", {}).get("used_mld", 0) / max(1, fin.get("stp", {}).get("design_mld", 1))) * 100, 1)},
                {"metric": "% Utilisation of FSTP", "value": round((fin.get("fstp", {}).get("used_tpd", 0) / max(1, fin.get("fstp", {}).get("design_tpd", 1))) * 100, 1)},
                {"metric": "Pro-poor financing %", "value": fin.get("pro_poor_pct", 0)},
                {"metric": "Budget variance % (actual/allocated)", "value": round((fin.get("budget", {}).get("actual", 0) / max(1, fin.get("budget", {}).get("allocated", 1))) * 100, 1)},
            ])
        else:
            rows = pd.DataFrame(FINANCIALS_TABLE)
        rows.insert(0, "zone", zone_name if zone_name and zone_name != "All zones" else "All")
        st.table(rows)
        data = rows.to_csv(index=False).encode("utf-8")
        st.download_button("Export CSV", data=data, file_name="key-financials.csv")
        st.markdown("</div>", unsafe_allow_html=True)


# ----------------------------- Additional Scenes -----------------------------

def scene_sanitation():
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
        ("sanitation", "Sanitation & Reuse Chain"),
        ("governance", "Governance & Compliance"),
        ("sector", "Sector & Environment"),
    ]

    active = st.session_state.get("active_scene", "exec")
    cols = st.columns(len(scene_labels))
    for (key, label), col in zip(scene_labels, cols):
        with col:
            is_active = active == key
            btn_label = ("● " if is_active else "○ ") + label
            if st.button(btn_label, key=f"tab_{key}"):
                st.session_state["active_scene"] = key
                st.rerun()

    def go_to(scene_key: str):
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
    elif active == "sanitation":
        scene_sanitation()
    elif active == "governance":
        scene_governance()
    elif active == "sector":
        scene_sector()
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
    elif scene_key == "sanitation":
        scene_sanitation()
    elif scene_key == "governance":
        scene_governance()
    elif scene_key == "sector":
        scene_sector()
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
