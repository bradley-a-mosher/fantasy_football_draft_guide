import os
import pandas as pd
import nfl_data_py as nfl

# ---------- Shared Build Logic ----------
def build_stats(level="season"):
    """
    Build NFL stats from nfl_data_py.

    Parameters
    ----------
    level : str
        "season" -> returns aggregated season stats
        "weekly" -> returns raw weekly stats

    Returns
    -------
    pd.DataFrame
    """
    years = list(range(2015, 2025))
    weekly_stats = nfl.import_weekly_data(years)

    # -----------------
    # Team ID Mapping
    # -----------------
    team_id_map = {
        'ARI': 1, 'ATL': 2, 'BAL': 3, 'BUF': 4, 'CAR': 5, 'CHI': 6, 'CIN': 7, 'CLE': 8,
        'DAL': 9, 'DEN': 10, 'DET': 11, 'GB': 12, 'HOU': 13, 'IND': 14, 'JAX': 15, 'KC': 16,
        'LAC': 17, 'SD': 17,
        'LAR': 18, 'STL': 18, 'LA': 18,
        'LV': 19, 'OAK': 19,
        'MIA': 20, 'MIN': 21, 'NE': 22, 'NO': 23, 'NYG': 24, 'NYJ': 25,
        'PHI': 26, 'PIT': 27, 'SEA': 28, 'SF': 29, 'TB': 30, 'TEN': 31, 'WAS': 32,
    }

    # Map team_id to weekly stats immediately
    weekly_stats['team_id'] = weekly_stats['recent_team'].map(team_id_map).astype('Int64')

    # Weekly mode: return raw weekly data directly
    if level == "weekly":
        return weekly_stats

    # Season mode: aggregate weekly data to season totals
    position_filt = ['QB', 'RB', 'WR', 'TE']
    weekly_stats_filtered = weekly_stats[
        (weekly_stats['position'].isin(position_filt)) &
        (weekly_stats['season_type'] == 'REG')
    ]

    season_stats = (
        weekly_stats_filtered
        .groupby(['season', 'player_id', 'player_display_name', 'recent_team', 'team_id', 'position'], as_index=False)
        .agg({
            'attempts': 'sum',
            'completions': 'sum',
            'passing_yards': 'sum',
            'passing_tds': 'sum',
            'interceptions': 'sum',
            'carries': 'sum',
            'rushing_yards': 'sum',
            'rushing_tds': 'sum',
            'targets': 'sum',
            'receptions': 'sum',
            'receiving_yards': 'sum',
            'receiving_tds': 'sum',
            'fantasy_points': 'sum',
            'fantasy_points_ppr': 'sum',
            'week': 'nunique'
        })
        .rename(columns={'week': 'games_played'})
    )

    # Team totals and derived metrics
    team_totals = (
        season_stats.groupby(['season', 'recent_team'], as_index=False)
        .agg({'attempts': 'sum', 'carries': 'sum'})
    )
    team_totals['team_total_plays'] = team_totals['attempts'] + team_totals['carries']
    season_stats = season_stats.merge(
        team_totals[['season', 'recent_team', 'team_total_plays']],
        on=['season', 'recent_team'],
        how='left'
    )

    # Usage and target share
    season_stats['usage'] = season_stats['carries'] / season_stats['team_total_plays']

    team_pass_totals = (
        season_stats.groupby(['season', 'recent_team'], as_index=False)
        .agg({'attempts': 'sum'})
        .rename(columns={'attempts': 'team_pass_attempts'})
    )
    season_stats = season_stats.merge(team_pass_totals, on=['season', 'recent_team'], how='left')

    season_stats['target_share'] = season_stats['targets'] / season_stats['team_pass_attempts']

    # Fantasy points per game
    season_stats['fantasy_points_pg'] = season_stats['fantasy_points'] / season_stats['games_played']
    season_stats['fantasy_points_ppr_pg'] = season_stats['fantasy_points_ppr'] / season_stats['games_played']

    return season_stats

# ---------- Save Parquet Files ----------
if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)

    print("Building season stats...")
    season_stats = build_stats(level="season")
    season_stats.to_parquet("data/season_stats.parquet", index=False)
    print("Saved data/season_stats.parquet")

    print("Building weekly stats...")
    weekly_stats = build_stats(level="weekly")
    weekly_stats.to_parquet("data/weekly_stats.parquet", index=False)
    print("Saved data/weekly_stats.parquet")

    print("Data files generated successfully!")
