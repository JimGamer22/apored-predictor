import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- SETUP ---
st.set_page_config(page_title="ApoRed Predictor Cloud", layout="centered")
st.title("🔴 ApoRed Reload Predictor (Cloud)")

# Verbindung zu Google Sheets herstellen
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(worksheet="stats", ttl=0) # ttl=0 sorgt für Echtzeit-Daten

def calculate_kelly(prob, yes_pct):
    if yes_pct <= 0: return 0
    odds = 100 / yes_pct
    b = odds - 1
    p = prob / 100
    if b <= 0: return 0
    f = (p * (b + 1) - 1) / b
    return max(0, f / 2)

MAP_MODES = {"1": "reload venture", "2": "oasis", "3": "slurp rush"}
df = load_data()

tab1, tab2, tab3 = st.tabs(["Check Wette", "Runde eintragen", "Statistik"])

with tab1:
    st.header("Twitch Live-Analyse")
    target = st.number_input("Wette (Kills):", min_value=0, value=10)
    m_id = st.selectbox("Map:", options=list(MAP_MODES.keys()), format_func=lambda x: MAP_MODES[x])
    l_win = st.checkbox("Letzte Runde Sieg?")
    yes_pct = st.slider("Wie viel % steht bei JA?", 1, 99, 50)

    if st.button("Chance berechnen"):
        map_name = MAP_MODES[m_id]
        map_df = df[df['map'] == map_name] if not df.empty else pd.DataFrame()
        prob = (map_df['kills'] >= target).mean() * 100 if not map_df.empty else 35
        
        # Form-Kurve
        if len(df) >= 3:
            form = (df.tail(3)['kills'].mean() - df['kills'].mean()) * 2
            prob += form
        if l_win: prob -= 10
        prob = max(5, min(95, prob))
        
        odds = 100 / yes_pct
        ev = (prob / 100) * odds
        kelly = calculate_kelly(prob, yes_pct) * 100
        
        st.metric("Gewinnchance", f"{prob:.1f}%")
        if ev > 1.05 and kelly > 0:
            st.success(f"TIPP: JA (EV: {ev:.2f}) - Einsatz: {kelly:.1f}%")
        else:
            st.error(f"KEIN JA (EV: {ev:.2f})")

with tab2:
    st.header("Neue Daten")
    with st.form("add_round"):
        p = st.number_input("Platzierung", 1, 50, 1)
        k = st.number_input("Kills", 0, 100, 5)
        m_add = st.selectbox("Map", options=list(MAP_MODES.keys()), format_func=lambda x: MAP_MODES[x])
        wv = st.checkbox("War Sieg?")
        submitted = st.form_submit_button("In Cloud speichern")
        
        if submitted:
            # Neue Daten anhängen
            new_row = pd.DataFrame([{
                'runde': len(df)+1, 'platz': p, 'kills': k, 
                'map': MAP_MODES[m_add], 'win_vorher': wv, 
                'stunde': datetime.now().hour
            }])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            # Direkt ins Google Sheet schreiben
            conn.update(worksheet="stats", data=updated_df)
            st.success("Runde in Google Sheets gespeichert!")
            st.cache_data.clear() # Cache leeren für neue Daten

with tab3:
    st.header("Daten Historie")
    st.dataframe(df.tail(15))
