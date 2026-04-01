import pandas as pd
import os
from datetime import datetime

FILENAME = 'apored_reload_stats.csv'
MAP_MODES = {"1": "reload venture", "2": "oasis", "3": "slurp rush"}

def load_data():
    if os.path.exists(FILENAME):
        return pd.read_csv(FILENAME)
    return pd.DataFrame(columns=['runde', 'platz', 'kills', 'map', 'win_vorher', 'stunde'])

def calculate_kelly(prob, yes_pct):
    # Umrechnung: Twitch-Prozent in Dezimalquote
    # Wenn 20% auf JA sind, ist die Quote 100/20 = 5.0
    if yes_pct <= 0: return 0
    odds = 100 / yes_pct
    
    b = odds - 1
    p = prob / 100
    if b <= 0: return 0
    
    # Kelly Formel
    f = (p * (b + 1) - 1) / b
    # Wir nutzen "Half-Kelly" (f / 2) für mehr Sicherheit
    return max(0, f / 2)

def get_prediction(target_kills, map_id, last_was_win, yes_pct):
    df = load_data()
    map_name = MAP_MODES.get(map_id, "unbekannt")
    
    if df.empty:
        return "Keine Daten vorhanden. Trag erst eine Runde ein!"

    # 1. Basis-Wahrscheinlichkeit (Map + Form)
    map_df = df[df['map'] == map_name]
    prob = (map_df['kills'] >= target_kills).mean() * 100 if not map_df.empty else 35
    
    # Form-Kurve der letzten 3 Runden
    if len(df) >= 3:
        form = (df.tail(3)['kills'].mean() - df['kills'].mean()) * 2
        prob += form

    if last_was_win: prob -= 10 # SBMM-Malus
    prob = max(5, min(95, prob))
    
    # 2. Kelly & EV Berechnung
    odds = 100 / yes_pct
    expected_value = (prob / 100) * odds
    kelly_pct = calculate_kelly(prob, yes_pct) * 100
    
    print(f"\n--- TWITCH LIVE-ANALYSE: {map_name.upper()} ---")
    print(f"Deine Gewinnchance: {prob:.1f}%")
    print(f"Aktuelle Quote für JA: {odds:.2f}")
    print(f"Erwartungswert (EV): {expected_value:.2f} (Über 1.0 ist gut!)")
    
    if expected_value > 1.05 and kelly_pct > 0:
        print(f"EMPFOHLENER EINSATZ: {kelly_pct:.1f}% deiner Punkte.")
        return ">>> TIPP: JA - Die Quote ist profitabel!"
    elif expected_value < 0.95:
        return ">>> TIPP: NEIN oder SKIP - Zu viele Leute wetten auf JA (Quote zu schlecht)."
    else:
        return ">>> TIPP: ZU UNSICHER - Finger weg."

# --- MAIN LOOP ---
print("=== APORED RELOAD PREDICTOR V2 (Twitch-Optimiert) ===")
while True:
    print("\n[1] Runde eintragen | [2] Twitch-Check (Prozent-Eingabe) | [q] Ende")
    choice = input("Wähle: ")

    if choice == '1':
        p = int(input("Platz: "))
        k = int(input("Kills: "))
        m = input("Map [1]Venture, [2]Oasis, [3]Slurp: ")
        wv = input("Vorher Sieg? (j/n): ").lower() == 'j'
        
        df = load_data()
        neue_runde = pd.DataFrame([{'runde': len(df)+1, 'platz': p, 'kills': k, 'map': MAP_MODES.get(m), 'win_vorher': wv, 'stunde': datetime.now().hour}])
        pd.concat([df, neue_runde], ignore_index=True).to_csv(FILENAME, index=False)
        print("Gespeichert!")
    
    elif choice == '2':
        target = int(input("Wette (Kills): "))
        m = input("Map [1]Venture, [2]Oasis, [3]Slurp: ")
        l_win = input("Letzte Runde Sieg? (j/n): ").lower() == 'j'
        yes_pct = float(input("Wie viel % steht bei JA? (z.B. 75): "))
        print(get_prediction(target, m, l_win, yes_pct))
    
    elif choice == 'q': break

