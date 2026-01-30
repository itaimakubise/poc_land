import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Austin Crash Command Center 2025", layout="wide")

# --- DATA LOADING ---
@st.cache_data
def load_data():
    # ADJUST THIS PATH to your actual file location
    file_path = r'C:\Users\itai.makubise\code_nova\poc_land\data\atx_crash_2025.csv'
    
    if not os.path.exists(file_path):
        return None
    
    df = pd.read_csv(file_path, low_memory=False)
    
    # Preprocessing
    df['Crash timestamp'] = pd.to_datetime(df['Crash timestamp (US/Central)'], errors='coerce')
    df['HOUR'] = df['Crash timestamp'].dt.hour
    df['MONTH'] = df['Crash timestamp'].dt.month_name()
    df['DAY_NAME'] = df['Crash timestamp'].dt.day_name()
    
    # Map Severity IDs to Names
    sev_map = {1: "Fatal", 2: "Serious Injury", 3: "Minor Injury", 4: "Possible Injury", 0: "No Injury", 5: "Unknown"}
    df['Severity_Label'] = df['crash_sev_id'].map(sev_map)
    
    # Road Type Label
    df['Road_Type'] = df['onsys_fl'].map({True: "Highway/On-System", False: "City Street/Off-System"})
    
    df['high_severity'] = ((df['death_cnt'] > 0) | (df['sus_serious_injry_cnt'] > 0)).astype(int)
    return df

df_raw = load_data()

# --- SAFETY GATE ---
if df_raw is None:
    st.error("🛑 File not found. Please update the 'file_path' in the code to your local CSV path.")
    st.stop()

# --- SIDEBAR: ADVANCED FILTERS ---
st.sidebar.header("🕹️ Control Panel")

# 1. Severity Filter
all_severities = df_raw['Severity_Label'].unique().tolist()
selected_sev = st.sidebar.multiselect("Crash Severity:", all_severities, default=all_severities)

# 2. Road System Filter
road_types = df_raw['Road_Type'].unique().tolist()
selected_roads = st.sidebar.multiselect("Road System:", road_types, default=road_types)

# 3. Day and Time Filter
day_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
selected_days = st.sidebar.multiselect("Days of Week:", day_list, default=day_list)
hour_range = st.sidebar.slider("Hour of Day:", 0, 23, (0, 23))

# 4. Street Search
all_streets = sorted(df_raw['rpt_street_name'].dropna().unique().tolist())
search_street = st.sidebar.multiselect("Filter by Street Name (Optional):", all_streets)

# APPLY ALL FILTERS
df = df_raw[
    (df_raw['Severity_Label'].isin(selected_sev)) &
    (df_raw['Road_Type'].isin(selected_roads)) &
    (df_raw['DAY_NAME'].isin(selected_days)) &
    (df_raw['HOUR'].between(hour_range[0], hour_range[1]))
]

if search_street:
    df = df[df['rpt_street_name'].isin(search_street)]

# --- MAIN DASHBOARD ---
st.title("🚔 Austin Traffic Safety Command Center (2025)")

# --- ROW 1: KPI METRICS ---
col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
with col_kpi1:
    st.metric("Total Incidents", f"{len(df):,}")
with col_kpi2:
    st.metric("Total Fatalities", int(df['death_cnt'].sum()), delta_color="inverse")
with col_kpi3:
    st.metric("Serious Injuries", int(df['sus_serious_injry_cnt'].sum()))
with col_kpi4:
    fatality_rate = (df['death_cnt'].sum() / len(df) * 100) if len(df) > 0 else 0
    st.metric("Fatality Rate", f"{fatality_rate:.2f}%")

st.markdown("---")

# --- ROW 2: BI DESCRIPTIVE ANALYSIS ---
tab1, tab2 = st.tabs(["📊 Incident Trends", "📍 Geographic & Street Risk"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Hourly Peak Analysis")
        fig_hour = px.area(df.groupby('HOUR').size().reset_index(name='count'), 
                           x='HOUR', y='count', title="Crash Volume by Hour",
                           color_discrete_sequence=['#ef233c'])
        st.plotly_chart(fig_hour, use_container_width=True)

    with col2:
        st.subheader("Weekly Distribution")
        # Ensure days are in order
        day_counts = df['DAY_NAME'].value_counts().reindex(day_list).reset_index()
        fig_day = px.bar(day_counts, x='DAY_NAME', y='count', color='count', 
                         title="Incidents by Day of Week", color_continuous_scale='Viridis')
        st.plotly_chart(fig_day, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Road System Comparison")
        fig_road = px.pie(df, names='Road_Type', hole=0.5, title="Highway vs. Local Streets")
        st.plotly_chart(fig_road, use_container_width=True)
        
    with col4:
        st.subheader("Severity Breakdown")
        fig_sev = px.bar(df['Severity_Label'].value_counts().reset_index(), 
                         x='count', y='Severity_Label', orientation='h', 
                         title="Volume by Injury Severity", color='Severity_Label')
        st.plotly_chart(fig_sev, use_container_width=True)

with tab2:
    col_map, col_street = st.columns([2, 1])
    
    with col_map:
        st.subheader("Collision Heatmap")
        st.map(df[['latitude', 'longitude']].dropna())
        
    with col_street:
        st.subheader("Top 10 High-Risk Streets")
        top_streets = df['rpt_street_name'].value_counts().head(10).reset_index()
        fig_top = px.bar(top_streets, x='count', y='rpt_street_name', orientation='h',
                         title="Streets with Highest Frequency", color='count')
        fig_top.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_top, use_container_width=True)

# --- ROW 3: RAW DATA INSPECTION ---
with st.expander("📝 View Filtered Raw Data"):
    st.dataframe(df[['Crash timestamp', 'rpt_street_name', 'Severity_Label', 'death_cnt', 'units_involved']].head(100))