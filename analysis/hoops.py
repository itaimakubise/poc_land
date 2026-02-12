import pandas as pd
import time
from nba_api.stats.endpoints import playergamelogs
from nba_api.stats.static import players

def fetch_current_season_data(season='2025-26'):
    """
    Fetches all player game logs for the specified season.
    """
    print(f"Fetching data for the {season} season...")
    
    # We use PlayerGameLogs to get EVERY game played by EVERY player in one call
    # This is much faster than looping through individual players
    gamelogs = playergamelogs.PlayerGameLogs(
        season_nullable=season,
        season_type_nullable='Regular Season'
    )
    
    df = gamelogs.get_data_frames()[0]
    
    # Selecting the specific columns useful for PrizePicks props
    relevant_cols = [
        'PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'GAME_ID', 'GAME_DATE',
        'MATCHUP', 'WL', 'MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FG3M'
    ]
    
    df = df[relevant_cols]
    
    # Creating common PrizePicks combo stats (PRA)
    df['PRA'] = df['PTS'] + df['REB'] + df['AST']
    
    # Formatting date for better sorting
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    
    return df

# Run the fetcher
nba_data = fetch_current_season_data()

# Quick look at the data
print(nba_data.head())

# Save to CSV for the next steps of your model
nba_data.to_csv('nba_player_logs_2026.csv', index=False)