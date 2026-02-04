# --- DATA LOADING ---
@st.cache_data
def load_data():
    # 1. Define the path inside the function
    file_path = "atx_crash_data_2018-2026_cleansed.csv"

    # 2. Check if file exists BEFORE trying to read it
    if not os.path.exists(file_path):
        # We return None so the script doesn't crash here
        return None

    # 3. Read the data (All these lines MUST be indented)
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
    
    return df # This now sits correctly inside the function

# --- EXECUTION ---
df_raw = load_data()

# --- SAFETY GATE ---
if df_raw is None:
    st.error("🛑 File not found. Please ensure 'atx_crash_data_2018-2026_cleansed.csv' is in your GitHub repository root.")
    st.stop()
    