import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="TxDOT | Austin Vision Zero Command Center", layout="wide", page_icon="🏎️")

# --- DATA LOADING ---
@st.cache_data
def load_data():
    file_path = r'C:\Users\itai.makubise\code_nova\poc_land\data\atx_crash_2025.csv'
    if not os.path.exists(file_path):
        return None
    
    df = pd.read_csv(file_path, low_memory=False)
    df['Crash timestamp'] = pd.to_datetime(df['Crash timestamp (US/Central)'], errors='coerce')
    df['Date'] = df['Crash timestamp'].dt.date
    df['HOUR'] = df['Crash timestamp'].dt.hour
    df['DAY_NAME'] = df['Crash timestamp'].dt.day_name()
    
    sev_map = {1: "Fatal", 2: "Serious Injury", 3: "Minor Injury", 4: "Possible Injury", 0: "No Injury", 5: "Unknown"}
    df['Severity_Label'] = df['crash_sev_id'].map(sev_map)
    df['Road_Type'] = df['onsys_fl'].map({True: "Highway/On-System", False: "City Street/Off-System"})
    
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    df['crash_speed_limit'] = pd.to_numeric(df['crash_speed_limit'], errors='coerce').fillna(0)
    df['map_size'] = df['crash_speed_limit'].apply(lambda x: x if x > 0 else 5)
    df['Estimated Total Comprehensive Cost'] = pd.to_numeric(df['Estimated Total Comprehensive Cost'], errors='coerce').fillna(0)
    
    return df.dropna(subset=['latitude', 'longitude'])

df_raw = load_data()

if df_raw is None:
    st.error("🛑 File not found. Please check your file path.")
    st.stop()

# --- SIDEBAR: TXDOT BRANDING & FILTERS ---
with st.sidebar:
    # TxDOT Logo Banner
    st.image("https://www.txdot.gov/etc.clientlibs/txdot/clientlibs/clientlib-site/resources/images/txdot-logo.png", width=200)
    st.markdown("### **Austin District Command**")
    st.divider()
    
    st.header("🕹️ Global Filters")
    clean_street_list = df_raw['rpt_street_name'].dropna()
    clean_street_list = clean_street_list[~clean_street_list.str.contains("NOT REPORTED|UNKNOWN", case=False)]
    all_streets = sorted(clean_street_list.unique().tolist())
    
    selected_street = st.selectbox("🎯 Street-Level Deep Dive:", ["All Streets"] + all_streets)
    hour_range = st.sidebar.slider("Hour of Day:", 0, 23, (0, 23))
    selected_sev = st.multiselect("Severity:", df_raw['Severity_Label'].unique().tolist(), default=df_raw['Severity_Label'].unique().tolist())

# --- DYNAMIC FILTERING LOGIC ---
# Initial Filter based on Sidebar
df_filtered = df_raw.copy()
if selected_street != "All Streets":
    df_filtered = df_filtered[df_filtered['rpt_street_name'] == selected_street]

df_filtered = df_filtered[
    (df_filtered['Severity_Label'].isin(selected_sev)) &
    (df_filtered['HOUR'].between(hour_range[0], hour_range[1]))
]

# --- MAIN UI ---
st.title("🛣️ TxDOT Vision Zero Intelligence Portal")
st.caption("Real-time Crash Data Analysis - Austin District")

# --- DRILL-THROUGH STATE MANAGEMENT ---
# We use a placeholder for the final data used in KPIs so charts can update it
final_df = df_filtered.copy()

# --- ROW 1: KPI METRICS (Dynamic) ---
kpi_container = st.container()

def update_kpis(data):
    m1, m2, m3, m4, m5 = kpi_container.columns(5)
    m1.metric("Total Crashes", f"{len(data):,}")
    m2.metric("🚶 Pedestrian Deaths", int(data['pedestrian_death_count'].sum()))
    m3.metric("🚲 Bicycle Deaths", int(data['bicycle_death_count'].sum()))
    m4.metric("🏍️ Motorcycle Deaths", int(data['motorcycle_death_count'].sum()))
    cost = data['Estimated Total Comprehensive Cost'].sum()
    m5.metric("Economic Impact", f"${cost/1e6:.1f}M")

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["💸 Financial Burden Drill-Through", "🗺️ Geographic Intelligence", "📍 High-Risk Index"])

with tab1:
    st.subheader("Financial Impact Analysis")
    st.info("👆 **Drill-Through Capability:** Click a slice of the donut chart to filter the entire dashboard by that Severity.")
    
    col_chart, col_info = st.columns([2, 1])
    
    with col_chart:
        # Prepare Donut Chart
        cost_sev = df_filtered.groupby('Severity_Label')['Estimated Total Comprehensive Cost'].sum().reset_index()
        cost_sev.columns = ['Injury Severity', 'Total Economic Cost']
        
        fig_donut = px.pie(cost_sev, values='Total Economic Cost', names='Injury Severity', 
                           hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel,
                           title="Comprehensive Cost by Severity")
        
        # ACTIVATE SELECTION
        selected_points = st.plotly_chart(fig_donut, on_select="rerun", selection_mode="points", use_container_width=True)
        
        # If user clicks a slice, filter the final_df
        if selected_points and selected_points["selection"]["points"]:
            selected_label = selected_points["selection"]["points"][0]["label"]
            final_df = df_filtered[df_filtered['Severity_Label'] == selected_label]
            st.success(f"Filtering by: {selected_label}")
            if st.button("Clear Drill-Down"):
                st.rerun()

    with col_info:
        st.write("### **Current Selection Profile**")
        st.write(f"**Records in View:** {len(final_df)}")
        avg_cost = final_df['Estimated Total Comprehensive Cost'].mean()
        st.write(f"**Average Cost/Incident:** ${avg_cost:,.2f}")
        
# Update KPIs at the top based on the final_df (Sidebar + Chart Selection)
with kpi_container:
    update_kpis(final_df)

with tab2:
    st.subheader("Interactive Geographic Intelligence")
    view_mode = st.radio("View Mode:", ["Heatmap", "Incident Detail Markers"], horizontal=True)
    
    if view_mode == "Heatmap":
        fig_map = px.density_mapbox(final_df, lat='latitude', lon='longitude', z='Estimated Total Comprehensive Cost',
                                    radius=12, center=dict(lat=30.2672, lon=-97.7431), zoom=10,
                                    mapbox_style="carto-darkmatter")
    else:
        fig_map = px.scatter_mapbox(final_df, lat='latitude', lon='longitude', color='Severity_Label', 
                                    size='map_size', size_max=15, center=dict(lat=30.2672, lon=-97.7431), zoom=10,
                                    mapbox_style="carto-positron", hover_data=['rpt_street_name', 'crash_speed_limit'])
    
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=600)
    st.plotly_chart(fig_map, use_container_width=True)

with tab3:
    st.subheader("📍 High-Risk Street Intelligence Index")
    # Exclude non-reported
    risk_df = final_df[~final_df['rpt_street_name'].str.contains("NOT REPORTED|UNKNOWN", case=False, na=True)]
    
    risk_index = risk_df.groupby('rpt_street_name').agg({
        'ID': 'count', 'death_cnt': 'sum', 'sus_serious_injry_cnt': 'sum', 'Estimated Total Comprehensive Cost': 'sum'
    }).reset_index()
    
    risk_index.columns = ['Street Name', 'Total Incidents', 'Death Count', 'Serious Injuries', 'Total Comprehensive Cost']
    risk_index = risk_index.nlargest(10, 'Total Incidents')

    st.dataframe(risk_index.style.format({
        'Total Comprehensive Cost': '${:,.0f}', 'Total Incidents': '{:,}', 'Death Count': '{:,}', 'Serious Injuries': '{:,}'
    }).background_gradient(subset=['Total Comprehensive Cost'], cmap='Reds'), use_container_width=True, hide_index=True)

# --- FOOTER ---
st.divider()
st.caption("Data Source: TxDOT CRIS | System maintained by Code Nova POC Land")