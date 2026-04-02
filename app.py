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
    try:
        data = conn.read(worksheet="stats", ttl=0)
        if data is None or data.empty:
            return pd.DataFrame(columns=['runde', 'platz', 'kills', 'map', 'win_vorher', 'stunde'])
        return data
    except Exception:
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

# Tabs erweitert um "Daten verwalten"
tab1, tab2, tab3, tab4 = st.tabs(["Check Wette", "Runde eintragen", "Statistik", "Daten verwalten"])

with tab1:
    st.header("Twitch Live-Analyse")
    target = st.number_input("Wette (Kills):", min_value=0, value=10)
    m_id = st.selectbox("Map:", options=list(MAP_MODES.keys()), format_func=lambda x: MAP_MODES[x])
    l_win = st.checkbox("Letzte Runde Sieg?")
    yes_pct = st.slider("Wie viel % steht bei JA?", 1, 99, 50)

    if st.button("Chance berechnen"):
        map_name = MAP_MODES[m_id]
        map_df = df[df['map'] == map_name] if not df.empty else pd.DataFrame()
        
        if map_df.empty:
            st.info(f"Keine Daten für '{map_name}' vorhanden.")
        else:
            prob = (map_df['kills'] >= target).mean() * 100
            if len(df) >= 3:
                try:
                    form = (df.tail(3)['kills'].mean() - df['kills'].mean()) * 2
                    prob += form
                except: pass
            
            if l_win: prob -= 10
            prob = max(5, min(95, prob))
            
            odds = 100 / yes_pct
            ev = (prob / 100) * odds
            kelly = calculate_kelly(prob, yes_pct) * 100
            
            st.metric("Gewinnchance", f"{prob:.1f}%")
            if ev > 1.05 and kelly > 0:
                st.success(f"TIPP: JA (EV: {ev:.2f}) — Setze {kelly:.1f}% deines Vermögens")
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
            new_row = pd.DataFrame([{
                'runde': len(df) + 1, 
                'platz': p, 'kills': k, 
                'map': MAP_MODES[m_add], 
                'win_vorher': wv, 
                'stunde': datetime.now().hour
            }])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            try:
                conn.update(worksheet="stats", data=updated_df)
                st.success("Gespeichert!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Fehler: {e}")

with tab3:
    st.header("Daten Historie")
    if not df.empty:
        st.dataframe(df.sort_values(by='runde', ascending=False).head(15))
    else:
        st.info("Noch keine Daten vorhanden.")

with tab4:
    st.header("Daten korrigieren")
    if df.empty:
        st.info("Keine Daten zum Löschen vorhanden.")
    else:
        st.subheader("Bestimmte Runde löschen")
        # Auswahl der Runde über die ID (Spalte 'runde')
        runde_to_delete = st.selectbox("Wähle die Runde aus, die gelöscht werden soll:", options=df['runde'].tolist())
        
        if st.button("Ausgewählte Runde unwiderruflich löschen"):
            # Filtere alle Zeilen heraus, die NICHT die gewählte Nummer haben
            updated_df = df[df['runde'] != runde_to_delete]
            
            # Optional: Runden-Nummern neu sortieren, damit keine Lücken entstehen
            updated_df = updated_df.reset_index(drop=True)
            updated_df['runde'] = range(1, len(updated_df) + 1)
            
            try:
                conn.update(worksheet="stats", data=updated_df)
                st.success(f"Runde {runde_to_delete} wurde gelöscht!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Fehler beim Löschen: {e}")

        st.divider()
        if st.button("Nur die allerletzte Zeile löschen"):
            updated_df = df.iloc[:-1] # Entfernt die letzte Zeile
            try:
                conn.update(worksheet="stats", data=updated_df)
                st.success("Letzte Zeile gelöscht!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Fehler beim Löschen: {e}")
