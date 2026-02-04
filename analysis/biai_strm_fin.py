import streamlit as st
import pandas as pd
import plotly.express as px
import os

# 1. Config must be the first Streamlit command
st.set_page_config(page_title="Austin Crash Command Center 2025", layout="wide")

# 2. Define the loading function
@st.cache_data
def load_data():
    file_path = "atx_crash_data_2018-2026_cleansed.csv"
    
    if not os.path.exists(file_path):
        return None
        
    # Read the data
    df = pd.read_csv(file_path, low_memory=False)
    
    # Preprocessing
    df['Crash timestamp'] = pd.to_datetime(df['Crash timestamp (US/Central)'], errors='coerce')
    df['HOUR'] = df['Crash timestamp'].dt.hour
    df['DAY_NAME'] = df['Crash timestamp'].dt.day_name()
    
    # Map Severity IDs to Names
    sev_map = {1: "Fatal", 2: "Serious Injury", 3: "Minor Injury", 4: "Possible Injury", 0: "No Injury", 5: "Unknown"}
    df['Severity_Label'] = df['crash_sev_id'].map(sev_map)
    
    # Road Type Label
    df['Road_Type'] = df['onsys_fl'].map({True: "Highway/On-System", False: "City Street/Off-System"})
    
    # Flag for Vulnerable Road Users (VRU)
    df['is_vru_fatal'] = (df['pedestrian_death_count'] > 0) | (df['bicycle_death_count'] > 0)
    
    return df

# 3. Call the function
df_raw = load_data()

# 4. Error Handling
if df_raw is None:
    st.error("🛑 File not found. Ensure the CSV is in the same GitHub folder as this script.")
    st.stop()