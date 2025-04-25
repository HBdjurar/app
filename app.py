import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import datetime
import io

# --- UI Setup ---
st.set_page_config(
    page_title="Soccer Player Stats Predictor",
    page_icon="⚽",
    layout="wide"
)


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit and username == "admin" and password == "1234":
            st.session_state.authenticated = True
        elif submit:
            st.error("Invalid credentials")
else:
    # --- Config ---
    API_URL = st.sidebar.text_input("API URL", "http://85.229.213.182:8000")
    TARGETS = [
        'Goals',
        'Assists',
        'Shots',
        'Shots on Target',
        'Yellow Cards',
        'Tackles',
        'Fouls Committed'
    ]

    # Common positions for dropdown - removed "Unknown" as per user request
    POSITIONS = [
        "GK", "CB", "LB", "RB", "LWB", "RWB", "CDM", "CM", "CAM",
        "LM", "RM", "LW", "RW", "CF", "ST"
    ]


    # --- Helper functions ---
    def get_threshold_ranges(target):
        """Get appropriate thresholds for over/under calculations based on target."""
        if target in ['Goals', 'Assists']:
            return [0.5, 1.5, 2.5, 3.5]
        elif target in ['Yellow Cards']:
            return [0.5]
        else:  # Shots, Shots on Target, Tackles, Fouls Committed
            return [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5]


    def format_odds(odds):
        """Format odds for display."""
        if odds >= 100:
            return "100+"
        return f"{odds:.2f}"


    def call_predict_api(match_data):
        """Call the prediction API and return results."""
        try:
            response = requests.post(f"{API_URL}/predict/", json=match_data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"API Error: {str(e)}")
            return None


    def call_export_api(match_data):
        """Call the export API and return Excel file."""
        try:
            response = requests.post(f"{API_URL}/export/", json=match_data, stream=True)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            st.error(f"Export Error: {str(e)}")
            return None


    def fetch_api_data(endpoint):
        """Fetch data from API endpoint."""
        try:
            response = requests.get(f"{API_URL}/{endpoint}/")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"API Error when fetching {endpoint}: {str(e)}")
            return {}


    def fetch_team_players(team_name):
        """Fetch players for a specific team."""
        if not team_name:
            return []

        try:
            response = requests.get(f"{API_URL}/team_players/{team_name}")
            response.raise_for_status()
            return response.json().get("players", [])
        except requests.exceptions.RequestException as e:
            st.error(f"API Error when fetching players for {team_name}: {str(e)}")
            return []


    def fetch_team_manager(team_name):
        """Fetch latest manager for a team."""
        if not team_name:
            return "Unknown"

        try:
            response = requests.get(f"{API_URL}/team_manager/{team_name}")
            response.raise_for_status()
            return response.json().get("manager", "Unknown")
        except requests.exceptions.RequestException as e:
            st.error(f"API Error when fetching manager for {team_name}: {str(e)}")
            return "Unknown"


    def fetch_team_captain(team_name):
        """Fetch latest captain for a team."""
        if not team_name:
            return "Unknown"

        try:
            response = requests.get(f"{API_URL}/team_captain/{team_name}")
            response.raise_for_status()
            return response.json().get("captain", "Unknown")
        except requests.exceptions.RequestException as e:
            st.error(f"API Error when fetching captain for {team_name}: {str(e)}")
            return "Unknown"


    def fetch_player_positions(players):
        """Fetch positions for a list of players."""
        if not players:
            return {}

        try:
            response = requests.post(f"{API_URL}/player_positions/", json=players)
            response.raise_for_status()
            return response.json().get("positions", {})
        except requests.exceptions.RequestException as e:
            st.error(f"API Error when fetching player positions: {str(e)}")
            return {}


    def fetch_player_info(player_name):
        """Fetch detailed information about a player."""
        if not player_name:
            return {"name": "", "position": "CM", "games_played": 0}

        try:
            response = requests.get(f"{API_URL}/player_info/{player_name}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"API Error when fetching info for {player_name}: {str(e)}")
            return {"name": player_name, "position": "CM", "games_played": 0}

    st.title("⚽ Soccer Player Stats Predictor")
    st.markdown("Predict player statistics for upcoming soccer matches")

    # Initialize session state for player lists and positions
    if 'home_players_selected' not in st.session_state:
        st.session_state.home_players_selected = []
    if 'away_players_selected' not in st.session_state:
        st.session_state.away_players_selected = []
    if 'player_positions' not in st.session_state:
        st.session_state.player_positions = {}

    # --- Fetch dropdown options from API ---
    leagues_data = fetch_api_data("leagues")
    teams_data = fetch_api_data("teams")
    referees_data = fetch_api_data("referees")
    managers_data = fetch_api_data("managers")
    captains_data = fetch_api_data("captains")

    # --- Sidebar for match inputs ---
    st.sidebar.header("Match Information")

    # League selection
    league = st.sidebar.selectbox(
        "League",
        leagues_data.get("leagues", ["Bundesliga", "Premier League", "La Liga", "Serie A", "Ligue 1"])
    )

    # Team selection with manager and captain auto-selection
    col1, col2 = st.sidebar.columns(2)

    with col1:
        st.write("Home Team")
        home_team = st.selectbox(
            "Select Home Team",
            teams_data.get("teams", ["Bayern Munich", "Borussia Dortmund"]),
            label_visibility="collapsed"
        )

    with col2:
        st.write("Away Team")
        away_team = st.selectbox(
            "Select Away Team",
            teams_data.get("teams", ["Borussia Dortmund", "Bayern Munich"]),
            index=1 if len(teams_data.get("teams", [])) > 1 else 0,
            label_visibility="collapsed"
        )

    # Auto-fetch managers and captains when teams change
    if 'previous_home_team' not in st.session_state or st.session_state.previous_home_team != home_team:
        st.session_state.home_manager = fetch_team_manager(home_team)
        st.session_state.home_captain = fetch_team_captain(home_team)
        st.session_state.previous_home_team = home_team

    if 'previous_away_team' not in st.session_state or st.session_state.previous_away_team != away_team:
        st.session_state.away_manager = fetch_team_manager(away_team)
        st.session_state.away_captain = fetch_team_captain(away_team)
        st.session_state.previous_away_team = away_team

    # Match officials
    referee = st.sidebar.selectbox(
        "Referee",
        referees_data.get("referees", ["Felix Brych"])
    )

    # Team management
    st.sidebar.subheader("Team Management")
    col1, col2 = st.sidebar.columns(2)

    with col1:
        st.write("Home Manager")
        home_manager = st.selectbox(
            "Home Team Manager",
            managers_data.get("managers", ["Julian Nagelsmann"]),
            index=managers_data.get("managers", []).index(
                st.session_state.home_manager) if st.session_state.home_manager in managers_data.get("managers", []) else 0,
            label_visibility="collapsed"
        )

    with col2:
        st.write("Away Manager")
        away_manager = st.selectbox(
            "Away Team Manager",
            managers_data.get("managers", ["Marco Rose"]),
            index=managers_data.get("managers", []).index(
                st.session_state.away_manager) if st.session_state.away_manager in managers_data.get("managers", []) else 0,
            label_visibility="collapsed"
        )

    # Team captains
    st.sidebar.subheader("Team Captains")
    col1, col2 = st.sidebar.columns(2)

    with col1:
        st.write("Home Captain")
        home_captain = st.selectbox(
            "Home Team Captain",
            captains_data.get("captains", ["manuel neuer"]),
            index=captains_data.get("captains", []).index(
                st.session_state.home_captain) if st.session_state.home_captain in captains_data.get("captains", []) else 0,
            label_visibility="collapsed"
        )

    with col2:
        st.write("Away Captain")
        away_captain = st.selectbox(
            "Away Team Captain",
            captains_data.get("captains", ["marco reus"]),
            index=captains_data.get("captains", []).index(
                st.session_state.away_captain) if st.session_state.away_captain in captains_data.get("captains", []) else 0,
            label_visibility="collapsed"
        )

    # Match date
    match_date = st.sidebar.date_input(
        "Match Date",
        datetime.date.today() + datetime.timedelta(days=1)
    )

    # --- Player input section ---
    st.header("Player Selection")

    # Fetch players for selected teams
    home_team_players = fetch_team_players(home_team)
    away_team_players = fetch_team_players(away_team)

    # Initialize selected players if teams change
    if 'previous_home_team_players' not in st.session_state or st.session_state.previous_home_team_players != home_team:
        st.session_state.home_players_selected = home_team_players.copy() if home_team_players else []
        st.session_state.previous_home_team_players = home_team

        # Fetch positions for home players
        if st.session_state.home_players_selected:
            positions = fetch_player_positions(st.session_state.home_players_selected)
            for player, position in positions.items():
                st.session_state.player_positions[player] = position

    if 'previous_away_team_players' not in st.session_state or st.session_state.previous_away_team_players != away_team:
        st.session_state.away_players_selected = away_team_players.copy() if away_team_players else []
        st.session_state.previous_away_team_players = away_team

        # Fetch positions for away players
        if st.session_state.away_players_selected:
            positions = fetch_player_positions(st.session_state.away_players_selected)
            for player, position in positions.items():
                st.session_state.player_positions[player] = position

    col1, col2 = st.columns(2)

    # Home team player selection
    with col1:
        st.subheader(f"Home Team: {home_team}")

        # Display currently selected players with positions
        st.write("Selected Players:")
        for i, player in enumerate(st.session_state.home_players_selected):
            cols = st.columns([3, 2, 1])
            cols[0].write(f"{i + 1}. {player}")

            # Position dropdown for each player
            current_pos = st.session_state.player_positions.get(player, "CM")
            # Ensure position is in the list, default to CM if not
            if current_pos not in POSITIONS:
                current_pos = "CM"

            new_pos = cols[1].selectbox(
                f"Position for {player}",
                POSITIONS,
                index=POSITIONS.index(current_pos),
                key=f"pos_home_{i}",
                label_visibility="collapsed"
            )
            st.session_state.player_positions[player] = new_pos

            # Remove button
            if cols[2].button("Remove", key=f"remove_home_{i}"):
                st.session_state.home_players_selected.pop(i)
                st.rerun()

        # Add new player
        st.write("Add Player:")
        home_cols = st.columns([3, 1])
        available_home_players = [p for p in home_team_players if p not in st.session_state.home_players_selected]

        selected_home_player = home_cols[0].selectbox(
            "Select Player",
            available_home_players,
            key="home_player_select",
            label_visibility="collapsed"
        )

        if home_cols[1].button("Add", key="add_home_player"):
            if selected_home_player and selected_home_player not in st.session_state.home_players_selected:
                st.session_state.home_players_selected.append(selected_home_player)

                # Fetch position for the new player
                player_info = fetch_player_info(selected_home_player)
                position = player_info.get("position", "CM")
                # Ensure position is in the list, default to CM if not
                if position not in POSITIONS:
                    position = "CM"
                st.session_state.player_positions[selected_home_player] = position

                st.rerun()

        # Clear all button
        if st.button("Clear All Home Players"):
            st.session_state.home_players_selected = []
            st.rerun()

    # Away team player selection
    with col2:
        st.subheader(f"Away Team: {away_team}")

        # Display currently selected players with positions
        st.write("Selected Players:")
        for i, player in enumerate(st.session_state.away_players_selected):
            cols = st.columns([3, 2, 1])
            cols[0].write(f"{i + 1}. {player}")

            # Position dropdown for each player
            current_pos = st.session_state.player_positions.get(player, "CM")
            # Ensure position is in the list, default to CM if not
            if current_pos not in POSITIONS:
                current_pos = "CM"

            new_pos = cols[1].selectbox(
                f"Position for {player}",
                POSITIONS,
                index=POSITIONS.index(current_pos),
                key=f"pos_away_{i}",
                label_visibility="collapsed"
            )
            st.session_state.player_positions[player] = new_pos

            # Remove button
            if cols[2].button("Remove", key=f"remove_away_{i}"):
                st.session_state.away_players_selected.pop(i)
                st.rerun()

        # Add new player
        st.write("Add Player:")
        away_cols = st.columns([3, 1])
        available_away_players = [p for p in away_team_players if p not in st.session_state.away_players_selected]

        selected_away_player = away_cols[0].selectbox(
            "Select Player",
            available_away_players,
            key="away_player_select",
            label_visibility="collapsed"
        )

        if away_cols[1].button("Add", key="add_away_player"):
            if selected_away_player and selected_away_player not in st.session_state.away_players_selected:
                st.session_state.away_players_selected.append(selected_away_player)

                # Fetch position for the new player
                player_info = fetch_player_info(selected_away_player)
                position = player_info.get("position", "CM")
                # Ensure position is in the list, default to CM if not
                if position not in POSITIONS:
                    position = "CM"
                st.session_state.player_positions[selected_away_player] = position

                st.rerun()

        # Clear all button
        if st.button("Clear All Away Players"):
            st.session_state.away_players_selected = []
            st.rerun()

    # --- Prediction button ---
    if st.button("Predict Player Stats", type="primary"):
        # Prepare request data
        match_data = {
            "home_team": home_team,
            "away_team": away_team,
            "league": league,
            "referee": referee,
            "home_manager": home_manager,
            "away_manager": away_manager,
            "home_captain": home_captain,
            "away_captain": away_captain,
            "datetime": match_date.strftime("%Y-%m-%d"),
            "predict_players": {
                "home": st.session_state.home_players_selected,
                "away": st.session_state.away_players_selected
            },
            "player_positions": st.session_state.player_positions
        }

        # Show loading spinner
        with st.spinner("Calculating predictions..."):
            # Call prediction API
            predictions = call_predict_api(match_data)

        if predictions:
            # Create tabs for each target
            tabs = st.tabs(TARGETS)

            # Process each target in its own tab
            for i, target in enumerate(TARGETS):
                with tabs[i]:
                    st.subheader(f"{target} Predictions")

                    # Create dataframe for this target
                    rows = []

                    for player in predictions:
                        # Get prediction value
                        pred_value = player["predictions"].get(target, 0)

                        # Get probabilities for thresholds
                        thresholds = get_threshold_ranges(target)
                        threshold_data = player["probabilities"].get(target, {})

                        # Basic player info
                        player_row = {
                            "Player": player["player_name"],
                            "Team": player["team"],
                            "Home/Away": "Home" if player["is_home"] else "Away",
                            "Position": st.session_state.player_positions.get(player["player_name"], "CM"),
                            f"Predicted {target}": round(pred_value, 2)
                        }

                        # Add over/under odds only, grouped: all overs first, then unders
                        for threshold in thresholds:
                            threshold_str = str(threshold)
                            if threshold_str in threshold_data:
                                # Over
                                over_data = threshold_data[threshold_str].get("over", {})
                                over_odds = over_data.get("fair_odds", 999.99)
                                player_row[f"Over {threshold} Odds"] = format_odds(over_odds)

                        # Add unders after overs
                        for threshold in thresholds:
                            threshold_str = str(threshold)
                            if threshold_str in threshold_data:
                                # Under
                                under_data = threshold_data[threshold_str].get("under", {})
                                under_odds = under_data.get("fair_odds", 999.99)
                                player_row[f"Under {threshold} Odds"] = format_odds(under_odds)

                        rows.append(player_row)

                    # Create and display dataframe
                    df = pd.DataFrame(rows)
                    st.dataframe(df, use_container_width=True)

            # Add export button
            st.header("Export Predictions")

            if st.button("Export to Excel"):
                with st.spinner("Generating Excel file..."):
                    excel_data = call_export_api(match_data)

                if excel_data:
                    # Create download button
                    filename = f"predictions_{home_team}_vs_{away_team}_{match_date}.xlsx"
                    st.download_button(
                        label="Download Excel File",
                        data=excel_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        else:
            st.error("Failed to get predictions. Please check if the API server is running.")

    # --- Footer ---
    st.markdown("---")
    st.markdown("⚽ Soccer Player Stats Predictor")
