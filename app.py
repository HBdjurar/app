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
    API_URL = st.sidebar.text_input("API URL", "http://85.229.213.182:8888")
    TARGETS = [
        'Goals', 'Assists', 'Shots', 'Shots on Target',
        'Yellow Cards', 'Tackles', 'Fouls Committed'
    ]

    POSITIONS = ["GK", "CB", "LB", "RB", "LWB", "RWB", "CDM", "CM", "CAM", "LM", "RM", "LW", "RW", "CF", "ST"]


    # --- Helper functions ---
    @st.cache_data(show_spinner=False)
    def fetch_api_data(endpoint):
        try:
            response = requests.get(f"{API_URL}/{endpoint}/")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"API Error when fetching {endpoint}: {str(e)}")
            return {}


    def fetch_team_players(team_name):
        if not team_name:
            return []
        try:
            response = requests.get(f"{API_URL}/team_players/{team_name}")
            response.raise_for_status()
            return response.json().get("players", [])
        except requests.exceptions.RequestException as e:
            st.error(f"API Error when fetching players for {team_name}: {str(e)}")
            return []


    def fetch_common_xi(team_name):
        try:
            response = requests.get(f"{API_URL}/common_xi/{team_name}")
            response.raise_for_status()
            return response.json().get("players", [])
        except requests.exceptions.RequestException as e:
            st.error(f"API Error when fetching common XI for {team_name}: {str(e)}")
            return []


    def fetch_player_info(player_name):
        try:
            response = requests.get(f"{API_URL}/player_info/{player_name}")
            response.raise_for_status()
            return response.json()
        except:
            return {"position": "CM"}


    def fetch_player_positions(players):
        try:
            response = requests.post(f"{API_URL}/player_positions/", json=players)
            response.raise_for_status()
            return response.json().get("positions", {})
        except:
            return {player: "CM" for player in players}


    def format_odds(odds):
        return "100+" if odds >= 100 else f"{odds:.2f}"


    def get_threshold_ranges(target):
        if target in ['Goals', 'Assists']:
            return [0.5, 1.5, 2.5, 3.5]
        elif target == 'Yellow Cards':
            return [0.5]
        else:
            return [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5]


    def call_predict_api(match_data):
        try:
            response = requests.post(f"{API_URL}/predict/", json=match_data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"API Error: {str(e)}")
            return None


    def call_export_api(match_data):
        try:
            response = requests.post(f"{API_URL}/export/", json=match_data, stream=True)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            st.error(f"Export Error: {str(e)}")
            return None


    # --- Callbacks for team selection ---
    def on_home_team_change():
        team = st.session_state.home_team_select
        st.session_state.home_players_selected = fetch_common_xi(team)
        positions = fetch_player_positions(st.session_state.home_players_selected)
        st.session_state.player_positions.update(positions)

        # Fetch manager and captain
        try:
            manager_data = fetch_api_data(f"team_manager/{team}")
            if manager_data and "manager" in manager_data:
                manager_index = st.session_state.dropdown_data['managers'].index(manager_data["manager"]) if \
                manager_data["manager"] in st.session_state.dropdown_data['managers'] else 0
                st.session_state.home_manager_select = st.session_state.dropdown_data['managers'][manager_index]
        except:
            pass

        try:
            captain_data = fetch_api_data(f"team_captain/{team}")
            if captain_data and "captain" in captain_data:
                captain_index = st.session_state.dropdown_data['captains'].index(captain_data["captain"]) if \
                captain_data["captain"] in st.session_state.dropdown_data['captains'] else 0
                st.session_state.home_captain_select = st.session_state.dropdown_data['captains'][captain_index]
        except:
            pass


    def on_away_team_change():
        team = st.session_state.away_team_select
        st.session_state.away_players_selected = fetch_common_xi(team)
        positions = fetch_player_positions(st.session_state.away_players_selected)
        st.session_state.player_positions.update(positions)

        # Fetch manager and captain
        try:
            manager_data = fetch_api_data(f"team_manager/{team}")
            if manager_data and "manager" in manager_data:
                manager_index = st.session_state.dropdown_data['managers'].index(manager_data["manager"]) if \
                manager_data["manager"] in st.session_state.dropdown_data['managers'] else 0
                st.session_state.away_manager_select = st.session_state.dropdown_data['managers'][manager_index]
        except:
            pass

        try:
            captain_data = fetch_api_data(f"team_captain/{team}")
            if captain_data and "captain" in captain_data:
                captain_index = st.session_state.dropdown_data['captains'].index(captain_data["captain"]) if \
                captain_data["captain"] in st.session_state.dropdown_data['captains'] else 0
                st.session_state.away_captain_select = st.session_state.dropdown_data['captains'][captain_index]
        except:
            pass

    # --- Fetch dropdown data once ---
    if 'dropdown_data' not in st.session_state:
        st.session_state.dropdown_data = {
            'leagues': fetch_api_data("leagues").get("leagues", []),
            'teams': fetch_api_data("teams").get("teams", []),
            'referees': fetch_api_data("referees").get("referees", []),
            'managers': fetch_api_data("managers").get("managers", []),
            'captains': fetch_api_data("captains").get("captains", [])
        }

    # --- Initialize session state variables ---
    if 'player_positions' not in st.session_state:
        st.session_state.player_positions = {}

    if 'home_players_selected' not in st.session_state:
        st.session_state.home_players_selected = []

    if 'away_players_selected' not in st.session_state:
        st.session_state.away_players_selected = []

    # --- UI Layout ---
    st.title("⚽ Soccer Player Stats Predictor")

    league = st.sidebar.selectbox("League", st.session_state.dropdown_data['leagues'])
    col1, col2 = st.sidebar.columns(2)
    with col1:
        home_team = st.selectbox("Home Team", st.session_state.dropdown_data['teams'],
                                 key="home_team_select", on_change=on_home_team_change)
    with col2:
        away_team = st.selectbox("Away Team", st.session_state.dropdown_data['teams'],
                                 index=1 if len(st.session_state.dropdown_data['teams']) > 1 else 0,
                                 key="away_team_select", on_change=on_away_team_change)

    referee = st.sidebar.selectbox("Referee", st.session_state.dropdown_data['referees'])

    st.sidebar.subheader("Team Management")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        home_manager = st.selectbox("Home Team Manager", st.session_state.dropdown_data['managers'], key="home_manager_select")
    with col2:
        away_manager = st.selectbox("Away Team Manager", st.session_state.dropdown_data['managers'], key="away_manager_select")

    st.sidebar.subheader("Team Captains")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        home_captain = st.selectbox("Home Team Captain", st.session_state.dropdown_data['captains'], key="home_captain_select")
    with col2:
        away_captain = st.selectbox("Away Team Captain", st.session_state.dropdown_data['captains'], key="away_captain_select")

    match_date = st.sidebar.date_input("Match Date", datetime.date.today() + datetime.timedelta(days=1))

    st.header("Player Selection")
    home_team_players = fetch_team_players(home_team)
    away_team_players = fetch_team_players(away_team)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(f"Home Team: {home_team}")
        st.write("Selected Players:")
        for i, player in enumerate(st.session_state.home_players_selected):
            cols = st.columns([3, 2, 1])
            cols[0].write(f"{i + 1}. {player}")
            pos = st.session_state.player_positions.get(player, "CM")
            pos = pos if pos in POSITIONS else "CM"
            new_pos = cols[1].selectbox("", POSITIONS, index=POSITIONS.index(pos), key=f"home_pos_{i}",
                                        label_visibility="collapsed")
            st.session_state.player_positions[player] = new_pos
            if cols[2].button("Remove", key=f"remove_home_{i}"):
                st.session_state.home_players_selected.pop(i)
                st.rerun()

        available_home_players = [p for p in home_team_players if p not in st.session_state.home_players_selected]
        home_cols = st.columns([3, 1])
        selected_home_player = home_cols[0].selectbox("Select Player", available_home_players, key="home_player_select")
        if home_cols[1].button("Add", key="add_home_player"):
            if selected_home_player:
                st.session_state.home_players_selected.append(selected_home_player)
                pos = fetch_player_info(selected_home_player).get("position", "CM")
                st.session_state.player_positions[selected_home_player] = pos
                st.rerun()

        home_buttons = st.columns(2)
        if home_buttons[0].button("Load All Home Players"):
            st.session_state.home_players_selected = home_team_players
            positions = fetch_player_positions(home_team_players)
            st.session_state.player_positions.update(positions)
            st.rerun()
        if home_buttons[1].button("Clear All Home Players"):
            st.session_state.home_players_selected = []
            st.rerun()

    with col2:
        st.subheader(f"Away Team: {away_team}")
        st.write("Selected Players:")
        for i, player in enumerate(st.session_state.away_players_selected):
            cols = st.columns([3, 2, 1])
            cols[0].write(f"{i + 1}. {player}")
            pos = st.session_state.player_positions.get(player, "CM")
            pos = pos if pos in POSITIONS else "CM"
            new_pos = cols[1].selectbox("", POSITIONS, index=POSITIONS.index(pos), key=f"away_pos_{i}",
                                        label_visibility="collapsed")
            st.session_state.player_positions[player] = new_pos
            if cols[2].button("Remove", key=f"remove_away_{i}"):
                st.session_state.away_players_selected.pop(i)
                st.rerun()

        available_away_players = [p for p in away_team_players if p not in st.session_state.away_players_selected]
        away_cols = st.columns([3, 1])
        selected_away_player = away_cols[0].selectbox("Select Player", available_away_players, key="away_player_select")
        if away_cols[1].button("Add", key="add_away_player"):
            if selected_away_player:
                st.session_state.away_players_selected.append(selected_away_player)
                pos = fetch_player_info(selected_away_player).get("position", "CM")
                st.session_state.player_positions[selected_away_player] = pos
                st.rerun()

        away_buttons = st.columns(2)
        if away_buttons[0].button("Load All Away Players"):
            st.session_state.away_players_selected = away_team_players
            positions = fetch_player_positions(away_team_players)
            st.session_state.player_positions.update(positions)
            st.rerun()
        if away_buttons[1].button("Clear All Away Players"):
            st.session_state.away_players_selected = []
            st.rerun()

    if st.button("Predict Player Stats", type="primary"):
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

        with st.spinner("Calculating predictions..."):
            predictions = call_predict_api(match_data)

        if predictions:
            tabs = st.tabs(TARGETS)
            for i, target in enumerate(TARGETS):
                with tabs[i]:
                    st.subheader(f"{target} Predictions")
                    rows = []
                    for player in predictions:
                        pred_value = player["predictions"].get(target, 0)
                        thresholds = get_threshold_ranges(target)
                        threshold_data = player["probabilities"].get(target, {})
                        row = {
                            "Player": player["player_name"],
                            "Team": player["team"],
                            "Home/Away": "Home" if player["is_home"] else "Away",
                            "Position": st.session_state.player_positions.get(player["player_name"], "CM"),
                            f"Predicted {target}": round(pred_value, 2)
                        }
                        for threshold in thresholds:
                            str_t = str(threshold)
                            if str_t in threshold_data:
                                row[f"Over {threshold} Odds"] = format_odds(
                                    threshold_data[str_t]["over"].get("fair_odds", 999.99))
                        for threshold in thresholds:
                            str_t = str(threshold)
                            if str_t in threshold_data:
                                row[f"Under {threshold} Odds"] = format_odds(
                                    threshold_data[str_t]["under"].get("fair_odds", 999.99))
                        rows.append(row)
                    df = pd.DataFrame(rows)
                    st.dataframe(df, use_container_width=True)

            st.header("Export Predictions")
            if st.button("Export to Excel"):
                with st.spinner("Generating Excel file..."):
                    excel_data = call_export_api(match_data)
                if excel_data:
                    filename = f"predictions_{home_team}_vs_{away_team}_{match_date}.xlsx"
                    st.download_button(
                        label="Download Excel File",
                        data=excel_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

    st.markdown("---")
    st.markdown("⚽ Soccer Player Stats Predictor")
