"""
Quick visualizations for Water/Sewer access data.

Reads the two CSVs, normalizes column names, and generates a few
Plotly charts saved to the `Output/` folder:

- Stacked bars: access ladder by zone (per type)
- Time series: municipal coverage by year (by type)
- Box plot: safely managed % distribution by type
- Country bars: top countries by safely managed % (latest year)

Usage:
  python visualize.py [--country NAME]

Dependencies: pandas, plotly (declared in requirements.txt)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import plotly.express as px


DATA_WATER = Path("Water Access Data.csv")
DATA_SEWER = Path("Sewer Access Data.csv")
OUT_DIR = Path("Output")


def load_data() -> pd.DataFrame:
    """Load, clean, and combine water + sewer CSVs into one DataFrame."""
    water_df = pd.read_csv(DATA_WATER)
    sewer_df = pd.read_csv(DATA_SEWER)

    # Strip prefixes introduced by source files
    water_df.columns = water_df.columns.str.replace("w_", "", regex=False)
    sewer_df.columns = sewer_df.columns.str.replace("s_", "", regex=False)

    # Combine
    df = pd.concat([water_df, sewer_df], ignore_index=True)
    # Ensure any remaining w_/s_ prefixes are removed on combined columns
    df.columns = df.columns.str.replace(r'^(w_|s_)', '', regex=True)

    # Dtypes & minor hygiene
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    if "zone" in df.columns:
        df["zone"] = df["zone"].astype("string").str.strip()
    if "country" in df.columns:
        df["country"] = df["country"].astype("string").str.strip()
    if "type" in df.columns:
        df["type"] = df["type"].astype("string").str.strip().str.lower()

    return df


def _ladder_config(for_type: str) -> tuple[list[str], dict[str, str]]:
    """Return ordered ladder columns and colors for a given type."""
    for_type = (for_type or "").lower()
    if for_type.startswith("water"):
        cols = [
            "surface_water_pct",
            "unimproved_pct",
            "limited_pct",
            "basic_pct",
            "safely_managed_pct",
        ]
    else:
        # default to sewer/sanitation order: open defecation lowest rung
        cols = [
            "open_def_pct",
            "unimproved_pct",
            "limited_pct",
            "basic_pct",
            "safely_managed_pct",
        ]

    colors = {
        "surface_water_pct": "#9ca3af",  # gray
        "open_def_pct": "#ef4444",       # red
        "unimproved_pct": "#a3a3a3",    # gray
        "limited_pct": "#f59e0b",       # amber
        "basic_pct": "#60a5fa",         # blue
        "safely_managed_pct": "#10b981", # green
    }
    return cols, colors


def plot_access_ladder_by_zone(df: pd.DataFrame, type_value: str | None = None) -> Path | None:
    """Stacked bar of ladder % by zone for the latest year, filtered by type."""
    if "type" in df.columns and type_value:
        dft = df[df["type"].str.lower() == type_value.lower()].copy()
        title_type = type_value.title()
    else:
        dft = df.copy()
        title_type = dft.get("type", pd.Series(["All"]).iloc[0])

    if dft.empty:
        return None

    # pick latest year per zone
    if "year" in dft.columns and dft["year"].notna().any():
        latest_year = int(dft["year"].dropna().max())
        dft = dft[dft["year"] == latest_year].copy()
        year_note = f" (Year {latest_year})"
    else:
        year_note = ""

    cols, colors = _ladder_config(type_value or "")
    avail = [c for c in cols if c in dft.columns]
    if not avail:
        return None

    # Avoid NaNs for stacking
    dft[avail] = dft[avail].fillna(0)

    # Make long for stacked bars
    id_vars = [c for c in ["zone"] if c in dft.columns]
    if not id_vars:
        id_vars = ["country"] if "country" in dft.columns else []
    dfl = dft.melt(id_vars=id_vars, value_vars=avail, var_name="level", value_name="pct")

    # Nicify labels
    dfl["level"] = dfl["level"].str.replace("_pct", "", regex=False).str.replace("_", " ").str.title()

    # Keep the original column names for color mapping
    level_order = [
        c.replace("_pct", "").replace("_", " ").title()
        for c in cols if c in avail
    ]
    color_map = {
        c.replace("_pct", "").replace("_", " ").title(): v for c, v in colors.items()
    }

    x_col = "zone" if "zone" in dfl.columns else ("country" if "country" in dfl.columns else None)
    if x_col is None:
        return None

    fig = px.bar(
        dfl,
        x=x_col,
        y="pct",
        color="level",
        category_orders={"level": level_order},
        color_discrete_map=color_map,
        title=f"{title_type} Access Ladder by {x_col.title()}{year_note}",
    )
    fig.update_layout(barmode="stack", yaxis_title="Percent", legend_title="Level")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fn = f"{(type_value or 'all').lower()}_access_ladder_by_{x_col}.html"
    out_path = OUT_DIR / fn
    fig.write_html(str(out_path), include_plotlyjs="cdn")
    return out_path


def plot_municipal_coverage_timeseries(df: pd.DataFrame) -> Path | None:
    if "municipal_coverage" not in df.columns or "year" not in df.columns:
        return None
    d = df.dropna(subset=["municipal_coverage", "year"]).copy()
    if d.empty:
        return None
    if "type" in d.columns:
        g = d.groupby(["type", "year"], as_index=False)["municipal_coverage"].mean()
        fig = px.line(
            g,
            x="year",
            y="municipal_coverage",
            color="type",
            markers=True,
            title="Municipal Coverage Over Time",
        )
    else:
        g = d.groupby(["year"], as_index=False)["municipal_coverage"].mean()
        fig = px.line(g, x="year", y="municipal_coverage", markers=True, title="Municipal Coverage Over Time")

    fig.update_layout(yaxis_title="Coverage %", legend_title="Type")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "municipal_coverage_timeseries.html"
    fig.write_html(str(out_path), include_plotlyjs="cdn")
    return out_path


def plot_safely_managed_box(df: pd.DataFrame) -> Path | None:
    col = "safely_managed_pct"
    if col not in df.columns:
        return None
    d = df.dropna(subset=[col]).copy()
    if d.empty:
        return None

    # Add contextual fields to point hover if present
    hover_cols = [c for c in ["country", "zone", "year"] if c in d.columns]

    if "type" in d.columns:
        fig = px.box(
            d,
            x="type",
            y=col,
            points="all",
            hover_data=hover_cols,
            title="Safely Managed % by Type",
        )
    else:
        fig = px.box(
            d,
            y=col,
            points="all",
            hover_data=hover_cols,
            title="Safely Managed % Distribution",
        )

    fig.update_layout(yaxis_title="Safely Managed %", xaxis_title="Type")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "safely_managed_box.html"
    fig.write_html(str(out_path), include_plotlyjs="cdn")
    return out_path


def plot_country_top_safely(df: pd.DataFrame, type_value: str | None = None, top_n: int = 10) -> Path | None:
    col = "safely_managed_pct"
    if col not in df.columns or "country" not in df.columns:
        return None

    d = df.copy()
    if type_value and "type" in d.columns:
        d = d[d["type"].str.lower() == type_value.lower()].copy()
    if d.empty:
        return None

    if "year" in d.columns and d["year"].notna().any():
        latest_year = int(d["year"].dropna().max())
        d = d[d["year"] == latest_year]
        year_note = f" (Year {latest_year})"
    else:
        year_note = ""

    g = (
        d.dropna(subset=[col])
        .groupby("country", as_index=False)[col]
        .mean()
        .sort_values(col, ascending=False)
        .head(top_n)
    )
    if g.empty:
        return None

    fig = px.bar(g, x="country", y=col, title=f"Top {top_n} Countries by Safely Managed %{year_note}")
    fig.update_layout(yaxis_title="Safely Managed %", xaxis_title="Country")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"_{type_value.lower()}" if type_value else ""
    out_path = OUT_DIR / f"top_countries_safely_managed{suffix}.html"
    fig.write_html(str(out_path), include_plotlyjs="cdn")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Generate quick plots for access data.")
    parser.add_argument("--country", type=str, default=None, help="Optional country filter")
    args = parser.parse_args()

    df = load_data()
    if args.country and "country" in df.columns:
        df = df[df["country"].str.lower() == args.country.lower()].copy()

    outputs: list[tuple[str, Path | None]] = []
    # Stacked ladders per type (if available)
    types = sorted(df["type"].dropna().unique().tolist()) if "type" in df.columns else [None]
    for t in types:
        outputs.append((f"ladder_{t}", plot_access_ladder_by_zone(df, t if t else None)))

    # Cross-type plots
    outputs.append(("timeseries", plot_municipal_coverage_timeseries(df)))
    outputs.append(("safely_box", plot_safely_managed_box(df)))
    for t in types:
        outputs.append((f"top_countries_{t}", plot_country_top_safely(df, t if t else None)))

    # Print a small summary
    print("Saved plots:")
    for name, path in outputs:
        if path:
            print(f"- {name}: {path}")
        else:
            print(f"- {name}: (skipped - missing columns or data)")


if __name__ == "__main__":
    main()
