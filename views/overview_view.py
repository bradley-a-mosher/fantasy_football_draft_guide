import streamlit as st
import pandas as pd

@st.cache_data
def load_season_stats():
    return pd.read_parquet("data/season_stats.parquet")

@st.cache_data
def load_coaching_data():
    return pd.read_csv("utils/nfl_coaching_data - Coaching Staff.csv")

def show_overview_view():
    st.title("Overview")

    # ----------------------
    # Load and Clean Data
    # ----------------------
    season_stats = load_season_stats()
    coaching_df = load_coaching_data()

    # Standardize team abbreviations (handle relocations)
    team_abbr_map = {
        "LA": "LAR",   # Rams
        "STL": "LAR",  # Old Rams
        "SD": "LAC",   # Old Chargers
        "OAK": "LV"    # Old Raiders
    }
    season_stats["recent_team"] = season_stats["recent_team"].replace(team_abbr_map)
    coaching_df["Team Abbr"] = coaching_df["Team Abbr"].replace(team_abbr_map)

    # ----------------------
    # Tabs
    # ----------------------
    tab_team, tab_coach, tab_player = st.tabs(["Team", "Coach", "Player"])

    # ==============================================================
    # TEAM TAB
    # ==============================================================
    with tab_team:
        st.subheader("Team Overview")

        # --- Season Selector ---
        available_seasons = sorted(season_stats["season"].unique(), reverse=True)
        selected_season = st.selectbox("Select Season", available_seasons, index=0, key="team_season_select")

        # Filter season stats
        team_df = season_stats[season_stats["season"] == selected_season]

        # --- Aggregate Team Stats ---
        team_agg = team_df.groupby(["recent_team"], as_index=False).agg({
            "passing_yards": "sum",
            "passing_tds": "sum",
            "attempts": "sum",
            "completions": "sum",
            "rushing_yards": "sum",
            "rushing_tds": "sum",
            "carries": "sum"
        })

        # --- Calculate Metrics ---
        team_agg["completion_pct"] = (team_agg["completions"] / team_agg["attempts"] * 100).round(1)
        team_agg["yards_per_attempt"] = (team_agg["rushing_yards"] / team_agg["carries"]).round(1)
        team_agg["total_offense"] = team_agg["passing_yards"] + team_agg["rushing_yards"]
        team_agg["total_tds"] = team_agg["passing_tds"] + team_agg["rushing_tds"]
        team_agg["total_plays"] = team_agg["attempts"] + team_agg["carries"]
        team_agg["pass_pct"] = ((team_agg["attempts"] / team_agg["total_plays"]) * 100).round(2)
        team_agg["run_pct"] = ((team_agg["carries"] / team_agg["total_plays"]) * 100).round(2)

        # ==============================================================
        # Merge Coaching Data (Grouped by Role)
        # ==============================================================
        coaches_season = coaching_df[coaching_df["Season"] == selected_season]

        # --- Helper: group and join names ---
        def group_coaches(df, role):
            role_df = df[df["Coach Type"] == role].groupby("Team Abbr")["Coach"].agg(
                lambda x: ", ".join(sorted(set(x.dropna())))
            )
            return role_df.reset_index()

        # Group by roles
        hc_df = group_coaches(coaches_season, "Head Coach")
        oc_df = group_coaches(coaches_season, "Offensive Coordinator")
        ihc_df = group_coaches(coaches_season, "Interim Head Coach")
        ioc_df = group_coaches(coaches_season, "Interim Offensive Coordinator")

        # --- Merge into team_agg ---
        team_agg = team_agg.merge(hc_df, how="left", left_on="recent_team", right_on="Team Abbr").rename(
            columns={"Coach": "HC"}
        ).drop(columns="Team Abbr")

        team_agg = team_agg.merge(oc_df, how="left", left_on="recent_team", right_on="Team Abbr").rename(
            columns={"Coach": "OC"}
        ).drop(columns="Team Abbr")

        team_agg = team_agg.merge(ihc_df, how="left", left_on="recent_team", right_on="Team Abbr").rename(
            columns={"Coach": "Interim HC"}
        ).drop(columns="Team Abbr")

        team_agg = team_agg.merge(ioc_df, how="left", left_on="recent_team", right_on="Team Abbr").rename(
            columns={"Coach": "Interim OC"}
        ).drop(columns="Team Abbr")

        # ==============================================================
        # Handle HC as OC (Play Calling Duties = Yes)
        # ==============================================================
        play_calling_hc = coaches_season[
            (coaches_season["Coach Type"] == "Head Coach") &
            (coaches_season["Playing Calling Duties"] == "Yes")
        ][["Team Abbr", "Coach"]]

        for team, coach in play_calling_hc.values:
            team_agg.loc[
                (team_agg["recent_team"] == team) & (team_agg["OC"].isna()),
                "OC"
            ] = coach

        # ==============================================================
        # Mark HC/OC with * if interim exists
        # ==============================================================
        team_agg["HC"] = team_agg.apply(
            lambda x: f"{x['HC']}*" if pd.notna(x["Interim HC"]) and x["Interim HC"] != "-" else x["HC"],
            axis=1
        )
        team_agg["OC"] = team_agg.apply(
            lambda x: f"{x['OC']}*" if pd.notna(x["Interim OC"]) and x["Interim OC"] != "-" else x["OC"],
            axis=1
        )

        # Fill missing interim and other coach roles with "-"
        for col in ["HC", "OC", "Interim HC", "Interim OC"]:
            team_agg[col] = team_agg[col].fillna("-")

        # If OC is missing but HC exists, set OC = HC (for dual-role coaches)
        team_agg.loc[
            (team_agg["OC"] == "-") & (team_agg["HC"] != "-"),
            "OC"
        ] = team_agg["HC"]



        # ==============================================================
        # Rename columns for clean display
        # ==============================================================
        team_agg = team_agg.rename(columns={
            "recent_team": "Team",
            "passing_yards": "Pass Yards",
            "passing_tds": "Pass TDs",
            "attempts": "Pass Attempts",
            "completions": "Completions",
            "rushing_yards": "Rush Yards",
            "rushing_tds": "Rush TDs",
            "carries": "Carries",
            "completion_pct": "Completion %",
            "yards_per_attempt": "Yards/Attempt",
            "total_offense": "Total Yards",
            "total_tds": "Total TDs",
            "total_plays": "Total Plays",
            "pass_pct": "Pass %",
            "run_pct": "Run %"
        })

        # ==============================================================
        # Sub-tabs for Overall, Passing, Rushing
        # ==============================================================
        subtab_overall, subtab_passing, subtab_rushing = st.tabs(["Overall Offense", "Passing", "Rushing"])

        # Overall Offense tab (unchanged order)
        with subtab_overall:
            display_cols_overall = [
                "Team", "HC", "OC", "Total Yards", "Total TDs", "Total Plays", "Pass %", "Run %", "Interim HC", "Interim OC"
            ]
            st.dataframe(team_agg[display_cols_overall].sort_values(by="Total Yards", ascending=False).reset_index(drop=True),
                         use_container_width=True, hide_index=True)

        # Passing tab (Attempts + Completions moved after OC)
        with subtab_passing:
            display_cols_passing = [
                "Team", "HC", "OC", "Pass Attempts", "Completions", "Pass Yards", "Pass TDs", "Completion %", "Interim HC", "Interim OC"
            ]
            st.dataframe(team_agg[display_cols_passing].sort_values(by="Pass Yards", ascending=False).reset_index(drop=True),
                         use_container_width=True, hide_index=True)

        # Rushing tab (Carries moved after OC)
        with subtab_rushing:
            display_cols_rushing = [
                "Team", "HC", "OC", "Carries", "Rush Yards", "Rush TDs", "Yards/Attempt", "Interim HC", "Interim OC"
            ]
            st.dataframe(team_agg[display_cols_rushing].sort_values(by="Rush Yards", ascending=False).reset_index(drop=True),
                         use_container_width=True, hide_index=True)

        # Legend
        st.caption("* Coach was replaced mid-season")

        # ==============================================================
        # COACH TAB
        # ==============================================================
        with tab_coach:
            st.subheader("Coach Overview")

            # --- Select Season ---
            available_seasons = sorted(season_stats["season"].unique(), reverse=True)
            selected_season = st.selectbox("Select Season", available_seasons, index=0, key="coach_season_select")

            # --- Filter data for selected season ---
            season_coaches = coaching_df[coaching_df["Season"] == selected_season].copy()

            # Merge season_stats with coaches (for all teams in season)
            coach_stats = season_stats[season_stats["season"] == selected_season].copy()

            # ----------------------
            # Get HC, OC, Interim HC, Interim OC per team
            # ----------------------
            def get_coach_by_role(df, role):
                return (
                    df[df["Coach Type"] == role]
                    .groupby("Team Abbr")["Coach"]
                    .agg(lambda x: ", ".join(sorted(set(x.dropna()))))
                    .reset_index()
                )

            hc_df = get_coach_by_role(season_coaches, "Head Coach")
            oc_df = get_coach_by_role(season_coaches, "Offensive Coordinator")
            ihc_df = get_coach_by_role(season_coaches, "Interim Head Coach")
            ioc_df = get_coach_by_role(season_coaches, "Interim Offensive Coordinator")

            # Merge coaches into stats
            coach_stats = coach_stats.merge(hc_df, how="left", left_on="recent_team", right_on="Team Abbr").rename(
                columns={"Coach": "HC"}
            ).drop(columns="Team Abbr")

            coach_stats = coach_stats.merge(oc_df, how="left", left_on="recent_team", right_on="Team Abbr").rename(
                columns={"Coach": "OC"}
            ).drop(columns="Team Abbr")

            coach_stats = coach_stats.merge(ihc_df, how="left", left_on="recent_team", right_on="Team Abbr").rename(
                columns={"Coach": "Interim HC"}
            ).drop(columns="Team Abbr")

            coach_stats = coach_stats.merge(ioc_df, how="left", left_on="recent_team", right_on="Team Abbr").rename(
                columns={"Coach": "Interim OC"}
            ).drop(columns="Team Abbr")

            # ==============================================================
            # Handle HC as OC (Play Calling Duties = Yes)
            # ==============================================================
            play_calling_hc = season_coaches[
                (season_coaches["Coach Type"] == "Head Coach") &
                (season_coaches["Playing Calling Duties"] == "Yes")
            ][["Team Abbr", "Coach"]]

            # Update OC column to match HC for these teams
            for team, coach in play_calling_hc.values:
                coach_stats.loc[coach_stats["recent_team"] == team, "OC"] = coach

            # If OC is still "-" but HC exists, fallback to HC
            coach_stats.loc[
                (coach_stats["OC"].isna()) & (coach_stats["HC"].notna()),
                "OC"
            ] = coach_stats["HC"]

            # ==============================================================
            # Mark HC/OC with * if interim exists
            # ==============================================================
            coach_stats["HC"] = coach_stats.apply(
                lambda x: f"{x['HC']}*" if pd.notna(x["Interim HC"]) and x["Interim HC"] != "-" else x["HC"],
                axis=1
            )
            coach_stats["OC"] = coach_stats.apply(
                lambda x: f"{x['OC']}*" if pd.notna(x["Interim OC"]) and x["Interim OC"] != "-" else x["OC"],
                axis=1
            )

            # Fill missing coaches with "-"
            for col in ["HC", "OC", "Interim HC", "Interim OC"]:
                coach_stats[col] = coach_stats[col].fillna("-")

            # ----------------------
            # Filter fantasy-relevant positions (QB/RB/WR/TE) + trick plays
            # ----------------------
            fantasy_positions = ["QB", "RB", "WR", "TE"]
            coach_stats = coach_stats[
                (coach_stats["position"].isin(fantasy_positions)) |
                (coach_stats[["attempts", "carries", "targets"]].sum(axis=1) > 0)
            ]

            # ----------------------
            # Create Tabs
            # ----------------------
            subtab_overall, subtab_passing, subtab_rushing, subtab_receiving, subtab_fantasy = st.tabs(
                ["Overall Offense", "Passing", "Rushing", "Receiving", "Fantasy"]
            )

            # ==============================================================
            # Overall Offense Tab
            # ==============================================================
            with subtab_overall:
                agg = coach_stats.groupby(["recent_team", "HC", "OC", "Interim HC", "Interim OC"], as_index=False).agg({
                    "passing_yards": "sum",
                    "passing_tds": "sum",
                    "attempts": "sum",
                    "completions": "sum",
                    "rushing_yards": "sum",
                    "rushing_tds": "sum",
                    "carries": "sum",
                    "team_total_plays": "sum",
                    "team_pass_attempts": "sum"
                })

                # Derived metrics
                agg["Total Yards"] = agg["passing_yards"] + agg["rushing_yards"]
                agg["Total TDs"] = agg["passing_tds"] + agg["rushing_tds"]
                agg["Total Plays"] = agg["team_total_plays"]
                agg["Pass %"] = (agg["team_pass_attempts"] / agg["team_total_plays"] * 100).round(2)
                agg["Run %"] = 100 - agg["Pass %"]

                agg.rename(columns={"recent_team": "Team"}, inplace=True)

                display_cols_overall = [
                    "Team", "HC", "OC", "Total Yards", "Total TDs", "Total Plays", "Pass %", "Run %", "Interim HC", "Interim OC"
                ]
                st.dataframe(
                    agg[display_cols_overall]
                    .sort_values(by=["Total Yards"], ascending=False)
                    .reset_index(drop=True),
                    use_container_width=True,
                    hide_index=True
                )

            # ==============================================================
            # Passing Tab
            # ==============================================================
            with subtab_passing:
                passing = coach_stats.groupby(
                    ["recent_team", "HC", "OC", "Interim HC", "Interim OC", "player_display_name", "position"],
                    as_index=False
                ).agg({
                    "attempts": "sum",
                    "completions": "sum",
                    "passing_tds": "sum",
                    "interceptions": "sum"
                })

                passing = passing[passing["attempts"] > 0]  # Filter out zero attempts
                passing["Completion %"] = (passing["completions"] / passing["attempts"] * 100).round(1)

                passing.rename(columns={
                    "recent_team": "Team",
                    "player_display_name": "Player",
                    "position": "Position",
                    "attempts": "Pass Attempts",
                    "completions": "Completions",
                    "passing_tds": "Pass TDs",
                    "interceptions": "INTs"
                }, inplace=True)

                display_cols_passing = [
                    "Team", "HC", "OC", "Player", "Position",
                    "Pass Attempts", "Completions", "Completion %", "Pass TDs", "INTs", "Interim HC", "Interim OC"
                ]
                st.dataframe(
                    passing[display_cols_passing]
                    .sort_values(by=["Pass Attempts"], ascending=False)
                    .reset_index(drop=True),
                    use_container_width=True,
                    hide_index=True
                )

            # ==============================================================
            # Rushing Tab
            # ==============================================================
            with subtab_rushing:
                rushing = coach_stats.groupby(
                    ["recent_team", "HC", "OC", "Interim HC", "Interim OC", "player_display_name", "position"],
                    as_index=False
                ).agg({
                    "carries": "sum",
                    "rushing_yards": "sum",
                    "rushing_tds": "sum",
                    "team_total_plays": "sum"
                })

                rushing = rushing[rushing["carries"] > 0]  # Filter out zero carries
                rushing["Yards/Attempt"] = (rushing["rushing_yards"] / rushing["carries"]).round(1)
                total_team_carries = rushing.groupby(["recent_team"])["carries"].transform("sum")
                rushing["Usage %"] = (rushing["carries"] / total_team_carries * 100).round(1)

                rushing.rename(columns={
                    "recent_team": "Team",
                    "player_display_name": "Player",
                    "position": "Position",
                    "carries": "Carries",
                    "rushing_yards": "Rush Yards",
                    "rushing_tds": "Rush TDs"
                }, inplace=True)

                display_cols_rushing = [
                    "Team", "HC", "OC", "Player", "Position",
                    "Carries", "Rush Yards", "Yards/Attempt", "Usage %", "Rush TDs", "Interim HC", "Interim OC"
                ]
                st.dataframe(
                    rushing[display_cols_rushing]
                    .sort_values(by=["Carries"], ascending=False)
                    .reset_index(drop=True),
                    use_container_width=True,
                    hide_index=True
                )

            # ==============================================================
            # Receiving Tab
            # ==============================================================
            with subtab_receiving:
                receiving = coach_stats.groupby(
                    ["recent_team", "HC", "OC", "Interim HC", "Interim OC", "player_display_name", "position"],
                    as_index=False
                ).agg({
                    "targets": "sum",
                    "receptions": "sum",
                    "receiving_yards": "sum",
                    "receiving_tds": "sum"
                })

                receiving = receiving[receiving["receptions"] > 0]  # Filter out zero receptions
                receiving["Catch %"] = (receiving["receptions"] / receiving["targets"] * 100).round(1)
                total_team_targets = receiving.groupby(["recent_team"])["targets"].transform("sum")
                receiving["Target Share %"] = (receiving["targets"] / total_team_targets * 100).round(1)

                receiving.rename(columns={
                    "recent_team": "Team",
                    "player_display_name": "Player",
                    "position": "Position",
                    "targets": "Targets",
                    "receptions": "Receptions",
                    "receiving_yards": "Receiving Yards",
                    "receiving_tds": "Receiving TDs"
                }, inplace=True)

                display_cols_receiving = [
                    "Team", "HC", "OC", "Player", "Position",
                    "Targets", "Receptions", "Catch %", "Target Share %", "Receiving Yards", "Receiving TDs", "Interim HC", "Interim OC"
                ]
                st.dataframe(
                    receiving[display_cols_receiving]
                    .sort_values(by=["Targets"], ascending=False)
                    .reset_index(drop=True),
                    use_container_width=True,
                    hide_index=True
                )

            # ==============================================================
            # Fantasy Tab (League-Wide Overall Ranks)
            # ==============================================================
            with subtab_fantasy:
                # --- Compute league-wide totals for the selected season only ---
                league_ranks = season_stats[season_stats["season"] == selected_season].groupby(
                    ["player_display_name"], as_index=False
                ).agg({
                    "fantasy_points": "sum",
                    "fantasy_points_ppr": "sum"
                })

                # Overall ranks across ALL players (not positional) for selected season
                league_ranks["Std Rank"] = league_ranks["fantasy_points"] \
                    .rank(method="min", ascending=False).astype(int)
                league_ranks["PPR Rank"] = league_ranks["fantasy_points_ppr"] \
                    .rank(method="min", ascending=False).astype(int)

                # --- Coach-specific fantasy data (filtered to selected season already) ---
                fantasy = coach_stats.groupby(
                    ["recent_team", "HC", "OC", "Interim HC", "Interim OC", "player_display_name", "position"],
                    as_index=False
                ).agg({
                    "fantasy_points": "sum",
                    "fantasy_points_pg": "mean",
                    "fantasy_points_ppr": "sum",
                    "fantasy_points_ppr_pg": "mean"
                })

                # Filter out players with 0 points
                fantasy = fantasy[(fantasy["fantasy_points"] > 0) | (fantasy["fantasy_points_ppr"] > 0)]

                # Merge in league-wide ranks (already filtered to selected season)
                fantasy = fantasy.merge(
                    league_ranks[["player_display_name", "Std Rank", "PPR Rank"]],
                    on="player_display_name",
                    how="left"
                ).drop_duplicates()

                # --- Rename for clean display ---
                fantasy.rename(columns={
                    "recent_team": "Team",
                    "player_display_name": "Player",
                    "position": "Position",
                    "fantasy_points": "Standard Total Points",
                    "fantasy_points_pg": "Standard PPG",
                    "fantasy_points_ppr": "PPR Total Points",
                    "fantasy_points_ppr_pg": "PPR PPG"
                }, inplace=True)

                # Ensure renamed columns exist before display
                required_cols = [
                    "Team", "HC", "OC", "Player", "Position",
                    "Standard Total Points", "Standard PPG", "Std Rank",
                    "PPR Total Points", "PPR PPG", "PPR Rank", "Interim HC", "Interim OC"
                ]
                missing_cols = [c for c in required_cols if c not in fantasy.columns]
                if missing_cols:
                    st.error(f"Missing columns in fantasy dataframe: {missing_cols}")
                else:
                    st.dataframe(
                        fantasy[required_cols]
                        .sort_values(by=["Standard Total Points"], ascending=False)
                        .reset_index(drop=True),
                        use_container_width=True,
                        hide_index=True
                    )






    # ==============================================================
    # PLAYER TAB
    # ==============================================================
    with tab_player:
        st.subheader("Player Overview")
        st.info("Player tab is under construction.")
