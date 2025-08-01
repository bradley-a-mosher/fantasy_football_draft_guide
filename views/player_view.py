import streamlit as st
import pandas as pd
import altair as alt

def show_player_view(coaching_df, stats_df, weekly_df, active_rosters_df, active_contracts_df):
    st.title("Player View")
    # Normalize Rams abbreviation: LA -> LAR (Team ID 18)
    stats_df.loc[stats_df["recent_team"] == "LA", "recent_team"] = "LAR"
    weekly_df.loc[weekly_df["recent_team"] == "LA", "recent_team"] = "LAR"
    # ----------------------
    # Filter Active Rosters to Fantasy Positions
    # ----------------------
    fantasy_positions = ["QB", "RB", "WR", "TE"]
    rosters_filtered = active_rosters_df[active_rosters_df["position"].isin(fantasy_positions)].copy()

    # Build dropdown label
    rosters_filtered["Display"] = (
        rosters_filtered["player_name"] + " – " +
        rosters_filtered["team"] + " (" + rosters_filtered["position"] + ")"
    )

    # Dropdown
    selected_display = st.selectbox(
        "Select Player:",
        sorted(rosters_filtered["Display"])
    )

    # Extract player_id for selected player
    selected_row = rosters_filtered[rosters_filtered["Display"] == selected_display].iloc[0]
    player_id = selected_row["player_id"]  # Matches gsis_id in contracts_df

    # ----------------------
    # Contract & Draft Details
    # ----------------------
    contract_info = active_contracts_df[active_contracts_df["gsis_id"] == player_id]

    if not contract_info.empty:
        contract_row = contract_info.iloc[0]

        def safe_int(val):
            return int(val) if pd.notnull(val) else "N/A"

        def format_currency(val):
            return f"${int(val * 1_000_000):,}" if pd.notnull(val) else "N/A"

        # Contract
        year_signed = safe_int(contract_row["year_signed"])
        years = safe_int(contract_row["years"])
        value = format_currency(contract_row["value"])
        guaranteed = format_currency(contract_row["guaranteed"])

        # Draft
        draft_year = safe_int(contract_row["draft_year"])
        draft_team = contract_row["draft_team"] if pd.notnull(contract_row["draft_team"]) else "N/A"
        draft_round = safe_int(contract_row["draft_round"])
        draft_overall = safe_int(contract_row["draft_overall"])
    else:
        year_signed = years = value = guaranteed = "N/A"
        draft_year = draft_team = draft_round = draft_overall = "N/A"

    # ----------------------
    # Display Info (Cards)
    # ----------------------
    col1, col2 = st.columns(2)

    st.markdown("""
        <style>
        .card {
            background-color: #1e1e1e;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #444;
            margin-bottom: 20px;
        }
        .card h3 {
            margin-top: 0;
            margin-bottom: 10px;
            font-size: 22px;
            color: #ffffff;
        }
        .card p {
            margin: 4px 0;
            font-size: 16px;
            color: #dddddd;
        }
        .label {
            font-weight: bold;
            color: #ffffff;
        }
        </style>
    """, unsafe_allow_html=True)

    with col1:
        st.markdown(
            f"""
            <div class="card">
                <h3>Contract Details</h3>
                <p><span class="label">Year Signed:</span> {year_signed}</p>
                <p><span class="label">Years:</span> {years}</p>
                <p><span class="label">Value:</span> {value}</p>
                <p><span class="label">Guaranteed:</span> {guaranteed}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f"""
            <div class="card">
                <h3>Draft Details</h3>
                <p><span class="label">Drafted:</span> {draft_year}</p>
                <p><span class="label">Team:</span> {draft_team}</p>
                <p><span class="label">Round:</span> {draft_round}</p>
                <p><span class="label">Overall:</span> {draft_overall}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ----------------------
    # Player Seasonal Stats Table
    # ----------------------
    player_stats = stats_df[stats_df["player_id"] == player_id].copy()
    if player_stats.empty:
        st.info("No historical stats available for this player.")
        return

    # Compute total yards & TDs
    player_stats["total_yards"] = (
        player_stats["passing_yards"].fillna(0) +
        player_stats["rushing_yards"].fillna(0) +
        player_stats["receiving_yards"].fillna(0)
    )
    player_stats["total_tds"] = (
        player_stats["passing_tds"].fillna(0) +
        player_stats["rushing_tds"].fillna(0) +
        player_stats["receiving_tds"].fillna(0)
    )

    # Merge HC/OC from coaching_df
    coach_merge = coaching_df[
        coaching_df["Coach Type"].isin([
            "Head Coach", "Offensive Coordinator",
            "Interim Head Coach", "Interim Offensive Coordinator"
        ])
    ][["Season", "Team Abbr", "Coach", "Coach Type"]]

    coach_pivot = coach_merge.pivot_table(
        index=["Season", "Team Abbr"],
        columns="Coach Type",
        values="Coach",
        aggfunc="first"
    ).reset_index()

    # Rename interim columns for clarity
    coach_pivot.rename(columns={
        "Head Coach": "HC",
        "Offensive Coordinator": "OC",
        "Interim Head Coach": "Interim HC",
        "Interim Offensive Coordinator": "Interim OC"
    }, inplace=True)

    # Merge with player stats
    player_stats = player_stats.merge(
        coach_pivot,
        left_on=["season", "recent_team"],
        right_on=["Season", "Team Abbr"],
        how="left"
    )

    # Build coach label
    def build_coach_label(row):
        hc_str = f"HC: {row['HC']}" if pd.notnull(row['HC']) else ""
        if pd.notnull(row.get("Interim HC")):
            hc_str += f" (Interim: {row['Interim HC']})"
        oc_str = f"OC: {row['OC']}" if pd.notnull(row['OC']) else ""
        if pd.notnull(row.get("Interim OC")):
            oc_str += f" (Interim: {row['Interim OC']})"
        return ", ".join(filter(None, [hc_str, oc_str]))

    player_stats["Coach Label"] = player_stats.apply(build_coach_label, axis=1)

    # ----------------------
    # Tables
    # ----------------------
    common_cols = ["season", "recent_team", "HC", "OC"]

    tab1, tab2, tab3 = st.tabs([
        "Total Yards & TDs",
        "Fantasy Points (Standard)",
        "Fantasy Points (PPR)"
    ])

    with tab1:
        st.dataframe(
            player_stats[common_cols + ["total_yards", "total_tds"]]
            .rename(columns={
                "season": "Season",
                "recent_team": "Team",
                "total_yards": "Total Yards",
                "total_tds": "Total TDs"
            })
            .sort_values(by="Season", ascending=False),
            use_container_width=True,
            hide_index=True
        )

    with tab2:
        st.dataframe(
            player_stats[common_cols + ["fantasy_points", "fantasy_points_pg"]]
            .rename(columns={
                "season": "Season",
                "recent_team": "Team",
                "fantasy_points": "Fantasy Points",
                "fantasy_points_pg": "Fantasy Points/Game"
            })
            .sort_values(by="Season", ascending=False),
            use_container_width=True,
            hide_index=True
        )

    with tab3:
        st.dataframe(
            player_stats[common_cols + ["fantasy_points_ppr", "fantasy_points_ppr_pg"]]
            .rename(columns={
                "season": "Season",
                "recent_team": "Team",
                "fantasy_points_ppr": "PPR Points",
                "fantasy_points_ppr_pg": "PPR Points/Game"
            })
            .sort_values(by="Season", ascending=False),
            use_container_width=True,
            hide_index=True
        )

    # ----------------------
    # Line Charts with Radio Toggle
    # ----------------------
    chart_type = st.radio(
        "Select Chart Type:",
        ["Fantasy Points (Total)", "Fantasy Points per Game"],
        horizontal=True
    )

    if chart_type == "Fantasy Points (Total)":
        st.markdown("### Fantasy Points (Total) Over Seasons")

        total_df = pd.melt(
            player_stats,
            id_vars=["season", "Coach Label"],
            value_vars=["fantasy_points", "fantasy_points_ppr"],
            var_name="metric",
            value_name="value"
        )

        total_chart = alt.Chart(total_df).mark_line(point=True).encode(
            x=alt.X("season:O", title="Season"),
            y=alt.Y("value:Q", title="Fantasy Points"),
            color=alt.Color("metric:N", title="Metric"),
            tooltip=[
                alt.Tooltip("season", title="Season"),
                alt.Tooltip("Coach Label", title="Coaches"),
                alt.Tooltip("value", title="Fantasy Points")
            ]
        )

        st.altair_chart(total_chart, use_container_width=True)

    else:
        st.markdown("### Fantasy Points per Game Over Seasons")

        pg_df = pd.melt(
            player_stats,
            id_vars=["season", "Coach Label"],
            value_vars=["fantasy_points_pg", "fantasy_points_ppr_pg"],
            var_name="metric",
            value_name="value"
        )

        pg_chart = alt.Chart(pg_df).mark_line(point=True).encode(
            x=alt.X("season:O", title="Season"),
            y=alt.Y("value:Q", title="Fantasy Points/Game"),
            color=alt.Color("metric:N", title="Metric"),
            tooltip=[
                alt.Tooltip("season", title="Season"),
                alt.Tooltip("Coach Label", title="Coaches"),
                alt.Tooltip("value", title="Fantasy Points/Game")
            ]
        )

        st.altair_chart(pg_chart, use_container_width=True)

    # -------------------------------------------------
    # Positional Usage Bar Chart (No League Avg, % scale for RB/WR/TE)
    # -------------------------------------------------
    position = player_stats.iloc[0]["position"]

    y_field, y_title, chart_title = None, None, None
    bar_data = None

    # QB: Attempts/Game
    if position == "QB":
        bar_data = player_stats.copy()
        bar_data["Attempts/Game"] = (
            bar_data["attempts"].fillna(0) / bar_data["games_played"].replace(0, 1)
        )
        y_field = "Attempts/Game"
        y_title = "Passing Attempts per Game"
        chart_title = "Passing Volume Trends"

        y_scale = alt.Scale()  # dynamic scale for attempts

    # RB: Usage %
    elif position == "RB":
        bar_data = player_stats.copy()

        # Calculate team total yards
        team_totals = stats_df.groupby(["season", "recent_team"])[
            ["passing_yards", "rushing_yards", "receiving_yards"]
        ].sum().reset_index()
        team_totals["team_total_yards"] = (
            team_totals["passing_yards"] + team_totals["rushing_yards"] + team_totals["receiving_yards"]
        )

        bar_data = bar_data.merge(
            team_totals[["season", "recent_team", "team_total_yards"]],
            on=["season", "recent_team"],
            how="left"
        )

        bar_data["Usage %"] = (bar_data["total_yards"] / bar_data["team_total_yards"]) * 100
        y_field = "Usage %"
        y_title = "Usage (% of Team Total Offense)"
        chart_title = "Usage in Team Total Offense"

        y_scale = alt.Scale(domain=[0, 100])  # fixed to 100%

    # WR: Target Share %
    elif position == "WR":
        bar_data = player_stats.copy()

        team_targets = stats_df.groupby(["season", "recent_team"])["targets"].sum().reset_index()
        team_targets.rename(columns={"targets": "team_targets"}, inplace=True)

        bar_data = bar_data.merge(team_targets, on=["season", "recent_team"], how="left")

        bar_data["Target Share %"] = (bar_data["targets"] / bar_data["team_targets"]) * 100
        y_field = "Target Share %"
        y_title = "Target Share (%)"
        chart_title = "Target Share Trends"

        y_scale = alt.Scale(domain=[0, 100])  # fixed to 100%

    # TE: Target Share %
    elif position == "TE":
        bar_data = player_stats.copy()

        team_targets = stats_df.groupby(["season", "recent_team"])["targets"].sum().reset_index()
        team_targets.rename(columns={"targets": "team_targets"}, inplace=True)

        bar_data = bar_data.merge(team_targets, on=["season", "recent_team"], how="left")

        bar_data["Target Share %"] = (bar_data["targets"] / bar_data["team_targets"]) * 100
        y_field = "Target Share %"
        y_title = "Target Share (%)"
        chart_title = "Target Share Trends"

        y_scale = alt.Scale(domain=[0, 100])  # fixed to 100%

    # Plot bar chart
    if bar_data is not None and y_field in bar_data.columns:
        st.markdown(f"### {chart_title}")

        bar_chart = alt.Chart(bar_data).mark_bar().encode(
            x=alt.X("season:O", title="Season"),
            y=alt.Y(f"{y_field}:Q", title=y_title, scale=y_scale),
            tooltip=[
                alt.Tooltip("season", title="Season"),
                alt.Tooltip(f"{y_field}", title=y_title)
            ]
        ).properties(
            width="container",
            height=300
        )

        st.altair_chart(bar_chart, use_container_width=True)



    # -------------------------------------------------
    # Weekly Fantasy Points Chart (2024 Season)
    # -------------------------------------------------
    st.markdown("### Weekly Fantasy Points (2024 Season)")

    weekly_stats = weekly_df[
        (weekly_df["player_id"] == player_id) &
        (weekly_df["season"] == 2024)
    ].copy()

    if weekly_stats.empty:
        st.info("No weekly data available for 2024 season.")
    else:
        weekly_stats = weekly_stats.merge(
            coach_pivot,
            left_on=["season", "recent_team"],
            right_on=["Season", "Team Abbr"],
            how="left"
        )
        weekly_stats["Coach Label"] = weekly_stats.apply(build_coach_label, axis=1)

        weekly_melted = pd.melt(
            weekly_stats,
            id_vars=["week", "Coach Label"],
            value_vars=["fantasy_points", "fantasy_points_ppr"],
            var_name="metric",
            value_name="value"
        )

        metric_map = {
            "fantasy_points": "Standard",
            "fantasy_points_ppr": "PPR"
        }
        weekly_melted["metric"] = weekly_melted["metric"].map(metric_map)

        weekly_chart = alt.Chart(weekly_melted).mark_line(point=True).encode(
            x=alt.X("week:O", title="Week"),
            y=alt.Y("value:Q", title="Fantasy Points"),
            color="metric:N",
            tooltip=[
                alt.Tooltip("week", title="Week"),
                alt.Tooltip("Coach Label", title="Coaches"),
                alt.Tooltip("value", title="Fantasy Points")
            ]
        ).properties(
            width="container",
            height=300
        )

        st.altair_chart(weekly_chart, use_container_width=True)
