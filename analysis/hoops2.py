import os
import ssl
import urllib3

# 1. Disable SSL check for the entire Python session
os.environ['CURL_CA_BUNDLE'] = ""
os.environ['PYTHONHTTPSVERIFY'] = '0'

# 2. Create an unverified context
ssl._create_default_https_context = ssl._create_unverified_context

# 3. Suppress the annoying "InsecureRequestWarning" messages
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

print("✅ Global SSL bypass active. Trying to pull data...")

from nba_api.stats.endpoints import playergamelogs
import pandas as pd

# 4. Attempt the pull with a small sample first
try:
    test_pull = playergamelogs.PlayerGameLogs(season_nullable='2025-26', last_n_games_nullable=5)
    df = test_pull.get_data_frames()[0]
    print(f"🎉 SUCCESS! Pulled {len(df)} rows of data.")
    print(df[['PLAYER_NAME', 'PTS']].head())
except Exception as e:
    print(f"❌ Still blocked. Error: {e}")