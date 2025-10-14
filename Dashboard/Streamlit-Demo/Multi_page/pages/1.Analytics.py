# pages/1_📊_analytics.py
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Analytics", page_icon="📊")

# Load data
@st.cache_data
def load_data():
    df = pd.read_csv('../../Data/WARIS.CSV')
    df['Date'] = pd.to_datetime(df[['Year', 'Month']].assign(DAY=1))
    return df

df = load_data()

st.title("Analytics")

# Zone selector
selected_zone = st.selectbox("Select Zone", df['Zone'].unique())

# Filter data by zone
zone_data = df[df['Zone'] == selected_zone]

# Display zone metrics
st.header(f"Zone: {selected_zone}")

# Create two columns for charts
col1, col2 = st.columns(2)

with col1:
    # Revenue pie chart
    fig1 = px.pie(zone_data, 
                  values='Total Operating Revenues', 
                  names='Year',
                  title='Revenue Distribution by Year')
    st.plotly_chart(fig1)

with col2:
    # Collection efficiency bar chart
    fig2 = px.bar(zone_data, 
                  x='Date', 
                  y='Collection Efficiency',
                  title='Collection Efficiency Over Time')
    st.plotly_chart(fig2)