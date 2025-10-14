import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Data", page_icon="📋")

# Load data
@st.cache_data
def load_data():
    df = pd.read_csv('../../Data/WARIS.CSV')
    df['Date'] = pd.to_datetime(df[['Year', 'Month']].assign(DAY=1))
    return df

df = load_data()

st.title("Data Explorer")

# Filters
col1, col2 = st.columns(2)

with col1:
    selected_year = st.multiselect("Select Years", sorted(df['Year'].unique()))

with col2:
    selected_zones = st.multiselect("Select Zones", df['Zone'].unique())

# Apply filters
if selected_year and selected_zones:
    filtered_df = df[df['Year'].isin(selected_year) & df['Zone'].isin(selected_zones)]
elif selected_year:
    filtered_df = df[df['Year'].isin(selected_year)]
elif selected_zones:
    filtered_df = df[df['Zone'].isin(selected_zones)]
else:
    filtered_df = df

# Show filtered data
st.dataframe(filtered_df)

# Download button
csv = filtered_df.to_csv(index=False).encode('utf-8')
st.download_button(
    "Download Data as CSV",
    csv,
    "filtered_data.csv",
    "text/csv",
    key='download-csv'
)