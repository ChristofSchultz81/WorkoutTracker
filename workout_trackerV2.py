import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import requests
import io

# -----------------------------------------------------------------------------
# 1. Nextcloud Konfiguration & WebDAV-Funktionen
# -----------------------------------------------------------------------------
# Falls in der Streamlit Cloud, nutzen wir Secrets. Lokal tragen wir es unten ein.
NC_URL = st.secrets.get("NC_URL", "https://cloud.htw-berlin.de/remote.php/dav/files/schultz")
NC_USER = st.secrets.get("NC_USER", "schultz")
NC_PASS = st.secrets.get("NC_PASS", "yjP2M-XYP2E-MNcDM-gMsAK-jeYdC")

def load_csv_from_nextcloud(filename, default_columns):
    """Lädt eine CSV-Datei aus Nextcloud. Erstellt sie, falls nicht vorhanden."""
    url = f"{NC_URL}/{filename}" if not NC_URL.endswith('/') else f"{NC_URL}{filename}"
    try:
        response = requests.get(url, auth=(NC_USER, NC_PASS))
        if response.status_code == 200:
            return pd.read_csv(io.StringIO(response.text))
        elif response.status_code == 404:
            # Datei existiert noch nicht -> leer anlegen
            df = pd.DataFrame(columns=default_columns)
            save_csv_to_nextcloud(filename, df)
            return df
    except Exception as e:
        st.error(f"Fehler beim Laden von {filename} aus Nextcloud: {e}")
    return pd.DataFrame(columns=default_columns)

def save_csv_to_nextcloud(filename, df):
    """Speichert einen Pandas DataFrame als CSV direkt in Nextcloud."""
    url = f"{NC_URL}/{filename}" if not NC_URL.endswith('/') else f"{NC_URL}{filename}"
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    try:
        response = requests.put(url, data=csv_buffer.getvalue().encode('utf-8'), auth=(NC_USER, NC_PASS))
        if response.status_code in [201, 204]:
            return True
    except Exception as e:
        st.error(f"Fehler beim Speichern in Nextcloud: {e}")
    return False

# -----------------------------------------------------------------------------
# 2. Daten laden
# -----------------------------------------------------------------------------
# Laden/Initialisieren der beiden benötigten Tabellen
df_exercises = load_csv_from_nextcloud("exercises.csv", ["Exercise"])
df_logs = load_csv_from_nextcloud("logs.csv", [
    "Date", "Exercise", 
    "Set1_Reps", "Set1_Weight", 
    "Set2_Reps", "Set2_Weight", 
    "Set3_Reps", "Set3_Weight", 
    "Total_Reps"
])

exercises = df_exercises["Exercise"].tolist()

# -----------------------------------------------------------------------------
# 3. Benutzeroberfläche (Streamlit)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Nextcloud Workout Tracker", layout="wide")
st.title("☁️ Mein Nextcloud Workout Tracker")

col1, col2 = st.columns(2)

# Spalte 1: Übung hinzufügen
with col1:
    st.subheader("1. Neue Übung hinzufügen")
    new_exercise = st.text_input("Name der Übung (z.B. Kreuzheben):")
    
    if st.button("Übung speichern"):
        if len(exercises) >= 10:
            st.error("Du hast bereits das Limit von 10 Übungen erreicht!")
        elif new_exercise and new_exercise not in exercises:
            # Zeile an den Übungs-DataFrame anhängen und hochladen
            new_row = pd.DataFrame([{"Exercise": new_exercise}])
            df_exercises = pd.concat([df_exercises, new_row], ignore_index=True)
            if save_csv_to_nextcloud("exercises.csv", df_exercises):
                st.success(f"Übung '{new_exercise}' wurde in Nextcloud gespeichert!")
                st.rerun()
        elif new_exercise in exercises:
            st.warning("Diese Übung existiert bereits.")

# Spalte 2: Training eintragen (3 Sätze)
with col2:
    st.subheader("2. Training eintragen")
    if exercises:
        selected_ex = st.selectbox("Übung auswählen:", exercises)
        log_date = st.date_input("Datum", datetime.date.today())
        
        st.write("---")
        st.markdown("**Satz-Daten eingeben:**")
        
        sat_col1, sat_col2, sat_col3 = st.columns(3)
        
        with sat_col1:
            st.caption("⚡ **Satz 1**")
            s1_reps = st.number_input("Wdh. (Satz 1)", min_value=0, step=1, key="s1_r")
            s1_weight = st.number_input("Gewicht 1 (kg)", min_value=0.0, step=0.5, key="s1_w")
            
        with sat_col2:
            st.caption("⚡ **Satz 2**")
            s2_reps = min_value=0, st.number_input("Wdh. (Satz 2)", min_value=0, step=1, key="s2_r")
            s2_weight = st.number_input("Gewicht 2 (kg)", min_value=0.0, step=0.5, key="s2_w")
            
        with sat_col3:
            st.caption("⚡ **Satz 3**")
            s3_reps = st.number_input("Wdh. (Satz 3)", min_value=0, step=1, key="s3_r")
            s3_weight = st.number_input("Gewicht 3 (kg)", min_value=0.0, step=0.5, key="s3_w")

        st.write("---")
        if st.button("Trainingseinheit speichern"):
            total_reps = s1_reps + s2_reps + s3_reps
            
            # Neue Zeile für das Log-Buch bauen
            new_log = pd.DataFrame([{
                "Date": str(log_date),
                "Exercise": selected_ex,
                "Set1_Reps": s1_reps, "Set1_Weight": s1_weight,
                "Set2_Reps": s2_reps, "Set2_Weight": s2_weight,
                "Set3_Reps": s3_reps, "Set3_Weight": s3_weight,
                "Total_Reps": total_reps
            }])
            
            df_logs = pd.concat([df_logs, new_log], ignore_index=True)
            if save_csv_to_nextcloud("logs.csv", df_logs):
                st.success("Erfolgreich in Nextcloud-CSV gespeichert!")
                st.rerun()
    else:
        st.info("Bitte füge zuerst auf der linken Seite eine Übung hinzu.")

st.divider()

# -----------------------------------------------------------------------------
# 4. Diagramm auswerten
# -----------------------------------------------------------------------------
st.subheader("📈 Dein Trainingsfortschritt")

if not df_logs.empty:
    # Daten für Plotly vorbereiten
    df_plot = df_logs.copy()
    df_plot["Date"] = pd.to_datetime(df_plot["Date"]).dt.date
    df_plot["Total_Reps"] = pd.to_numeric(df_plot["Total_Reps"])
    
    df_grouped = df_plot.groupby(["Date", "Exercise"], as_index=False)["Total_Reps"].sum()
    
    fig = px.line(
        df_grouped,
        x="Date",
        y="Total_Reps",
        color="Exercise",
        markers=True,
        title="Gesamtwiederholungen über Zeit",
        labels={"Date": "Datum", "Total_Reps": "Wiederholungen (Gesamt)", "Exercise": "Übung"}
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.write("Noch keine CSV-Daten in Nextcloud vorhanden.")