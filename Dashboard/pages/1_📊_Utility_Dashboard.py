import streamlit as st
from utility_dashboard import render_dashboard


nav_cols = st.columns([1, 1, 6])
with nav_cols[0]:
    st.page_link("Home.py", label="Home", icon="🏠")
with nav_cols[1]:
    st.page_link("pages/1_📊_Utility_Dashboard.py", label="Indicator Catalogue", icon="📊")

st.divider()

# In multipage context, main page already sets wide layout/theme.
render_dashboard(with_page_config=False)
