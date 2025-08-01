import streamlit as st
import pandas as pd
import altair as alt

def show_team_view(coaching_df, stats_df):
    st.title("NFL Team Fantasy Overview (2015–2025)")

    # ----------------------
    # Team Abbreviation Fixes
    # ----------------------
    team_abbr_mapping = {
        # Rams historical abbreviations
        "LA": "LAR",
        "STL": "LAR",
        # Chargers historical abbreviations
        "SD": "LAC",
        # Raiders historical abbreviations
        "OAK": "LV"
    }

    # Normalize team abbreviations in both datasets
    stats_df["recent_team"] = stats_df["recent_team"].replace(team_abbr_mapping)
    coaching_df["Team Abbr"] = coaching_df["Team Abbr"].replace(team_abbr_mapping)

    # Ensure Rams have correct team_id (18)
    stats_df.loc[stats_df["recent_team"] == "LAR", "team_id"] = 18
    coaching_df.loc[coaching_df["Team Abbr"] == "LAR", "Team ID"] = 18

    # Remove duplicates after mapping
    stats_df = stats_df.drop_duplicates()
    coaching_df = coaching_df.drop_duplicates()

    # ----------------------
    # Helper: Get HC/OC/Interim Coaches for Tooltip
    # ----------------------
    def get_coach_roles(team_abbr, season):
        season_data = coaching_df[
            (coaching_df["Team Abbr"] == team_abbr) &
            (coaching_df["Season"] == season)
        ]
        hc = season_data[season_data["Coach Type"] == "Head Coach"]["Coach"].values
        oc = season_data[season_data["Coach Type"] == "Offensive Coordinator"]["Coach"].values
        interim_hc = season_data[season_data["Coach Type"] == "Interim Head Coach"]["Coach"].values
        interim_oc = season_data[season_data["Coach Type"] == "Interim Offensive Coordinator"]["Coach"].values

        return {
            "HC": hc[0] if len(hc) > 0 else "N/A",
            "OC": oc[0] if len(oc) > 0 else "N/A",
            "Interim HC": interim_hc[0] if len(interim_hc) > 0 else "N/A",
            "Interim OC": interim_oc[0] if len(interim_oc) > 0 else "N/A"
        }

    # ----------------------
    # CSS for Overview Boxes
    # ----------------------
    st.markdown(
        """
        <style>
        .equal-boxes {
            display: flex;
            gap: 20px;
            margin-top: 10px;
            margin-bottom: 20px;
        }
        .box-style {
            flex: 1;
            min-height: 160px;
            border: 1px solid #666666;
            border-radius: 6px;
            padding: 12px;
            background-color: #1e1e1e;
            text-align: center;
        }
        .box-style h3 {
            margin-top: 0;
            margin-bottom: 12px;
        }
        .metric-container {
            display: flex;
            justify-content: space-around;
            text-align: center;
        }
        .metric {
            flex: 1;
        }
        .metric-label {
            font-size: 14px;
            color: #cccccc;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #ffffff;
            margin-top: 4px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # ----------------------
    # Prepare 2024 Overview Data
    # ----------------------
    stats_2024 = stats_df[stats_df["season"] == 2024]
    team_totals_2024 = stats_2024.groupby("recent_team").agg(
        pass_yards=("passing_yards", "sum"),
        rush_yards=("rushing_yards", "sum")
    ).reset_index()

    team_totals_2024["total_yards"] = (
        team_totals_2024["pass_yards"] + team_totals_2024["rush_yards"]
    )

    # Compute ranks
    team_totals_2024["pass_rank"] = team_totals_2024["pass_yards"].rank(ascending=False, method="min").astype(int)
    team_totals_2024["rush_rank"] = team_totals_2024["rush_yards"].rank(ascending=False, method="min").astype(int)
    team_totals_2024["total_rank"] = team_totals_2024["total_yards"].rank(ascending=False, method="min").astype(int)

    # ----------------------
    # Dropdown (deduplicated)
    # ----------------------
    team_options = (
        coaching_df[["Team Abbr", "Team"]]
        .drop_duplicates(subset=["Team Abbr"])
        .sort_values("Team Abbr")
    )
    team_abbr = st.selectbox("Select a Team", team_options["Team Abbr"])
    team_name = team_options.loc[team_options["Team Abbr"] == team_abbr, "Team"].values[0]

    # ----------------------
    # Get 2024 ranks for selected team
    # ----------------------
    team_rank_row = team_totals_2024[team_totals_2024["recent_team"] == team_abbr].iloc[0]

    # ----------------------
    # Get 2025 Coaching Staff with hire year (promotion-aware)
    # ----------------------
    hc_2025 = coaching_df[
        (coaching_df["Season"] == 2025) &
        (coaching_df["Team Abbr"] == team_abbr) &
        (coaching_df["Coach Type"] == "Head Coach")
    ]
    oc_2025 = coaching_df[
        (coaching_df["Season"] == 2025) &
        (coaching_df["Team Abbr"] == team_abbr) &
        (coaching_df["Coach Type"] == "Offensive Coordinator")
    ]

    hc_name = hc_2025.iloc[0]['Coach'] if not hc_2025.empty else None
    oc_name = oc_2025.iloc[0]['Coach'] if not oc_2025.empty else None

    # Promotion-aware hire year
    def get_hire_year(coach_name, team_abbr, role):
        if not coach_name:
            return None

        history = coaching_df[
            (coaching_df["Coach"] == coach_name) &
            (coaching_df["Team Abbr"] == team_abbr)
        ]

        if history.empty:
            return None

        # Only count earliest year in CURRENT role
        role_history = history[history["Coach Type"] == role]

        if role_history.empty:
            return None

        return int(role_history["Season"].min())

    hc_hire = get_hire_year(hc_name, team_abbr, "Head Coach")
    oc_hire = get_hire_year(oc_name, team_abbr, "Offensive Coordinator")

    hc_display = f"{hc_name} (Hired {hc_hire})" if hc_name else "Not available"
    oc_display = f"{oc_name} (Hired {oc_hire})" if oc_name else "Not available"

    # ----------------------
    # Overview Boxes Layout
    # ----------------------
    st.markdown("<div class='equal-boxes'>", unsafe_allow_html=True)

    # 2024 Overview Box
    st.markdown(f"""
    <div class="box-style">
        <h3>2024 Overview</h3>
        <div class="metric-container">
            <div class="metric">
                <div class="metric-label">Pass Offense</div>
                <div class="metric-value">{team_rank_row['pass_rank']}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Rush Offense</div>
                <div class="metric-value">{team_rank_row['rush_rank']}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Total Offense</div>
                <div class="metric-value">{team_rank_row['total_rank']}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2025 Coaching Staff Box
    st.markdown(f"""
    <div class="box-style">
        <h3>2025 Coaching Staff</h3>
        <p><strong>HC:</strong> {hc_display}</p>
        <p><strong>OC:</strong> {oc_display}</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


    # ----------------------
    # Pass vs Rush Yards Chart (with ranks + coach tooltips)
    # ----------------------
    yards_by_season = stats_df.groupby(["season", "recent_team"]).agg(
        pass_yards=("passing_yards", "sum"),
        rush_yards=("rushing_yards", "sum")
    ).reset_index()

    # Add ranks across all teams for each season
    yards_by_season["pass_rank"] = yards_by_season.groupby("season")["pass_yards"].rank(ascending=False, method="min").astype(int)
    yards_by_season["rush_rank"] = yards_by_season.groupby("season")["rush_yards"].rank(ascending=False, method="min").astype(int)

    # Filter for selected team
    yards_team = yards_by_season[yards_by_season["recent_team"] == team_abbr].copy()

    # Add coaching info
    coach_roles_yards = yards_team["season"].apply(lambda s: get_coach_roles(team_abbr, s))
    yards_team = pd.concat([yards_team.reset_index(drop=True), pd.DataFrame(list(coach_roles_yards))], axis=1)

    # Melt for chart
    yards_melted = yards_team.melt(
        id_vars=["season", "HC", "OC", "Interim HC", "Interim OC", "pass_rank", "rush_rank"],
        value_vars=["pass_yards", "rush_yards"],
        var_name="Type",
        value_name="Yards"
    )
    yards_melted["Type"] = yards_melted["Type"].replace({
        "pass_yards": "Pass Yards",
        "rush_yards": "Rush Yards"
    })

    # Chart
    yards_chart = (
        alt.Chart(yards_melted)
        .mark_line(point=True)
        .encode(
            x=alt.X("season:O", title="Season"),
            y=alt.Y("Yards:Q", title="Total Yards"),
            color="Type:N",
            tooltip=[
                "season",
                "Type",
                alt.Tooltip("Yards:Q", format=".0f"),
                alt.Tooltip("pass_rank:Q", title="Pass Rank"),
                alt.Tooltip("rush_rank:Q", title="Rush Rank"),
                "HC",
                "OC",
                "Interim HC",
                "Interim OC"
            ]
        )
    )

    st.subheader(f"{team_name} Pass vs. Rush Yards (2015–2024)")
    st.altair_chart(yards_chart, use_container_width=True)

    # ----------------------
    # Pass vs Rush TDs Chart (with ranks + coach tooltips)
    # ----------------------
    tds_by_season = stats_df.groupby(["season", "recent_team"]).agg(
        pass_tds=("passing_tds", "sum"),
        rush_tds=("rushing_tds", "sum")
    ).reset_index()

    # Add ranks
    tds_by_season["pass_rank"] = tds_by_season.groupby("season")["pass_tds"].rank(ascending=False, method="min").astype(int)
    tds_by_season["rush_rank"] = tds_by_season.groupby("season")["rush_tds"].rank(ascending=False, method="min").astype(int)

    # Filter for selected team
    tds_team = tds_by_season[tds_by_season["recent_team"] == team_abbr].copy()

    # Add coaching info
    coach_roles_tds = tds_team["season"].apply(lambda s: get_coach_roles(team_abbr, s))
    tds_team = pd.concat([tds_team.reset_index(drop=True), pd.DataFrame(list(coach_roles_tds))], axis=1)

    # Melt for chart
    tds_melted = tds_team.melt(
        id_vars=["season", "HC", "OC", "Interim HC", "Interim OC", "pass_rank", "rush_rank"],
        value_vars=["pass_tds", "rush_tds"],
        var_name="Type",
        value_name="TDs"
    )
    tds_melted["Type"] = tds_melted["Type"].replace({
        "pass_tds": "Pass TDs",
        "rush_tds": "Rush TDs"
    })

    # Chart
    tds_chart = (
        alt.Chart(tds_melted)
        .mark_line(point=True)
        .encode(
            x=alt.X("season:O", title="Season"),
            y=alt.Y("TDs:Q", title="Total Touchdowns"),
            color="Type:N",
            tooltip=[
                "season",
                "Type",
                alt.Tooltip("TDs:Q", format=".0f"),
                alt.Tooltip("pass_rank:Q", title="Pass Rank"),
                alt.Tooltip("rush_rank:Q", title="Rush Rank"),
                "HC",
                "OC",
                "Interim HC",
                "Interim OC"
            ]
        )
    )

    st.subheader(f"{team_name} Pass vs. Rush TDs (2015–2024)")
    st.altair_chart(tds_chart, use_container_width=True)

    # ----------------------
    # Pass vs Run Percentage Stacked Bar Chart (with coach tooltips)
    # ----------------------

    team_stats = stats_df[stats_df["recent_team"] == team_abbr].copy()

    team_pct_data = team_stats.groupby("season").agg(
        total_plays=("team_total_plays", "mean"),
        pass_attempts=("team_pass_attempts", "mean")
    ).reset_index()

    team_pct_data = team_stats.groupby("season").agg(
        total_plays=("team_total_plays", "mean"),
        pass_attempts=("team_pass_attempts", "mean")
    ).reset_index()

    team_pct_data["pass_pct"] = (team_pct_data["pass_attempts"] / team_pct_data["total_plays"]) * 100
    team_pct_data["run_pct"] = 100 - team_pct_data["pass_pct"]

    # Add coaching info for tooltip
    coach_roles_pct = team_pct_data["season"].apply(lambda s: get_coach_roles(team_abbr, s))
    coach_roles_df_pct = pd.DataFrame(list(coach_roles_pct))
    team_pct_data = pd.concat([team_pct_data, coach_roles_df_pct], axis=1)

    # Melt for stacked bar
    pct_melted = team_pct_data.melt(
        id_vars=["season", "HC", "OC", "Interim HC", "Interim OC"],
        value_vars=["pass_pct", "run_pct"],
        var_name="Type",
        value_name="Percent"
    )
    pct_melted["Type"] = pct_melted["Type"].replace({
        "pass_pct": "Pass %",
        "run_pct": "Run %"
    })

    # Chart
    pct_chart = (
        alt.Chart(pct_melted)
        .mark_bar()
        .encode(
            x=alt.X("season:O", title="Season"),
            y=alt.Y("Percent:Q", title="Play Percentage", stack="normalize"),
            color=alt.Color("Type:N", scale=alt.Scale(domain=["Pass %", "Run %"], range=["#1f77b4", "#ff7f0e"])),
            tooltip=[
                "season",
                "Type",
                alt.Tooltip("Percent:Q", format=".1f"),
                "HC",
                "OC",
                "Interim HC",
                "Interim OC"
            ]
        )
    )

    st.subheader(f"{team_name} Pass vs. Run Percentage (2015–2024)")
    st.altair_chart(pct_chart, use_container_width=True)


    # ----------------------
    # Target Share by Position (Stacked Bar with Tooltips)
    # ----------------------

    # 1. Aggregate targets by position/season (WR/RB/TE)
    target_data = stats_df[
        (stats_df["recent_team"] == team_abbr) &
        (stats_df["position"].isin(["WR", "RB", "TE"]))
    ].groupby(["season", "position"]).agg(
        total_targets=("targets", "sum")
    ).reset_index()

    # 2. Calculate target share percentage
    season_totals = target_data.groupby("season")["total_targets"].transform("sum")
    target_data["target_share"] = (target_data["total_targets"] / season_totals) * 100

    # 3. Add coach info for tooltip
    coach_roles_target = target_data["season"].apply(lambda s: get_coach_roles(team_abbr, s))
    target_data = pd.concat([target_data.reset_index(drop=True), pd.DataFrame(list(coach_roles_target))], axis=1)

    # 4. Stacked bar chart
    target_share_chart = (
        alt.Chart(target_data)
        .mark_bar()
        .encode(
            x=alt.X("season:O", title="Season"),
            y=alt.Y("target_share:Q", title="Target Share (%)", stack="normalize"),
            color=alt.Color("position:N", title="Position", scale=alt.Scale(domain=["WR", "RB", "TE"], range=["#1f77b4", "#ff7f0e", "#2ca02c"])),
            tooltip=[
                "season",
                "position",
                alt.Tooltip("target_share:Q", format=".1f", title="Target Share (%)"),
                "HC",
                "OC",
                "Interim HC",
                "Interim OC"
            ]
        )
    )

    st.subheader(f"{team_name} Target Share by Position (2015–2024)")
    st.altair_chart(target_share_chart, use_container_width=True)




    # ----------------------
    # Total Fantasy Points by Position (Vertical Stacked Bar with ranks + coaches)
    # ----------------------

    # 1. Aggregate fantasy points for ALL teams
    fantasy_all = stats_df[
        stats_df["position"].isin(["WR", "RB", "TE", "QB"])
    ].groupby(["season", "recent_team", "position"]).agg(
        total_fp=("fantasy_points_ppr", "sum")
    ).reset_index()

    # 2. Rank within each season + position (across all teams)
    fantasy_all["fp_rank"] = fantasy_all.groupby(["season", "position"])["total_fp"].rank(
        ascending=False, method="min"
    ).astype(int)

    # 3. Filter for the selected team
    fantasy_data = fantasy_all[fantasy_all["recent_team"] == team_abbr].copy()

    # 4. Add coach info
    coach_roles_fp = fantasy_data["season"].apply(lambda s: get_coach_roles(team_abbr, s))
    fantasy_data = pd.concat([fantasy_data.reset_index(drop=True), pd.DataFrame(list(coach_roles_fp))], axis=1)

    # 5. Rename positions for clarity
    fantasy_data["position"] = fantasy_data["position"].replace({
        "WR": "Wide Receiver",
        "RB": "Running Back",
        "TE": "Tight End",
        "QB": "Quarterback"
    })

    # 6. Stacked vertical bar chart
    stacked_fp_chart = (
        alt.Chart(fantasy_data)
        .mark_bar()
        .encode(
            x=alt.X("season:O", title="Season"),
            y=alt.Y("total_fp:Q", title="Total Fantasy Points (PPR)"),
            color=alt.Color("position:N", title="Position"),
            tooltip=[
                "season",
                "position",
                alt.Tooltip("total_fp:Q", format=".0f", title="Fantasy Points"),
                alt.Tooltip("fp_rank:Q", title="Position Rank"),
                "HC",
                "OC",
                "Interim HC",
                "Interim OC"
            ]
        )
    )

    st.subheader(f"{team_name} Total Fantasy Points by Position (2015–2024)")
    st.altair_chart(stacked_fp_chart, use_container_width=True)








