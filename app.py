import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- SETUP ---
st.set_page_config(page_title="ApoRed Predictor Cloud", layout="centered")
st.title("ApoRed Reload Predictor (Cloud)")

# Verbindung zu Google Sheets herstellen
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Versuche Daten zu lesen
        data = conn.read(worksheet="stats", ttl=0)
        if data is None or data.empty:
            return pd.DataFrame(columns=['runde', 'platz', 'kills', 'map', 'win_vorher', 'stunde'])
        return data
    except Exception as e:
        # Falls das Sheet komplett leer ist oder nicht existiert
        st.warning("Konnte keine Daten laden. Starte mit leeres Tabelle.")
        return pd.DataFrame(columns=['runde', 'platz', 'kills', 'map', 'win_vorher', 'stunde'])

def calculate_kelly(prob, yes_pct):
    if yes_pct <= 0 or yes_pct >= 100: return 0
    odds = 100 / yes_pct
    b = odds - 1
    p = prob / 100
    if b <= 0: return 0
    f = (p * (b + 1) - 1) / b
    return max(0, f / 2)

MAP_MODES = {"1": "venture", "2": "oasis", "3": "slurp rush"}
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
        
        # Sicherstellen, dass Map-Daten existieren
        map_df = df[df['map'] == map_name] if not df.empty else pd.DataFrame()
        
        if not map_df.empty:
            prob = (map_df['kills'] >= target).mean() * 100
        else:
            prob = 35.0  # Fallback, wenn keine Daten für die Map da sind
        
        # Form-Kurve berechnen (nur wenn genug Daten da sind)
        if len(df) >= 3:
            try:
                form = (df.tail(3)['kills'].mean() - df['kills'].mean()) * 2
                prob += form
            except:
                pass
        
        if l_win: 
            prob -= 10
            
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
            # Neue Zeile erstellen
            new_row = pd.DataFrame([{
                'runde': len(df) + 1, 
                'platz': p, 
                'kills': k, 
                'map': MAP_MODES[m_add], 
                'win_vorher': wv, 
                'stunde': datetime.now().hour
            }])
            
            # Daten zusammenführen
            updated_df = pd.concat([df, new_row], ignore_index=True)
            
            try:
                # Versuch, ins Google Sheet zu schreiben
                conn.update(worksheet="stats", data=updated_df)
                st.success("Runde erfolgreich in Google Sheets gespeichert!")
                st.cache_data.clear() # Cache leeren, damit Tab 3 sofort aktuell ist
                st.rerun() # App neu laden, um Daten-Refresh zu erzwingen
            except Exception as e:
                st.error(f"Fehler beim Speichern: {e}")
                st.info("Hast du den Service Account in den Secrets konfiguriert?")

with tab3:
    st.header("Daten Historie")
    if not df.empty:
        st.dataframe(df.sort_values(by='runde', ascending=False).head(15))
    else:
        st.info("Noch keine Daten vorhanden.")
