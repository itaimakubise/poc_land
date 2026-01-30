import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Austin Vision Zero Command Center", layout="wide")

# --- DATA LOADING ---
@st.cache_data
def load_data():
    # ADJUST THIS PATH to your actual file location
    file_path = r'C:\Users\itai.makubise\code_nova\poc_land\data\atx_crash_2025.csv'
    
    if not os.path.exists(file_path):
        return None
    
    df = pd.read_csv(file_path, low_memory=False)
    
    # 1. Basic Preprocessing
    df['Crash timestamp'] = pd.to_datetime(df['Crash timestamp (US/Central)'], errors='coerce')
    df['Date'] = df['Crash timestamp'].dt.date
    df['HOUR'] = df['Crash timestamp'].dt.hour
    df['DAY_NAME'] = df['Crash timestamp'].dt.day_name()
    
    # 2. Map Severity IDs to Labels
    sev_map = {1: "Fatal", 2: "Serious Injury", 3: "Minor Injury", 4: "Possible Injury", 0: "No Injury", 5: "Unknown"}
    df['Severity_Label'] = df['crash_sev_id'].map(sev_map)
    
    # 3. System Labels
    df['Road_Type'] = df['onsys_fl'].map({True: "Highway/On-System", False: "City Street/Off-System"})
    
    # 4. DATA SANITIZATION (Prevents Map Crashes)
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    
    # Clean Speed Limit: Fill NaNs with 0, ensure no negative values
    df['crash_speed_limit'] = pd.to_numeric(df['crash_speed_limit'], errors='coerce').fillna(0)
    df.loc[df['crash_speed_limit'] < 0, 'crash_speed_limit'] = 0
    
    # Create a 'map_size' column: ensures dots are visible even if speed is 0
    df['map_size'] = df['crash_speed_limit'].apply(lambda x: x if x > 0 else 5)
    
    return df.dropna(subset=['latitude', 'longitude'])

df_raw = load_data()

if df_raw is None:
    st.error("🛑 File not found. Please check your file path.")
    st.stop()

# --- SIDEBAR: CONTROL PANEL ---
st.sidebar.header("🕹️ Vision Zero Filters")

all_streets = sorted(df_raw['rpt_street_name'].dropna().unique().tolist())
selected_street = st.sidebar.selectbox("🎯 Street-Level Deep Dive:", ["All Streets"] + all_streets)
hour_range = st.sidebar.slider("Hour of Day:", 0, 23, (0, 23))
selected_days = st.sidebar.multiselect("Days of Week:", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
selected_sev = st.sidebar.multiselect("Severity:", df_raw['Severity_Label'].unique().tolist(), default=df_raw['Severity_Label'].unique().tolist())

# --- FILTER LOGIC ---
df = df_raw.copy()
if selected_street != "All Streets":
    df = df[df['rpt_street_name'] == selected_street]

df = df[
    (df['Severity_Label'].isin(selected_sev)) &
    (df['DAY_NAME'].isin(selected_days)) &
    (df['HOUR'].between(hour_range[0], hour_range[1]))
]

# --- MAIN DASHBOARD HEADER ---
st.title("🏙️ Austin Vision Zero Command Center")
if selected_street != "All Streets":
    st.subheader(f"Street Profile: {selected_street}")

# --- ROW 1: KPI METRICS ---
m1, m2, m3, m4, m5 = st.columns(5)
with m1: st.metric("Total Crashes", f"{len(df):,}")
with m2: st.metric("🚶 Pedestrian Deaths", int(df['pedestrian_death_count'].sum()))
with m3: st.metric("🚲 Bicycle Deaths", int(df['bicycle_death_count'].sum()))
with m4: st.metric("🏍️ Motorcycle Deaths", int(df['motorcycle_death_count'].sum()))
with m5:
    total_cost = df['Estimated Total Comprehensive Cost'].sum()
    st.metric("Total Economic Drain", f"${total_cost/1e6:.1f}M")

st.markdown("---")

# --- ROW 2: TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["📈 Trends", "🗺️ Geographic Intelligence", "🏘️ Streets", "💸 Financials"])

with tab1:
    st.subheader("Cumulative Economic Impact Over Time")
    ts_data = df.groupby('Date')['Estimated Total Comprehensive Cost'].sum().cumsum().reset_index()
    fig_ts = px.line(ts_data, x='Date', y='Estimated Total Comprehensive Cost', 
                     title="Cumulative Cost of Crashes (Year-to-Date)",
                     color_discrete_sequence=['#ff4b4b'])
    st.plotly_chart(fig_ts, use_container_width=True)

with tab2:
    st.subheader("Interactive Geographic Intelligence")
    
    # MAP LAYERING CONTROLS
    map_col1, map_col2 = st.columns([1, 3])
    with map_col1:
        st.write("🔍 **Map Layers**")
        view_mode = st.radio("Switch Intelligence View:", 
                             ["Economic Density (Heatmap)", 
                              "Incident Detail (Markers)", 
                              "Collision Heatmap (Frequency)"])
        
        st.markdown("---")
        st.write("🛰️ **Current View Logic:**")
        if view_mode == "Economic Density (Heatmap)":
            st.caption("Intensity based on **Total Comprehensive Cost**. Reveals financial hotspots.")
        elif view_mode == "Incident Detail (Markers)":
            st.caption("Size based on **Speed Limit**. Reveals correlation between velocity and severity.")
        else:
            st.caption("Standard frequency heatmap. Reveals where crashes happen most often regardless of cost.")
        
    with map_col2:
        if view_mode == "Economic Density (Heatmap)":
            fig_map = px.density_mapbox(df, lat='latitude', lon='longitude', z='Estimated Total Comprehensive Cost',
                                        radius=12, center=dict(lat=30.2672, lon=-97.7431), zoom=10,
                                        mapbox_style="carto-darkmatter")
        elif view_mode == "Incident Detail (Markers)":
            fig_map = px.scatter_mapbox(df, lat='latitude', lon='longitude', color='Severity_Label', 
                                        size='map_size', size_max=15,
                                        center=dict(lat=30.2672, lon=-97.7431), zoom=10,
                                        mapbox_style="carto-positron", 
                                        hover_data={'rpt_street_name':True, 'crash_speed_limit':True, 'Estimated Total Comprehensive Cost':True, 'map_size':False})
        else:
            # Frequency Heatmap
            fig_map = px.density_mapbox(df, lat='latitude', lon='longitude', radius=10,
                                        center=dict(lat=30.2672, lon=-97.7431), zoom=10,
                                        mapbox_style="stamen-terrain") # Traditional map feel
        
        fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=600)
        st.plotly_chart(fig_map, use_container_width=True)
    
    # STREET RISK INDEX (From your first map view)
    st.markdown("---")
    st.subheader("📍 High-Risk Street Intelligence")
    col_idx1, col_idx2 = st.columns([2, 1])
    with col_idx1:
        st.write("Top 10 High-Risk Corridors (Sorted by Fatality & Frequency)")
        risk_index = df.groupby('rpt_street_name').agg({
            'ID': 'count',
            'death_cnt': 'sum',
            'sus_serious_injry_cnt': 'sum',
            'Estimated Total Comprehensive Cost': 'sum'
        }).rename(columns={'ID': 'Total Incidents'}).nlargest(10, 'Total Incidents')
        st.dataframe(risk_index.style.background_gradient(cmap='YlOrRd'), use_container_width=True)
    with col_idx2:
        st.info("""
        **User Insights:**
        - **Policymakers:** Focus on streets with high 'Economic Drain'.
        - **Law Enforcement:** Note the 'Total Incidents' for patrol planning.
        - **Engineers:** Compare 'Fatality' vs 'Total Incidents' to identify lethal infrastructure.
        """)

with tab3:
    c1, c2 = st.columns(2)
    with c1:
        speed_data = df.groupby('crash_speed_limit').size().reset_index(name='count')
        fig_speed = px.bar(speed_data, x='crash_speed_limit', y='count', color='count', color_continuous_scale='YlOrRd')
        st.plotly_chart(fig_speed, use_container_width=True)
    with c2:
        drain_data = df.groupby('rpt_street_name')['Estimated Total Comprehensive Cost'].sum().nlargest(10).reset_index()
        fig_drain = px.bar(drain_data, x='Estimated Total Comprehensive Cost', y='rpt_street_name', orientation='h', color='Estimated Total Comprehensive Cost', color_continuous_scale='Purples')
        st.plotly_chart(fig_drain, use_container_width=True)

with tab4:
    vru_sums = df[['pedestrian_death_count', 'bicycle_death_count', 'motorcycle_death_count', 'motor_vehicle_death_count']].sum()
    fig_vru_pie = px.pie(values=vru_sums.values, names=['Pedestrian', 'Bicycle', 'Motorcycle', 'Motor Vehicle'], 
                         hole=0.5, title="Fatality Distribution")
    st.plotly_chart(fig_vru_pie, use_container_width=True)

# --- RAW DATA VIEW ---
with st.expander("🔍 Detailed Records"):
    st.write(df[['Crash timestamp', 'rpt_street_name', 'crash_speed_limit', 'Severity_Label', 'Estimated Total Comprehensive Cost']].sort_values(by='Estimated Total Comprehensive Cost', ascending=False))