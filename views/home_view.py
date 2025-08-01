import streamlit as st
import pandas as pd

def show_home_view(coaching_df, stats_df):
    # ----------------------
    # Title & Intro
    # ----------------------
    st.title("Fantasy Football Draft Guide")

    st.markdown("""
    **Welcome to the Fantasy Football Draft Guide** — your one-stop tool to navigate the 2025 redraft season.

    This app combines **team, coach, and player-level insights** to help you draft smarter — all in one place instead of juggling multiple sites and spreadsheets. It was born out of my own frustration during drafts: I’d constantly flip between sources trying to piece together context about team trends, coaching tendencies, and player performance.

    - **Team View** shows which franchises consistently produce high fantasy output. I use this to spot not just above-average offenses, but also specialized strengths — like teams that might be mediocre overall yet elite in rushing or passing.

    - **Coach View** highlights how coaching changes — especially head coaches and offensive coordinators — influence fantasy production over time. I like to see whether a coach runs a balanced offense, leans run-heavy or pass-heavy, and how they historically treat certain positions like RBs or TEs.

    - **Player View** lets you dive into year-over-year player stats, and even zoom into specific seasons to explore weekly trends — perfect for finding late-round gems or players trending up (or down) at the end of a season. I also use this view to connect player performance to context — like if a WR’s production dipped after his QB got hurt.

    Fantasy success isn’t just about talent — it’s about context. Some players thrive immediately, while others break out only after the right coaching change or scheme shift. This guide helps you uncover those patterns so you can draft with confidence.
    """)


    # ----------------------
    # How to Use Section
    # ----------------------
    st.subheader("How to Use This App")
    st.markdown("""
    1. **Start with Team View** – Explore which teams consistently deliver fantasy production and compare year-over-year trends.  
    2. **Check Coach View** – See how head coaches and offensive coordinators have influenced fantasy production across different teams and seasons.  
    3. **Dive into Player View** – Analyze individual player stats across multiple seasons, and even zoom into weekly trends for deeper insights.  
    4. **Hover for Details** – On any chart, hover over a year (or week) to see quick details — including coaching staff, fantasy points, rankings, and more contextual data for that point in time.
    """)

    # ----------------------
    # 2024 Season Overview
    # ----------------------
    st.subheader("2024 Season Overview")

    # ----------------------------
    # Normalize Rams Abbreviation
    # ----------------------------
    coaching_df = coaching_df.copy()
    coaching_df["Team Abbr"] = coaching_df["Team Abbr"].replace(
        {"LA": "LAR", "STL": "LAR"}
    )
    # Ensure Rams get proper Team ID (18)
    coaching_df.loc[coaching_df["Team Abbr"] == "LAR", "Team ID"] = 18

    # ----------------------------
    # Filter 2024 Data
    # ----------------------------
    stats_2024 = stats_df[stats_df["season"] == 2024].copy()
    coaches_2024 = coaching_df[coaching_df["Season"] == 2024].copy()

    # ----------------------------
    # Aggregate Team Offensive Stats
    # ----------------------------
    team_agg = (
        stats_2024.groupby("team_id", as_index=False)
        .agg({
            "passing_yards": "sum",
            "passing_tds": "sum",
            "rushing_yards": "sum",
            "rushing_tds": "sum"
        })
    )
    team_agg["total_offense_yards"] = team_agg["passing_yards"] + team_agg["rushing_yards"]
    team_agg["total_offense_rank"] = team_agg["total_offense_yards"].rank(
        method="min", ascending=False
    ).astype(int)

    # ----------------------------
    # Merge Head Coach (non-interim)
    # ----------------------------
    hc_data = coaches_2024[coaches_2024["Coach Type"] == "Head Coach"]
    team_agg = team_agg.merge(
        hc_data[["Team ID", "Coach"]].rename(columns={"Coach": "Head Coach"}),
        left_on="team_id",
        right_on="Team ID",
        how="left"
    ).drop(columns="Team ID")

    # ----------------------------
    # Merge Offensive Coordinator (non-interim)
    # ----------------------------
    oc_data = coaches_2024[coaches_2024["Coach Type"] == "Offensive Coordinator"]
    team_agg = team_agg.merge(
        oc_data[["Team ID", "Coach"]].rename(columns={"Coach": "Offensive Coordinator"}),
        left_on="team_id",
        right_on="Team ID",
        how="left"
    ).drop(columns="Team ID")

    # ----------------------------
    # Handle HC-as-OC Fallback
    # ----------------------------
    hc_playcallers = hc_data[hc_data["Playing Calling Duties"].str.lower() == "yes"]
    for idx, row in hc_playcallers.iterrows():
        team_id = row["Team ID"]
        if team_agg.loc[team_agg["team_id"] == team_id, "Offensive Coordinator"].isna().any():
            team_agg.loc[team_agg["team_id"] == team_id, "Offensive Coordinator"] = row["Coach"]

    # ----------------------------
    # Aggregate Interim Coaches (Combine Names)
    # ----------------------------
    # Interim Head Coaches
    interim_hc_combined = (
        coaches_2024[coaches_2024["Coach Type"] == "Interim Head Coach"]
        .groupby("Team ID")["Coach"]
        .apply(lambda names: ", ".join(names))
        .reset_index()
        .rename(columns={"Coach": "Interim HC"})
    )

    # Interim Offensive Coordinators
    interim_oc_combined = (
        coaches_2024[coaches_2024["Coach Type"] == "Interim Offensive Coordinator"]
        .groupby("Team ID")["Coach"]
        .apply(lambda names: ", ".join(names))
        .reset_index()
        .rename(columns={"Coach": "Interim OC"})
    )

    # Merge aggregated interim HCs and OCs
    team_agg = team_agg.merge(interim_hc_combined, left_on="team_id", right_on="Team ID", how="left").drop(columns="Team ID")
    team_agg = team_agg.merge(interim_oc_combined, left_on="team_id", right_on="Team ID", how="left").drop(columns="Team ID")

    # Fill blanks with "-"
    team_agg["Interim HC"] = team_agg["Interim HC"].fillna("-")
    team_agg["Interim OC"] = team_agg["Interim OC"].fillna("-")

    # ----------------------------
    # Merge Team Abbreviation for Display
    # ----------------------------
    team_agg = team_agg.merge(
        coaches_2024[["Team ID", "Team Abbr"]].drop_duplicates(),
        left_on="team_id",
        right_on="Team ID",
        how="left"
    ).rename(columns={"Team Abbr": "Team"}).drop(columns="Team ID")

    # ----------------------------
    # Sort and Reorder Columns
    # ----------------------------
    team_agg = team_agg.sort_values(by="total_offense_yards", ascending=False)

    team_agg = team_agg[
        [
            "Head Coach",
            "Offensive Coordinator",
            "Team",
            "team_id",
            "passing_yards",
            "passing_tds",
            "rushing_yards",
            "rushing_tds",
            "total_offense_yards",
            "total_offense_rank",
            "Interim HC",
            "Interim OC",
        ]
    ]

    # ----------------------------
    # Display Table
    # ----------------------------
    st.dataframe(team_agg, use_container_width=True, hide_index=True)

    # ----------------------------
    # Fantasy Points by Position (2024)
    # ----------------------------

    # Filter to 2024
    fantasy_2024 = stats_df[stats_df["season"] == 2024].copy()

    # Aggregate total fantasy points by team + position
    position_totals = (
        fantasy_2024.groupby(["team_id", "position"], as_index=False)["fantasy_points"]
        .sum()
    )

    # Pivot to get separate columns for QB, RB, WR, TE totals
    position_pivot = position_totals.pivot(
        index="team_id", columns="position", values="fantasy_points"
    ).reset_index()

    # Ensure all positions exist as columns
    for pos in ["QB", "RB", "WR", "TE"]:
        if pos not in position_pivot.columns:
            position_pivot[pos] = 0

    # Fill missing values with 0
    position_pivot = position_pivot.fillna(0)

    # Add ranks for each position (higher points = better rank)
    for pos in ["QB", "RB", "WR", "TE"]:
        rank_col = f"{pos} Rank"
        position_pivot[rank_col] = position_pivot[pos].rank(method="min", ascending=False).astype(int)

    # Merge with first table's coach/team data
    fantasy_table = position_pivot.merge(
        team_agg[["Head Coach", "Offensive Coordinator", "Team", "Interim HC", "Interim OC", "team_id"]],
        on="team_id",
        how="left"
    )

    # Sort by QB Rank ascending (best QB fantasy teams first)
    fantasy_table = fantasy_table.sort_values(by="QB Rank", ascending=True)



    # Reorder columns: Coaches, Team, Position Totals + Ranks, Interims
    fantasy_table = fantasy_table[
        [
            "Head Coach",
            "Offensive Coordinator",
            "Team",
            "QB", "QB Rank",
            "RB", "RB Rank",
            "WR", "WR Rank",
            "TE", "TE Rank",
            "Interim HC",
            "Interim OC",
        ]
    ]

    # Display Fantasy Points Table
    st.subheader("2024 Fantasy Points by Position")
    st.dataframe(fantasy_table, use_container_width=True, hide_index=True)

    # ----------------------------
    # Top 5 Fantasy Performers by Position (2024)
    # ----------------------------
    st.subheader("Top 5 Fantasy Performers by Position (2024)")

    # ---- Scoring Type Selector ----
    scoring_option = st.radio(
        "Select Scoring Metric:",
        options=[
            "Standard Points",
            "PPR Points",
            "Standard Points Per Game",
            "PPR Points Per Game",
        ],
        horizontal=True
    )

    # Map selection to column in stats_df
    metric_map = {
        "Standard Points": "fantasy_points",
        "PPR Points": "fantasy_points_ppr",
        "Standard Points Per Game": "fantasy_points_pg",
        "PPR Points Per Game": "fantasy_points_ppr_pg",
    }
    metric_col = metric_map[scoring_option]

    # ---- Filter 2024 data ----
    player_2024 = stats_df[stats_df["season"] == 2024].copy()

    # Remove anomalies: For per-game metrics, exclude players with <= 1 game
    if "Per Game" in scoring_option:
        player_2024 = player_2024[player_2024["games_played"] > 1]

    # Merge coaching info (HC and OC) from team_agg
    player_2024 = player_2024.merge(
        team_agg[["team_id", "Head Coach", "Offensive Coordinator", "Team"]],
        on="team_id",
        how="left"
    )

    # ---- Generate Top 5 per position ----
    top_tables = {}
    for pos in ["QB", "RB", "WR", "TE"]:
        pos_data = player_2024[player_2024["position"] == pos][
            ["player_display_name", "Head Coach", "Offensive Coordinator", "Team", metric_col]
        ].rename(columns={
            "player_display_name": "Player",
            metric_col: scoring_option  # Rename column to match selected metric
        })

        # Sort by metric descending
        pos_data = pos_data.sort_values(by=scoring_option, ascending=False)

        # Determine cutoff for top 5 (include ties)
        if len(pos_data) > 5:
            cutoff_value = pos_data.iloc[4][scoring_option]
            pos_data = pos_data[pos_data[scoring_option] >= cutoff_value]

        top_tables[pos] = pos_data

    # ---- Display tables: 2 per row ----
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Top QBs**")
        st.dataframe(top_tables["QB"], use_container_width=True, hide_index=True)

    with col2:
        st.markdown("**Top RBs**")
        st.dataframe(top_tables["RB"], use_container_width=True, hide_index=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown("**Top WRs**")
        st.dataframe(top_tables["WR"], use_container_width=True, hide_index=True)

    with col4:
        st.markdown("**Top TEs**")
        st.dataframe(top_tables["TE"], use_container_width=True, hide_index=True)

    # ----------------------------
    # Data Sources
    # ----------------------------
    st.markdown("""
    ---
    **Data Sources:**

    - [nfl_data_py](https://pypi.org/project/nfl-data-py/) – for all player, team, and weekly/seasonal statistics (2015–2024).  
    - Custom Coaching CSV – manually compiled dataset of head coaches and offensive coordinators (2015–2025) with play-calling details.
    """)









