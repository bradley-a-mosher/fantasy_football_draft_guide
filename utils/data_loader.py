import pandas as pd

# ------------------------------
# Load Season & Weekly Stats
# ------------------------------

def load_season_stats(level="season"):
    """
    Load aggregated season stats or weekly stats from parquet files.

    Parameters
    ----------
    level : str
        "season" -> returns aggregated season stats
        "weekly" -> returns weekly stats

    Returns
    -------
    pd.DataFrame
    """
    if level == "season":
        file_path = "data/season_stats.parquet"
    elif level == "weekly":
        file_path = "data/weekly_stats.parquet"
    else:
        raise ValueError("Invalid level. Choose 'season' or 'weekly'.")

    return pd.read_parquet(file_path)


# ------------------------------
# Load Coaching Data (CSV)
# ------------------------------

def load_coaching_data():
    """
    Load NFL coaching data (historical) from CSV.
    """
    file_path = "utils/nfl_coaching_data - Coaching Staff.csv"
    return pd.read_csv(file_path).drop_duplicates()


# ------------------------------
# Load Active Rosters
# ------------------------------

def load_active_rosters():
    """
    Load active NFL rosters from parquet.
    """
    file_path = "data/active_rosters.parquet"
    return pd.read_parquet(file_path)


# ------------------------------
# Load Active Contracts
# ------------------------------

def load_active_contracts():
    """
    Load active NFL contracts from parquet.
    """
    file_path = "data/active_contracts.parquet"
    return pd.read_parquet(file_path)
