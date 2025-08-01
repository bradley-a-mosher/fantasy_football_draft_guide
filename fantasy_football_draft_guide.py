import streamlit as st
from utils.data_loader import (
    load_season_stats,
    load_coaching_data,
    load_active_rosters,
    load_active_contracts
)
from views.overview_view import show_overview_view
from views.team_view import show_team_view
from views.coach_view import show_coach_view
from views.player_view import show_player_view

# ----------------------
# Initialize Session State
# ----------------------
if "view" not in st.session_state:
    st.session_state.view = "overview"
if "selected_team" not in st.session_state:
    st.session_state.selected_team = None
if "selected_coach" not in st.session_state:
    st.session_state.selected_coach = None
if "player_selected" not in st.session_state:
    st.session_state.player_selected = None

# ----------------------
# Load Data
# ----------------------
def load_data():
    """
    Loads all required datasets:
    - Coaching data (CSV)
    - Season stats (Parquet)
    - Weekly stats (Parquet)
    - Active rosters (Parquet)
    - Active contracts (Parquet)
    """
    coaching_df = load_coaching_data()                  # Coaching data
    season_stats_df = load_season_stats(level="season")  # Aggregated season stats
    weekly_stats_df = load_season_stats(level="weekly")  # Weekly stats
    rosters_df = load_active_rosters()                   # Active rosters
    contracts_df = load_active_contracts()               # Active contracts

    return coaching_df, season_stats_df, weekly_stats_df, rosters_df, contracts_df

# Load everything at once
coaching_df, stats_df, weekly_df, rosters_df, contracts_df = load_data()

# ----------------------
# Sidebar Navigation
# ----------------------
view_choice = st.sidebar.radio(
    "Navigate to:",
    options=["Overview", "Team View", "Coach View", "Player View"],
    index=["overview", "team", "coach", "player"].index(st.session_state.view)
)

# Sync sidebar selection with session state
if view_choice == "Overview":
    st.session_state.view = "overview"
elif view_choice == "Team View":
    st.session_state.view = "team"
elif view_choice == "Coach View":
    st.session_state.view = "coach"
elif view_choice == "Player View":
    st.session_state.view = "player"

# ----------------------
# Render the Correct View
# ----------------------
if st.session_state.view == "overview":
    show_overview_view()

elif st.session_state.view == "team":
    show_team_view(coaching_df, stats_df)

elif st.session_state.view == "coach":
    show_coach_view(coaching_df, stats_df)

elif st.session_state.view == "player":
    show_player_view(coaching_df, stats_df, weekly_df, rosters_df, contracts_df)
