import streamlit as st
import pandas as pd
import plotly.express as px

from utility_dashboard import _inject_base_styles


st.set_page_config(page_title="Utility Performance Monitor", page_icon="💧", layout="wide")
_inject_base_styles()


st.markdown(
    """
    <div class='dashboard-hero'>
        <div class='hero-left'>
            <div class='hero-icon'>💧</div>
            <div>
                <h1>Utility Performance Monitor</h1>
                <p>Landing overview • KPI map and quick insights.</p>
            </div>
        </div>
        <div class='hero-stats' id='landing-hero-stats'></div>
    </div>
    """,
    unsafe_allow_html=True,
)


nav_cols = st.columns([1, 1, 6])
with nav_cols[0]:
    st.page_link("Home.py", label="Home", icon="🏠")
with nav_cols[1]:
    st.page_link("pages/1_📊_Utility_Dashboard.py", label="Indicator Catalogue", icon="📊")

st.divider()


st.subheader("KPI Map")
st.caption("Upload a CSV or use the sample dataset. Required columns: name, lat, lon, kpi.")

uploaded = st.file_uploader("Upload KPI CSV", type=["csv"], label_visibility="collapsed")

if uploaded is not None:
    try:
        kpi_df = pd.read_csv(uploaded)
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        kpi_df = pd.DataFrame()
else:
    # Sample dataset across selected African cities
    kpi_df = pd.DataFrame(
        {
            "name": [
                "Nairobi", "Lagos", "Accra", "Addis Ababa", "Dar es Salaam", "Cape Town"
            ],
            "lat": [ -1.286389, 6.524379, 5.603717, 8.980603, -6.792354, -33.924869 ],
            "lon": [ 36.817223, 3.379206, -0.187000, 38.757759, 39.208328, 18.424055 ],
            # Example KPIs (editable in CSV): continuity hours/day, DWQ compliance %, NRW %
            "Continuity_hours": [ 22, 10, 18, 20, 16, 24 ],
            "DWQ_compliance": [ 96, 85, 92, 94, 88, 98 ],
            "NRW_percent": [ 22, 45, 32, 28, 35, 18 ],
        }
    )
    kpi_df = kpi_df.melt(
        id_vars=["name", "lat", "lon"],
        var_name="kpi_name",
        value_name="kpi",
    )


if kpi_df.empty or not set(["name", "lat", "lon"]).issubset(kpi_df.columns):
    st.info("Awaiting valid KPI data. Ensure columns: name, lat, lon, kpi or wide KPI columns.")
else:
    # If "kpi" column not present (wide format), let user pick one
    kpi_options = []
    if "kpi" in kpi_df.columns and "kpi_name" in kpi_df.columns:
        kpi_options = list(kpi_df["kpi_name"].unique())
    else:
        kpi_options = [c for c in kpi_df.columns if c not in {"name", "lat", "lon"}]

    if kpi_options:
        selected_kpi = st.selectbox("Select KPI", kpi_options, index=0)
        if "kpi" in kpi_df.columns and "kpi_name" in kpi_df.columns:
            plot_df = kpi_df[kpi_df["kpi_name"] == selected_kpi].copy()
        else:
            plot_df = kpi_df.rename(columns={selected_kpi: "kpi"}).copy()

        # KPI cards
        c1, c2, c3 = st.columns(3)
        c1.metric("Average", f"{plot_df['kpi'].mean():.1f}")
        c2.metric("Best", f"{plot_df['kpi'].max():.1f}")
        c3.metric("Worst", f"{plot_df['kpi'].min():.1f}")

        # Color scale direction: green-good for Continuity/DWQ, red-worse for NRW
        if selected_kpi.lower().startswith("nrw"):
            color_cont = "Reds"
            size_scale = 8
        else:
            color_cont = "Greens"
            size_scale = 10

        fig = px.scatter_geo(
            plot_df,
            lat="lat",
            lon="lon",
            hover_name="name",
            size="kpi",
            color="kpi",
            color_continuous_scale=color_cont,
            projection="natural earth",
        )
        fig.update_traces(marker=dict(sizemode="area", sizeref=2.0 * plot_df["kpi"].max() / (size_scale ** 2)))
        fig.update_layout(
            title=f"{selected_kpi} by location",
            margin=dict(l=10, r=10, t=40, b=0),
            height=540,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


st.sidebar.title("About")
st.sidebar.info(
    """
This landing page uses a simple KPI map. Upload your KPI CSV (columns: name, lat, lon, KPI columns) or explore the sample.
Use the Indicator Catalogue page for the full indicator reference and analysis.
    """
)

