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
    file_path = r'C:\Users\itai.makubise\code_nova\poc_land\data\atx_crash_2025.csv'
    
    if not os.path.exists(file_path):
        return None
    
    df = pd.read_csv(file_path, low_memory=False)
    
    # 1. Preprocessing & Clean Timestamps
    df['Crash timestamp'] = pd.to_datetime(df['Crash timestamp (US/Central)'], errors='coerce')
    df['Date'] = df['Crash timestamp'].dt.date
    df['HOUR'] = df['Crash timestamp'].dt.hour
    df['DAY_NAME'] = df['Crash timestamp'].dt.day_name()
    
    # 2. Map Severity IDs to Labels
    sev_map = {1: "Fatal", 2: "Serious Injury", 3: "Minor Injury", 4: "Possible Injury", 0: "No Injury", 5: "Unknown"}
    df['Severity_Label'] = df['crash_sev_id'].map(sev_map)
    
    # 3. System Labels
    df['Road_Type'] = df['onsys_fl'].map({True: "Highway/On-System", False: "City Street/Off-System"})
    
    # 4. Lat/Lon Cleaning for Mapbox
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    
    # 5. Clean Speed & Financial Fields
    df['crash_speed_limit'] = pd.to_numeric(df['crash_speed_limit'], errors='coerce').fillna(0)
    df.loc[df['crash_speed_limit'] < 0, 'crash_speed_limit'] = 0
    df['map_size'] = df['crash_speed_limit'].apply(lambda x: x if x > 0 else 5)
    
    # 6. Comprehensive Cost
    df['Estimated Total Comprehensive Cost'] = pd.to_numeric(df['Estimated Total Comprehensive Cost'], errors='coerce').fillna(0)
    
    return df.dropna(subset=['latitude', 'longitude'])

df_raw = load_data()

if df_raw is None:
    st.error("🛑 File not found. Please check your file path.")
    st.stop()

# --- SIDEBAR: CONTROL PANEL ---
st.sidebar.header("🕹️ Vision Zero Filters")

# Clean street list for the dropdown
clean_street_list = df_raw['rpt_street_name'].dropna()
clean_street_list = clean_street_list[~clean_street_list.str.contains("NOT REPORTED|UNKNOWN", case=False)]
all_streets = sorted(clean_street_list.unique().tolist())

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
    st.metric("Economic Impact", f"${total_cost/1e6:.1f}M")

st.markdown("---")

# --- ROW 2: ENHANCED TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["📈 Trends", "🗺️ Geographic Intelligence", "🏘️ Street Analysis", "💸 Financial & VRU Impact"])

# TAB 1: TRENDS
with tab1:
    st.subheader("Cumulative Economic Impact Over Time")
    ts_data = df.groupby('Date')['Estimated Total Comprehensive Cost'].sum().cumsum().reset_index()
    fig_ts = px.line(ts_data, x='Date', y='Estimated Total Comprehensive Cost', 
                     title="Cumulative Fiscal Drain (Year-to-Date)",
                     labels={'Estimated Total Comprehensive Cost': 'Total Cost ($)', 'Date': 'Month/Day'},
                     color_discrete_sequence=['#ff4b4b'])
    st.plotly_chart(fig_ts, use_container_width=True)

# TAB 2: GEOGRAPHY
with tab2:
    st.subheader("Interactive Geographic Intelligence")
    map_col1, map_col2 = st.columns([1, 3])
    with map_col1:
        st.write("🔍 **Map Layers**")
        view_mode = st.radio("Switch Intelligence View:", 
                             ["Economic Density (Heatmap)", "Incident Detail (Markers)", "Collision Heatmap"])
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
            fig_map = px.density_mapbox(df, lat='latitude', lon='longitude', radius=10,
                                        center=dict(lat=30.2672, lon=-97.7431), zoom=10,
                                        mapbox_style="open-street-map")
        fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=550)
        st.plotly_chart(fig_map, use_container_width=True)

# TAB 3: STREET ANALYSIS
with tab3:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Incident Volume by Speed Limit")
        speed_data = df.groupby('crash_speed_limit').size().reset_index(name='Total Crashes')
        fig_speed = px.bar(speed_data, x='crash_speed_limit', y='Total Crashes', color='Total Crashes', 
                           labels={'crash_speed_limit': 'Speed Limit (MPH)'}, color_continuous_scale='YlOrRd')
        st.plotly_chart(fig_speed, use_container_width=True)
    with c2:
        st.subheader("Top 10 High-Risk Corridors")
        # EXCLUDE NOT REPORTED FROM BAR CHART
        street_df = df[~df['rpt_street_name'].str.contains("NOT REPORTED|UNKNOWN", case=False, na=True)]
        risk_idx = street_df.groupby('rpt_street_name').agg({'ID':'count', 'Estimated Total Comprehensive Cost':'sum'}).nlargest(10, 'ID').reset_index()
        risk_idx.columns = ['Street Name', 'Incident Count', 'Total Cost']
        fig_drain = px.bar(risk_idx, x='Total Cost', y='Street Name', orientation='h', color='Total Cost', 
                           labels={'Total Cost': 'Economic Drain ($)'}, color_continuous_scale='Purples')
        st.plotly_chart(fig_drain, use_container_width=True)

# TAB 4: FINANCIAL & VRU IMPACT
with tab4:
    st.subheader("Economic Drain & Vulnerable User Strain")
    f_col1, f_col2 = st.columns(2)
    
    with f_col1:
        cost_sev = df.groupby('Severity_Label')['Estimated Total Comprehensive Cost'].sum().reset_index()
        cost_sev.columns = ['Injury Severity', 'Total Economic Cost']
        fig_cost_sev = px.pie(cost_sev, values='Total Economic Cost', names='Injury Severity', 
                              title="Financial Burden by Injury Severity", hole=0.4,
                              color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_cost_sev, use_container_width=True)
        
    with f_col2:
        vru_data = pd.DataFrame({
            'User Type': ['Pedestrian', 'Bicycle', 'Motorcycle', 'Motor Vehicle'],
            'Death Count': [df['pedestrian_death_count'].sum(), 
                            df['bicycle_death_count'].sum(), 
                            df['motorcycle_death_count'].sum(),
                            df['motor_vehicle_death_count'].sum()]
        })
        fig_vru = px.bar(vru_data, x='User Type', y='Death Count', color='User Type',
                         title="Vulnerable Road User (VRU) Fatality Split",
                         color_discrete_map={'Pedestrian':'#ef233c', 'Bicycle':'#ffb703', 'Motorcycle':'#8d99ae', 'Motor Vehicle':'#2b2d42'})
        st.plotly_chart(fig_vru, use_container_width=True)

    st.markdown("---")
    st.subheader("📍 High-Risk Street Intelligence Index")
    
    # EXCLUDE NOT REPORTED FROM TABLE
    risk_table_df = df[~df['rpt_street_name'].str.contains("NOT REPORTED|UNKNOWN", case=False, na=True)]
    
    risk_index = risk_table_df.groupby('rpt_street_name').agg({
        'ID': 'count',
        'death_cnt': 'sum',
        'sus_serious_injry_cnt': 'sum',
        'Estimated Total Comprehensive Cost': 'sum'
    }).reset_index()
    
    risk_index.columns = ['Street Name', 'Total Incidents', 'Death Count', 'Serious Injuries', 'Total Comprehensive Cost']
    risk_index = risk_index.nlargest(10, 'Total Incidents')

    styled_index = risk_index.style.format({
        'Total Comprehensive Cost': '${:,.0f}',
        'Total Incidents': '{:,}',
        'Death Count': '{:,}',
        'Serious Injuries': '{:,}'
    }).background_gradient(subset=['Total Comprehensive Cost'], cmap='Reds')

    st.dataframe(styled_index, use_container_width=True, hide_index=True)

# --- RAW DATA VIEW ---
with st.expander("🔍 Detailed Records (Sanitized)"):
    raw_display = df[['Crash timestamp', 'rpt_street_name', 'crash_speed_limit', 'Severity_Label', 'Estimated Total Comprehensive Cost']].copy()
    raw_display.columns = ['Timestamp', 'Street Name', 'Speed (MPH)', 'Severity', 'Comprehensive Cost']
    st.dataframe(raw_display.sort_values(by='Comprehensive Cost', ascending=False).style.format({'Comprehensive Cost': '${:,.0f}'}), use_container_width=True)