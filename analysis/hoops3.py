import pandas as pd
import ssl
import os
import urllib3
from datetime import datetime, timedelta
from nba_api.stats.endpoints import playergamelogs

# ==========================================
# 1. SSL & SECURITY BYPASS
# ==========================================
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def run_nba_betting_pipeline(season='2025-26'):
    # Browser-mimicking headers
    custom_headers = {
        'Host': 'stats.nba.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'x-nba-stats-origin': 'stats',
        'x-nba-stats-token': 'true',
        'Referer': 'https://www.nba.com/'
    }

    print(f"🚀 Step 1: Fetching data for {season}...")

    try:
        # Fetch data
        log = playergamelogs.PlayerGameLogs(
            season_nullable=season,
            headers=custom_headers,
            timeout=30
        )
        df = log.get_data_frames()[0]
        
        # Initial Cleanup
        df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
        df = df.sort_values(['PLAYER_NAME', 'GAME_DATE'], ascending=[True, True])
        
        # Calculate Combo Stats
        df['PRA'] = df['PTS'] + df['REB'] + df['AST']
        df['PR'] = df['PTS'] + df['REB']
        df['PA'] = df['PTS'] + df['AST']

        # ==========================================
        # 2. BACK-TO-BACK (B2B) LOGIC
        # ==========================================
        print("🔄 Step 2: Identifying Back-to-Back games...")
        
        # We look at the gap between the current game and the previous game for each team
        # shift(1) gets the previous game's date
        df['PREV_GAME_DATE'] = df.groupby('TEAM_ID')['GAME_DATE'].shift(1)
        
        # If the difference is exactly 1 day, it's the 2nd leg of a B2B
        df['IS_B2B_SECOND_LEG'] = (df['GAME_DATE'] - df['PREV_GAME_DATE']).dt.days == 1
        df['IS_B2B_SECOND_LEG'] = df['IS_B2B_SECOND_LEG'].astype(int)

        # ==========================================
        # 3. ROLLING AVERAGES (L5, L10)
        # ==========================================
        print("📊 Step 3: Calculating Trends...")
        metrics = ['PTS', 'REB', 'AST', 'PRA', 'FG3M']

        for col in metrics:
            # Rolling window of 5 and 10 games
            df[f'{col}_L5'] = df.groupby('PLAYER_NAME')[col].transform(lambda x: x.rolling(window=5, min_periods=1).mean())
            df[f'{col}_L10'] = df.groupby('PLAYER_NAME')[col].transform(lambda x: x.rolling(window=10, min_periods=1).mean())
            df[f'{col}_Season_Avg'] = df.groupby('PLAYER_NAME')[col].transform('mean')

        # ==========================================
        # 4. SAVE AND EXPORT
        # ==========================================
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Save full logs (history)
        raw_filename = f"nba_raw_logs_{today}.csv"
        df.to_csv(raw_filename, index=False, encoding='utf-8-sig')

        # Save only the most recent status for each player
        latest_stats = df.groupby('PLAYER_NAME').tail(1).copy()
        trend_filename = f"nba_trends_ready_{today}.csv"
        latest_stats.to_csv(trend_filename, index=False, encoding='utf-8-sig')
        
        print(f"✅ Success! Trends saved to: {trend_filename}")
        print("-" * 30)
        
        # Quick check: How many players are on the 2nd leg of a B2B today?
        b2b_players = latest_stats[latest_stats['IS_B2B_SECOND_LEG'] == 1]
        print(f"💡 Found {len(b2b_players)} players who just played yesterday.")
        print(b2b_players[['PLAYER_NAME', 'TEAM_ABBREVIATION', 'GAME_DATE']].head())
        
        return latest_stats

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

# Execute
processed_data = run_nba_betting_pipeline()