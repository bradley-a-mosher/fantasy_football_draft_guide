import streamlit as st
import pandas as pd
import altair as alt

def show_coach_view(coaching_df, stats_df):
    st.title("Coach View")

    # ----------------------
    # Coach Selection: 2025 HC/OC only
    # ----------------------
    current_coaches_df = coaching_df[
        (coaching_df["Season"] == 2025) &
        (coaching_df["Coach Type"].isin(["Head Coach", "Offensive Coordinator"]))
    ][["Team Abbr", "Coach", "Coach Type"]].dropna()

    # Create display label: "KC – Andy Reid"
    current_coaches_df["Display"] = current_coaches_df["Team Abbr"] + " – " + current_coaches_df["Coach"]

    # Map display label to actual coach name
    coach_display_map = dict(zip(current_coaches_df["Display"], current_coaches_df["Coach"]))

    # Dropdown with sorted display labels
    coach_display_selected = st.selectbox(
        "Select a Coach (2025 HC/OC Only)",
        sorted(current_coaches_df["Display"])
    )

    # Get coach name
    coach_selected = coach_display_map[coach_display_selected]

    # Show contextual info under dropdown
    row_info = current_coaches_df[current_coaches_df["Coach"] == coach_selected].iloc[0]
    st.write(f"**Selected:** {row_info['Coach']} ({row_info['Coach Type']}) – {row_info['Team Abbr']}")

    # ----------------------
    # Get Coaching History
    # ----------------------
    coach_history = coaching_df[
        (coaching_df["Coach"] == coach_selected) &
        (coaching_df["Coach Type"].isin(["Head Coach", "Offensive Coordinator"]))
    ]

    # Handle rookie or no history
    if coach_history.empty:
        st.info("No historical data available for this coach (rookie or no prior HC/OC experience).")
        return

    # Merge with player stats
    history_stats = stats_df.merge(
        coach_history,
        left_on=["season", "team_id"],
        right_on=["Season", "Team ID"],
        how="inner"
    )

    # ----------------------
    # Season Filter
    # ----------------------
    available_seasons = sorted(history_stats["season"].unique())
    selected_seasons = st.multiselect(
        "Filter by Season",
        options=available_seasons,
        default=available_seasons
    )

    history_stats = history_stats[history_stats["season"].isin(selected_seasons)]

    # ----------------------------
    # Position Selector
    # ----------------------------
    st.markdown("### Position Trends")

    position_choice = st.radio(
        "Select Position:",
        options=["QB", "RB", "WR", "TE"],
        horizontal=True
    )

    # ==============================================================
    # =====================  QB SECTION  ===========================
    # ==============================================================
    if position_choice == "QB":
        st.subheader("Quarterback Trends")

        # Filter QB data
        qb_data = history_stats[history_stats["position"] == "QB"].copy()

        # Early exit if no QB data
        if qb_data.empty:
            st.info("No QB data available for this coach in the selected seasons.")
            return

        # League-wide rank calculations
        league_qb_data = stats_df[stats_df["position"] == "QB"].copy()
        league_qb_data["Fantasy Rank"] = league_qb_data.groupby("season")["fantasy_points"] \
            .rank(method="min", ascending=False).astype(int)
        league_qb_data["PPR Rank"] = league_qb_data.groupby("season")["fantasy_points_ppr"] \
            .rank(method="min", ascending=False).astype(int)

        # Merge ranks into QB data
        qb_data = qb_data.merge(
            league_qb_data[["season", "player_id", "Fantasy Rank", "PPR Rank"]],
            on=["season", "player_id"],
            how="left"
        )

        # Common columns
        common_cols = ["season", "recent_team", "Coach Type", "player_display_name"]

        # Tabs for QB
        tab1, tab2, tab3, tab4 = st.tabs([
            "Passing Stats",
            "Rushing Stats",
            "Fantasy Points (Standard)",
            "Fantasy Points (PPR)"
        ])

        # Passing Tab
        with tab1:
            st.dataframe(
                qb_data[common_cols + ["attempts", "completions", "passing_yards", "passing_tds", "interceptions"]]
                .rename(columns={"player_display_name": "Player"})
                .sort_values(by="season", ascending=False),
                use_container_width=True,
                hide_index=True
            )

        # Rushing Tab
        with tab2:
            st.dataframe(
                qb_data[common_cols + ["carries", "rushing_yards", "rushing_tds"]]
                .rename(columns={"player_display_name": "Player"})
                .sort_values(by="season", ascending=False),
                use_container_width=True,
                hide_index=True
            )

        # Fantasy Standard Tab
        with tab3:
            st.dataframe(
                qb_data[common_cols + ["fantasy_points", "Fantasy Rank", "fantasy_points_pg"]]
                .rename(columns={
                    "player_display_name": "Player",
                    "fantasy_points": "Fantasy Points",
                    "fantasy_points_pg": "Fantasy Points/Game"
                })
                .sort_values(by="season", ascending=False),
                use_container_width=True,
                hide_index=True
            )

        # Fantasy PPR Tab
        with tab4:
            st.dataframe(
                qb_data[common_cols + ["fantasy_points_ppr", "PPR Rank", "fantasy_points_ppr_pg"]]
                .rename(columns={
                    "player_display_name": "Player",
                    "fantasy_points_ppr": "PPR Points",
                    "fantasy_points_ppr_pg": "PPR Points/Game"
                })
                .sort_values(by="season", ascending=False),
                use_container_width=True,
                hide_index=True
            )

        # QB Fantasy Line Chart
        st.markdown("### QB Fantasy Points Year-Over-Year")

        scoring_choice = st.radio(
            "Scoring Format:",
            options=["Standard", "PPR"],
            horizontal=True,
            key="qb_scoring_choice"
        )

        metric_col = "fantasy_points" if scoring_choice == "Standard" else "fantasy_points_ppr"
        metric_label = "Fantasy Points" if scoring_choice == "Standard" else "PPR Fantasy Points"

        top_qbs = qb_data.loc[qb_data.groupby("season")[metric_col].idxmax()]

        league_qbs = stats_df[stats_df["position"] == "QB"].copy()
        league_qbs["Rank"] = league_qbs.groupby("season")[metric_col] \
            .rank(method="min", ascending=False)
        top32_qbs = league_qbs[league_qbs["Rank"] <= 32]

        league_avg = top32_qbs.groupby("season")[metric_col].mean().reset_index()
        league_avg.rename(columns={metric_col: metric_label}, inplace=True)

        coach_seasons = top_qbs["season"].unique()
        league_avg = league_avg[league_avg["season"].isin(coach_seasons)]

        coach_line = alt.Chart(top_qbs).mark_line(point=True, color="#1f77b4").encode(
            x=alt.X("season:O", title="Season"),
            y=alt.Y(f"{metric_col}:Q", title=metric_label),
            tooltip=[
                alt.Tooltip("season", title="Season"),
                alt.Tooltip("player_display_name", title="Player"),
                alt.Tooltip(metric_col, title=metric_label)
            ]
        )

        avg_line = alt.Chart(league_avg).mark_line(point=True, strokeDash=[5, 5], color="red").encode(
            x=alt.X("season:O"),
            y=alt.Y(f"{metric_label}:Q"),
            tooltip=[
                alt.Tooltip("season", title="Season"),
                alt.Tooltip(f"{metric_label}:Q", title="League Avg")
            ]
        )

        st.altair_chart(coach_line + avg_line, use_container_width=True)

        



    # ==============================================================
    # =====================  RB SECTION  ===========================
    # ==============================================================
    elif position_choice == "RB":
        st.subheader("Running Back Trends")

        # Filter RB data
        coach_rbs = history_stats[history_stats["position"] == "RB"].copy()

        # Early exit if no RB data
        if coach_rbs.empty:
            st.info("No RB data available for this coach in the selected seasons.")
            return

        # League-wide rank calculations (fantasy points & PPR)
        league_rb_data = stats_df[stats_df["position"] == "RB"].copy()
        league_rb_data["Fantasy Rank"] = league_rb_data.groupby("season")["fantasy_points"] \
            .rank(method="min", ascending=False).astype(int)
        league_rb_data["PPR Rank"] = league_rb_data.groupby("season")["fantasy_points_ppr"] \
            .rank(method="min", ascending=False).astype(int)

        # Merge ranks into RB data
        coach_rbs = coach_rbs.merge(
            league_rb_data[["season", "player_id", "Fantasy Rank", "PPR Rank"]],
            on=["season", "player_id"],
            how="left"
        )

        # Add yards per carry (formatted to 2 decimals)
        coach_rbs["yards_per_carry"] = coach_rbs.apply(
            lambda row: row["rushing_yards"] / row["carries"] if row["carries"] > 0 else 0, axis=1
        )
        coach_rbs["yards_per_carry"] = coach_rbs["yards_per_carry"].round(2)

        # Common columns
        common_cols = ["season", "recent_team", "Coach Type", "player_display_name"]

        # Tabs: Rushing, Receiving, Fantasy Std, Fantasy PPR
        tab1, tab2, tab3, tab4 = st.tabs([
            "Rushing Stats",
            "Receiving Stats",
            "Fantasy Points (Standard)",
            "Fantasy Points (PPR)"
        ])

        # --- Rushing Stats Tab ---
        with tab1:
            rushing_cols = common_cols + [
                "carries", "rushing_yards", "yards_per_carry", "rushing_tds"
            ]
            st.markdown("**Rushing Production (Seasonal)**")
            st.dataframe(
                coach_rbs[rushing_cols].rename(columns={
                    "player_display_name": "Player",
                    "rushing_yards": "Rush Yards",
                    "yards_per_carry": "Yards/Carry",
                    "rushing_tds": "Rush TDs"
                }).sort_values(by="season", ascending=False),
                use_container_width=True,
                hide_index=True
            )

        # --- Receiving Stats Tab ---
        with tab2:
            receiving_cols = common_cols + [
                "targets", "receptions", "receiving_yards", "receiving_tds"
            ]
            st.markdown("**Receiving Production (Seasonal)**")
            st.dataframe(
                coach_rbs[receiving_cols].rename(columns={
                    "player_display_name": "Player",
                    "receiving_yards": "Rec Yards",
                    "receiving_tds": "Rec TDs"
                }).sort_values(by="season", ascending=False),
                use_container_width=True,
                hide_index=True
            )

        # --- Fantasy Points (Standard) Tab ---
        with tab3:
            fantasy_standard_cols = common_cols + [
                "fantasy_points", "Fantasy Rank", "fantasy_points_pg"
            ]
            st.markdown("**Standard Fantasy Production (Seasonal)**")
            st.dataframe(
                coach_rbs[fantasy_standard_cols]
                .rename(columns={
                    "player_display_name": "Player",
                    "fantasy_points": "Fantasy Points",
                    "fantasy_points_pg": "Fantasy Points/Game"
                }).sort_values(by="season", ascending=False),
                use_container_width=True,
                hide_index=True
            )

        # --- Fantasy Points (PPR) Tab ---
        with tab4:
            fantasy_ppr_cols = common_cols + [
                "fantasy_points_ppr", "PPR Rank", "fantasy_points_ppr_pg"
            ]
            st.markdown("**PPR Fantasy Production (Seasonal)**")
            st.dataframe(
                coach_rbs[fantasy_ppr_cols]
                .rename(columns={
                    "player_display_name": "Player",
                    "fantasy_points_ppr": "PPR Points",
                    "fantasy_points_ppr_pg": "PPR Points/Game"
                }).sort_values(by="season", ascending=False),
                use_container_width=True,
                hide_index=True
            )

        # ----------------------------
        # RB Fantasy Points Line Chart (Top RB or Combined if RB2 in Top 40)
        # ----------------------------
        st.markdown("### RB Fantasy Points Year-Over-Year")

        # Toggle between Standard and PPR scoring
        scoring_choice_rb = st.radio(
            "Scoring Format:",
            options=["Standard", "PPR"],
            horizontal=True,
            key="rb_scoring_choice"
        )

        # Determine metric
        if scoring_choice_rb == "Standard":
            metric_col_rb = "fantasy_points"
            metric_label_rb = "Fantasy Points"
        else:
            metric_col_rb = "fantasy_points_ppr"
            metric_label_rb = "PPR Fantasy Points"

        # League-wide RB data for top 40 ranking
        league_rb_all = stats_df[stats_df["position"] == "RB"].copy()
        league_rb_all["Rank"] = league_rb_all.groupby("season")[metric_col_rb] \
            .rank(method="min", ascending=False)

        # Filter top 40 RBs per season (league-wide)
        top40_league_rbs = league_rb_all[league_rb_all["Rank"] <= 40]

        # ----------------------------
        # Build coach RB line data
        # ----------------------------
        combined_rb_records = []

        for season in coach_rbs["season"].unique():
            season_rbs = coach_rbs[coach_rbs["season"] == season].copy()
            if season_rbs.empty:
                continue

            # Sort by fantasy points
            season_rbs = season_rbs.sort_values(by=metric_col_rb, ascending=False)

            # Always take top RB
            top_rb = season_rbs.iloc[0]

            player_names = [top_rb["player_display_name"]]
            total_points = top_rb[metric_col_rb]

            # Check if RB2 qualifies (in league top 40)
            if len(season_rbs) > 1:
                rb2 = season_rbs.iloc[1]
                rb2_rank = top40_league_rbs[
                    (top40_league_rbs["season"] == season) &
                    (top40_league_rbs["player_id"] == rb2["player_id"])
                ]
                if not rb2_rank.empty:
                    player_names.append(rb2["player_display_name"])
                    total_points += rb2[metric_col_rb]

            combined_rb_records.append({
                "season": season,
                "Players": " / ".join(player_names),
                metric_label_rb: total_points
            })

        rb_line_df = pd.DataFrame(combined_rb_records)

        # Handle empty case
        if rb_line_df.empty:
            st.info("No RB fantasy data available for this coach in the selected seasons.")
        else:
            # League average line (Top 40 RBs) filtered to coach's seasons
            league_avg_rb = top40_league_rbs.groupby("season")[metric_col_rb].mean().reset_index()
            league_avg_rb.rename(columns={metric_col_rb: metric_label_rb}, inplace=True)

            coach_seasons_rb = rb_line_df["season"].unique()
            league_avg_rb = league_avg_rb[league_avg_rb["season"].isin(coach_seasons_rb)]

            # Build Altair lines
            coach_rb_line = alt.Chart(rb_line_df).mark_line(point=True, color="#1f77b4").encode(
                x=alt.X("season:O", title="Season"),
                y=alt.Y(f"{metric_label_rb}:Q", title=metric_label_rb),
                tooltip=[
                    alt.Tooltip("season", title="Season"),
                    alt.Tooltip("Players", title="Player(s)"),
                    alt.Tooltip(metric_label_rb, title=metric_label_rb)
                ]
            )

            avg_rb_line = alt.Chart(league_avg_rb).mark_line(point=True, strokeDash=[5, 5], color="red").encode(
                x=alt.X("season:O"),
                y=alt.Y(f"{metric_label_rb}:Q"),
                tooltip=[
                    alt.Tooltip("season", title="Season"),
                    alt.Tooltip(f"{metric_label_rb}:Q", title="League Avg")
                ]
            )

            st.altair_chart(coach_rb_line + avg_rb_line, use_container_width=True)

        # ----------------------------
        # RB Usage Bar Chart (Run Game vs Total Offense)
        # ----------------------------

        st.markdown("### RB Usage (Run Game vs Total Offense)")

        # Toggle between run game usage and overall usage
        usage_choice = st.radio(
            "Usage Metric:",
            options=["Run Game Usage", "Total Offensive Usage"],
            horizontal=True,
            key="rb_usage_choice"
        )

        # Prepare data
        usage_records = []

        for season in coach_rbs["season"].unique():
            season_rbs = coach_rbs[coach_rbs["season"] == season].copy()
            if season_rbs.empty:
                continue

            # Sort RBs by fantasy points
            season_rbs = season_rbs.sort_values(by=metric_col_rb, ascending=False)

            # Always take top RB
            top_rb = season_rbs.iloc[0]

            # Calculate usage for top RB
            team_total_carries = season_rbs["team_total_plays"].iloc[0] - season_rbs["team_pass_attempts"].iloc[0]
            team_total_plays = season_rbs["team_total_plays"].iloc[0]

            top_run_usage = top_rb["carries"] / team_total_carries if team_total_carries > 0 else 0
            top_total_usage = (top_rb["carries"] + top_rb["targets"]) / team_total_plays if team_total_plays > 0 else 0

            usage_records.append({
                "season": season,
                "Player": top_rb["player_display_name"],
                "Run Game Usage": top_run_usage * 100,
                "Total Offensive Usage": top_total_usage * 100
            })

            # Check if RB2 qualifies (Top 40 league-wide)
            if len(season_rbs) > 1:
                rb2 = season_rbs.iloc[1]
                rb2_rank = top40_league_rbs[
                    (top40_league_rbs["season"] == season) &
                    (top40_league_rbs["player_id"] == rb2["player_id"])
                ]
                if not rb2_rank.empty:
                    rb2_run_usage = rb2["carries"] / team_total_carries if team_total_carries > 0 else 0
                    rb2_total_usage = (rb2["carries"] + rb2["targets"]) / team_total_plays if team_total_plays > 0 else 0

                    usage_records.append({
                        "season": season,
                        "Player": rb2["player_display_name"],
                        "Run Game Usage": rb2_run_usage * 100,
                        "Total Offensive Usage": rb2_total_usage * 100
                    })

        # Convert to DataFrame
        usage_df = pd.DataFrame(usage_records)

        # Handle empty case
        if usage_df.empty:
            st.info("No RB usage data available for this coach.")
        else:
            # Select metric based on toggle
            metric_selected = usage_choice

            # Build grouped bar chart
            usage_chart = alt.Chart(usage_df).mark_bar().encode(
                x=alt.X("season:O", title="Season"),
                y=alt.Y(f"{metric_selected}:Q", title=f"{metric_selected} (%)"),
                color="Player:N",
                tooltip=[
                    alt.Tooltip("season", title="Season"),
                    alt.Tooltip("Player", title="Player"),
                    alt.Tooltip(f"{metric_selected}:Q", title=f"{metric_selected} (%)", format=".2f")
                ]
            ).properties(width=600)

            st.altair_chart(usage_chart, use_container_width=True)

    # ==============================================================
    # =====================  WR SECTION (placeholder) ===============
    # ==============================================================
    elif position_choice == "WR":
        st.subheader("Wide Receiver Trends")

        # ---- WR TABLES (Tabs) ----

        # Filter WR data
        wr_data = history_stats[history_stats["position"] == "WR"].copy()

        # League-wide rank calculations (fantasy points & PPR)
        league_wr_data = stats_df[stats_df["position"] == "WR"].copy()
        league_wr_data["Fantasy Rank"] = league_wr_data.groupby("season")["fantasy_points"] \
            .rank(method="min", ascending=False).astype(int)
        league_wr_data["PPR Rank"] = league_wr_data.groupby("season")["fantasy_points_ppr"] \
            .rank(method="min", ascending=False).astype(int)

        # Merge ranks into WR data
        wr_data = wr_data.merge(
            league_wr_data[["season", "player_id", "Fantasy Rank", "PPR Rank"]],
            on=["season", "player_id"],
            how="left"
        )

        # Add yards per carry (2 decimals) for rushing tab
        wr_data["yards_per_carry"] = wr_data.apply(
            lambda row: row["rushing_yards"] / row["carries"] if row["carries"] > 0 else 0, axis=1
        )
        wr_data["yards_per_carry"] = wr_data["yards_per_carry"].round(2)

        # Common columns
        common_cols = ["season", "recent_team", "Coach Type", "player_display_name"]

        # Tabs: Receiving, Rushing, Fantasy Std, Fantasy PPR
        tab1, tab2, tab3, tab4 = st.tabs([
            "Receiving Stats",
            "Rushing Stats",
            "Fantasy Points (Standard)",
            "Fantasy Points (PPR)"
        ])

        # --- Receiving Stats Tab ---
        with tab1:
            receiving_cols = common_cols + [
                "targets", "receptions", "receiving_yards", "receiving_tds"
            ]
            st.markdown("**Receiving Production (Seasonal)**")
            st.dataframe(
                wr_data[receiving_cols].rename(columns={
                    "player_display_name": "Player",
                    "receiving_yards": "Rec Yards",
                    "receiving_tds": "Rec TDs"
                }).sort_values(by="season", ascending=False),
                use_container_width=True,
                hide_index=True
            )

        # --- Rushing Stats Tab ---
        with tab2:
            rushing_cols = common_cols + [
                "carries", "rushing_yards", "yards_per_carry", "rushing_tds"
            ]
            st.markdown("**Rushing Production (Seasonal)**")
            st.dataframe(
                wr_data[rushing_cols].rename(columns={
                    "player_display_name": "Player",
                    "rushing_yards": "Rush Yards",
                    "yards_per_carry": "Yards/Carry",
                    "rushing_tds": "Rush TDs"
                }).sort_values(by="season", ascending=False),
                use_container_width=True,
                hide_index=True
            )

        # --- Fantasy Points (Standard) Tab ---
        with tab3:
            fantasy_standard_cols = common_cols + [
                "fantasy_points", "Fantasy Rank", "fantasy_points_pg"
            ]
            st.markdown("**Standard Fantasy Production (Seasonal)**")
            st.dataframe(
                wr_data[fantasy_standard_cols]
                .rename(columns={
                    "player_display_name": "Player",
                    "fantasy_points": "Fantasy Points",
                    "fantasy_points_pg": "Fantasy Points/Game"
                }).sort_values(by="season", ascending=False),
                use_container_width=True,
                hide_index=True
            )

        # --- Fantasy Points (PPR) Tab ---
        with tab4:
            fantasy_ppr_cols = common_cols + [
                "fantasy_points_ppr", "PPR Rank", "fantasy_points_ppr_pg"
            ]
            st.markdown("**PPR Fantasy Production (Seasonal)**")
            st.dataframe(
                wr_data[fantasy_ppr_cols]
                .rename(columns={
                    "player_display_name": "Player",
                    "fantasy_points_ppr": "PPR Points",
                    "fantasy_points_ppr_pg": "PPR Points/Game"
                }).sort_values(by="season", ascending=False),
                use_container_width=True,
                hide_index=True
            )

        # ----------------------------
        # WR Fantasy Points Line Chart (Top WR or Combined if WR2 in Top 40)
        # ----------------------------

        st.markdown("### WR Fantasy Points Year-Over-Year")

        # Initialize WR line DataFrame
        wr_line_df = pd.DataFrame()

        # Get WR data for the selected coach
        coach_wrs = history_stats[history_stats["position"] == "WR"].copy()

        if coach_wrs.empty:
            st.info("No WR fantasy data available for this coach in the selected seasons.")
        else:
            # Scoring toggle
            scoring_choice_wr = st.radio(
                "Scoring Format:",
                options=["Standard", "PPR"],
                horizontal=True,
                key="wr_scoring_choice"
            )

            # Determine metric
            if scoring_choice_wr == "Standard":
                metric_col_wr = "fantasy_points"
                metric_label_wr = "Fantasy Points"
            else:
                metric_col_wr = "fantasy_points_ppr"
                metric_label_wr = "PPR Fantasy Points"

            # League-wide WR data for ranking
            league_wr_data = stats_df[stats_df["position"] == "WR"].copy()
            league_wr_data["Rank"] = league_wr_data.groupby("season")[metric_col_wr] \
                .rank(method="min", ascending=False)

            # Top 40 WRs league-wide
            top40_league_wrs = league_wr_data[league_wr_data["Rank"] <= 40]

            # Build combined WR records for each season
            combined_wr_records = []

            for season in coach_wrs["season"].unique():
                season_wrs = coach_wrs[coach_wrs["season"] == season].copy()
                if season_wrs.empty:
                    continue

                # Sort by fantasy points
                season_wrs = season_wrs.sort_values(by=metric_col_wr, ascending=False)

                # Always take top WR
                top_wr = season_wrs.iloc[0]
                player_names = [top_wr["player_display_name"]]
                total_points = top_wr[metric_col_wr]

                # Check if WR2 qualifies (in top 40 league-wide)
                if len(season_wrs) > 1:
                    wr2 = season_wrs.iloc[1]
                    wr2_rank = top40_league_wrs[
                        (top40_league_wrs["season"] == season) &
                        (top40_league_wrs["player_id"] == wr2["player_id"])
                    ]
                    if not wr2_rank.empty:
                        player_names.append(wr2["player_display_name"])
                        total_points += wr2[metric_col_wr]

                combined_wr_records.append({
                    "season": season,
                    "Players": " / ".join(player_names),
                    metric_label_wr: total_points
                })

            # Convert to DataFrame
            wr_line_df = pd.DataFrame(combined_wr_records)

            # League average (Top 40 WRs) filtered to coach seasons
            league_avg_wr = top40_league_wrs.groupby("season")[metric_col_wr].mean().reset_index()
            league_avg_wr.rename(columns={metric_col_wr: metric_label_wr}, inplace=True)
            league_avg_wr = league_avg_wr[league_avg_wr["season"].isin(wr_line_df["season"].unique())]

            # Build Altair lines
            coach_wr_line = alt.Chart(wr_line_df).mark_line(point=True, color="#1f77b4").encode(
                x=alt.X("season:O", title="Season"),
                y=alt.Y(f"{metric_label_wr}:Q", title=metric_label_wr),
                tooltip=[
                    alt.Tooltip("season", title="Season"),
                    alt.Tooltip("Players", title="Player(s)"),
                    alt.Tooltip(metric_label_wr, title=metric_label_wr)
                ]
            )

            avg_wr_line = alt.Chart(league_avg_wr).mark_line(point=True, strokeDash=[5, 5], color="red").encode(
                x=alt.X("season:O"),
                y=alt.Y(f"{metric_label_wr}:Q"),
                tooltip=[
                    alt.Tooltip("season", title="Season"),
                    alt.Tooltip(f"{metric_label_wr}:Q", title="League Avg")
                ]
            )

            # Display chart
            st.altair_chart(coach_wr_line + avg_wr_line, use_container_width=True)

        # ----------------------------
        # WR Target Share Bar Chart
        # ----------------------------

        st.markdown("### WR Target Share (Season-Over-Season)")

        # Filter WRs with target share >= 10%
        wr_target_data = coach_wrs.copy()
        wr_target_data = wr_target_data[wr_target_data["target_share"] >= 0.10]

        if wr_target_data.empty:
            st.info("No WR target share data (≥10%) available for this coach in the selected seasons.")
        else:
            # Convert target share to percentage
            wr_target_data["Target Share (%)"] = wr_target_data["target_share"] * 100

            # Merge league ranks for tooltips
            league_wr_ranks = stats_df[stats_df["position"] == "WR"].copy()
            league_wr_ranks["Fantasy Rank"] = league_wr_ranks.groupby("season")["fantasy_points"] \
                .rank(method="min", ascending=False).astype(int)

            wr_target_data = wr_target_data.merge(
                league_wr_ranks[["season", "player_id", "Fantasy Rank"]],
                on=["season", "player_id"],
                how="left"
            )

            # Build Altair grouped bar chart
            target_chart = alt.Chart(wr_target_data).mark_bar().encode(
                x=alt.X("season:O", title="Season"),
                y=alt.Y("Target Share (%):Q", title="Target Share (%)"),
                color="player_display_name:N",
                tooltip=[
                    alt.Tooltip("season", title="Season"),
                    alt.Tooltip("player_display_name", title="Player"),
                    alt.Tooltip("Target Share (%)", title="Target Share (%)", format=".2f"),
                    alt.Tooltip("Fantasy Rank", title="Fantasy Rank")
                ]
            ).properties(width=600)

            st.altair_chart(target_chart, use_container_width=True)





    # ==============================================================
    # =====================  TE SECTION (placeholder) ===============
    # ==============================================================
    elif position_choice == "TE":
        st.subheader("Tight End Trends")

        # ---- TE TABLES (Tabs) ----

        # Filter TE data
        te_data = history_stats[history_stats["position"] == "TE"].copy()

        # League-wide rank calculations (fantasy points & PPR) for TEs only
        league_te_data = stats_df[stats_df["position"] == "TE"].copy()
        league_te_data["Fantasy Rank"] = league_te_data.groupby("season")["fantasy_points"] \
            .rank(method="min", ascending=False).astype(int)
        league_te_data["PPR Rank"] = league_te_data.groupby("season")["fantasy_points_ppr"] \
            .rank(method="min", ascending=False).astype(int)

        # Merge ranks into TE data
        te_data = te_data.merge(
            league_te_data[["season", "player_id", "Fantasy Rank", "PPR Rank"]],
            on=["season", "player_id"],
            how="left"
        )

        # Add yards per carry (for rushing tab, though rarely relevant)
        te_data["yards_per_carry"] = te_data.apply(
            lambda row: row["rushing_yards"] / row["carries"] if row["carries"] > 0 else 0, axis=1
        )
        te_data["yards_per_carry"] = te_data["yards_per_carry"].round(2)

        # Common columns
        common_cols = ["season", "recent_team", "Coach Type", "player_display_name"]

        # Tabs: Receiving, Rushing, Fantasy Std, Fantasy PPR
        tab1, tab2, tab3, tab4 = st.tabs([
            "Receiving Stats",
            "Rushing Stats",
            "Fantasy Points (Standard)",
            "Fantasy Points (PPR)"
        ])

        # --- Receiving Stats Tab ---
        with tab1:
            receiving_cols = common_cols + [
                "targets", "receptions", "receiving_yards", "receiving_tds"
            ]
            st.markdown("**Receiving Production (Seasonal)**")
            st.dataframe(
                te_data[receiving_cols].rename(columns={
                    "player_display_name": "Player",
                    "receiving_yards": "Rec Yards",
                    "receiving_tds": "Rec TDs"
                }).sort_values(by="season", ascending=False),
                use_container_width=True,
                hide_index=True
            )

        # --- Rushing Stats Tab ---
        with tab2:
            rushing_cols = common_cols + [
                "carries", "rushing_yards", "yards_per_carry", "rushing_tds"
            ]
            st.markdown("**Rushing Production (Seasonal)**")
            st.dataframe(
                te_data[rushing_cols].rename(columns={
                    "player_display_name": "Player",
                    "rushing_yards": "Rush Yards",
                    "yards_per_carry": "Yards/Carry",
                    "rushing_tds": "Rush TDs"
                }).sort_values(by="season", ascending=False),
                use_container_width=True,
                hide_index=True
            )

        # --- Fantasy Points (Standard) Tab ---
        with tab3:
            fantasy_standard_cols = common_cols + [
                "fantasy_points", "Fantasy Rank", "fantasy_points_pg"
            ]
            st.markdown("**Standard Fantasy Production (Seasonal)**")
            st.dataframe(
                te_data[fantasy_standard_cols]
                .rename(columns={
                    "player_display_name": "Player",
                    "fantasy_points": "Fantasy Points",
                    "fantasy_points_pg": "Fantasy Points/Game"
                })
                .sort_values(by="season", ascending=False),
                use_container_width=True,
                hide_index=True
            )

        # --- Fantasy Points (PPR) Tab ---
        with tab4:
            fantasy_ppr_cols = common_cols + [
                "fantasy_points_ppr", "PPR Rank", "fantasy_points_ppr_pg"
            ]
            st.markdown("**PPR Fantasy Production (Seasonal)**")
            st.dataframe(
                te_data[fantasy_ppr_cols]
                .rename(columns={
                    "player_display_name": "Player",
                    "fantasy_points_ppr": "PPR Points",
                    "fantasy_points_ppr_pg": "PPR Points/Game"
                })
                .sort_values(by="season", ascending=False),
                use_container_width=True,
                hide_index=True
            )

        # ----------------------------
        # TE Fantasy Points Line Chart (Top TE per Year)
        # ----------------------------

        st.markdown("### TE Fantasy Points Year-Over-Year")

        scoring_choice_te = st.radio(
            "Scoring Format:",
            options=["Standard", "PPR"],
            horizontal=True,
            key="te_scoring_choice"
        )

        # Metric selection
        metric_col_te = "fantasy_points" if scoring_choice_te == "Standard" else "fantasy_points_ppr"
        metric_label_te = "Fantasy Points" if scoring_choice_te == "Standard" else "PPR Fantasy Points"

        coach_tes = history_stats[history_stats["position"] == "TE"].copy()
        top_tes = coach_tes.loc[
            coach_tes.groupby("season")[metric_col_te].idxmax()
        ]

        # League average (top 32 TEs)
        league_tes = stats_df[stats_df["position"] == "TE"].copy()
        league_tes["Rank"] = league_tes.groupby("season")[metric_col_te].rank(method="min", ascending=False)
        top32_tes = league_tes[league_tes["Rank"] <= 32]
        league_avg_te = top32_tes.groupby("season")[metric_col_te].mean().reset_index()
        league_avg_te.rename(columns={metric_col_te: metric_label_te}, inplace=True)

        # Filter league avg to coach seasons
        league_avg_te = league_avg_te[league_avg_te["season"].isin(top_tes["season"])]

        # Build Altair line chart
        coach_te_line = alt.Chart(top_tes).mark_line(point=True, color="#1f77b4").encode(
            x=alt.X("season:O", title="Season"),
            y=alt.Y(f"{metric_col_te}:Q", title=metric_label_te),
            tooltip=[
                alt.Tooltip("season", title="Season"),
                alt.Tooltip("player_display_name", title="Player"),
                alt.Tooltip(metric_col_te, title=metric_label_te)
            ]
        )

        avg_te_line = alt.Chart(league_avg_te).mark_line(point=True, strokeDash=[5, 5], color="red").encode(
            x=alt.X("season:O"),
            y=alt.Y(f"{metric_label_te}:Q"),
            tooltip=[
                alt.Tooltip("season", title="Season"),
                alt.Tooltip(f"{metric_label_te}:Q", title="League Avg")
            ]
        )

        st.altair_chart(coach_te_line + avg_te_line, use_container_width=True)

        # ----------------------------
        # TE Target Share Bar Chart (≥10%)
        # ----------------------------

        st.markdown("### TE Target Share (Season-Over-Season)")

        te_target_data = coach_tes.copy()
        te_target_data = te_target_data[te_target_data["target_share"] >= 0.10]  # Filter ≥10%

        if te_target_data.empty:
            st.info("No TE target share data (≥10%) available for this coach in the selected seasons.")
        else:
            te_target_data["Target Share (%)"] = te_target_data["target_share"] * 100

            league_te_ranks = stats_df[stats_df["position"] == "TE"].copy()
            league_te_ranks["Fantasy Rank"] = league_te_ranks.groupby("season")["fantasy_points"] \
                .rank(method="min", ascending=False).astype(int)

            te_target_data = te_target_data.merge(
                league_te_ranks[["season", "player_id", "Fantasy Rank"]],
                on=["season", "player_id"],
                how="left"
            )

            target_chart_te = alt.Chart(te_target_data).mark_bar().encode(
                x=alt.X("season:O", title="Season"),
                y=alt.Y("Target Share (%):Q", title="Target Share (%)"),
                color="player_display_name:N",
                tooltip=[
                    alt.Tooltip("season", title="Season"),
                    alt.Tooltip("player_display_name", title="Player"),
                    alt.Tooltip("Target Share (%)", title="Target Share (%)", format=".2f"),
                    alt.Tooltip("Fantasy Rank", title="Fantasy Rank")
                ]
            ).properties(width=600)

            st.altair_chart(target_chart_te, use_container_width=True)



