# Thema: 
# Datenaufbereitung und Visualisierung globaler COVID-19-Daten aus dem Our World in Data-Datensatz  
# Implementierung in Python/R mit Pandas/Tidyverse und DuckDB/SQLite. Fokus auf Zeitreihenanalyse und geographische Visualisierung. 
# Interaktives Dashboard

import pandas as pd
import duckdb
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
# CSV im Projektordner ODER eine Ebene darüber suchen
_CANDIDATES = [
    os.path.join(_HERE, 'owid-covid-data.csv'),
    os.path.join(_HERE, '..', 'owid-covid-data.csv'),
]
RAW_CSV = next((p for p in _CANDIDATES if os.path.exists(p)), _CANDIDATES[0])
DB_PATH = os.path.join(_HERE, 'covid.duckdb')

# Der Originaldatensatz hat 67 Spalten -> reduziert auf 21 wegen Fokus auf Zeitreihen und globaler Visualisierung. Spalten wie (z.B. Raucherquote, Diabetesrate) ausgelassen. 
# Frage: Sinnvoll für diese Analyse? (Frage: Wie könnte man die restlichen Spalten sinnvoll einbringen oder passt das?) Fokus auf 21 relevante Spalten.
KEEP_COLS = [
    'iso_code', 'continent', 'location', 'date',
    'new_cases', 'new_cases_smoothed',
    'new_deaths', 'new_deaths_smoothed',
    'total_cases', 'total_deaths',
    'total_cases_per_million', 'total_deaths_per_million',
    'new_vaccinations_smoothed',
    'people_vaccinated_per_hundred',
    'people_fully_vaccinated_per_hundred',
    'population',
    'gdp_per_capita',
    'median_age',
    # Krankenhausdaten – nur für ~30 Länder verfügbar
    'icu_patients_per_million',
    'hosp_patients_per_million',
    'weekly_hosp_admissions_per_million',
]

# Tageswerte = neue Fälle/Tode/Impfungen PRO TAG.
# Können negativ werden, wenn ein Land frühere Zahlen nach unten korrigiert.
# Werden später auf 0 gesetzt (negativ ergibt im Diagramm keinen Sinn).
FLOW_COLS = [
    'new_cases', 'new_deaths',
    'new_cases_smoothed', 'new_deaths_smoothed',
    'new_vaccinations_smoothed',
]

# Kumulierte Werte = Gesamtsumme bis zum jeweiligen Tag (laufend addiert).
# Können logisch nie sinken. Fehlt ein Tag, wird der letzte Wert weitergezogen.
CUMUL_COLS = [
    'total_cases', 'total_deaths',
    'total_cases_per_million', 'total_deaths_per_million',
]

# Impfquoten = Anteil der geimpften Bevölkerung in Prozent.
# Werden nur unregelmäßig gemeldet, steigen aber nur an (sinken nie).
# Lücken werden daher mit dem letzten bekannten Wert gefüllt.
VAX_COLS = [
    'people_vaccinated_per_hundred',
    'people_fully_vaccinated_per_hundred',
]


def load_and_clean() -> pd.DataFrame:
    print("  Lese CSV ...")
    df = pd.read_csv(RAW_CSV, parse_dates=['date'], usecols=KEEP_COLS)
    print(f"  Rohdaten: {len(df):,} Zeilen")

    # Problem: Der Datensatz enthält neben Ländern auch Aggregate, z.B.
    # "World" (OWID_WRL) oder "High-income countries" (OWID_HIC).
    # Würde man die behalten, wären Fälle mehrfach gezählt.
    # Lösung: Echte Länder haben einen ISO-Code aus genau 3 Großbuchstaben
    # (DEU, USA). Aggregate mit "OWID_" fallen so automatisch raus.
    real_countries = df['iso_code'].str.match(r'^[A-Z]{3}$', na=False)
    excluded = df[~real_countries]['location'].unique()
    print(f"  Ausgeschlossen: {sorted(excluded)}")
    df = df[real_countries].copy()
    print(f"  Nach Filter: {len(df):,} Zeilen, {df['location'].nunique()} Länder")

    df = df.sort_values(['location', 'date']).reset_index(drop=True)

    # Problem: Länder melden manchmal negative Tageswerte, wenn sie frühere
    # Zahlen nach unten korrigieren. Ein negativer Balken ergibt im Diagramm
    # keinen Sinn. Lösung: zählen (zur Kontrolle) und auf 0 setzen.
    print("  Negative Tagswerte:")
    for col in FLOW_COLS:
        n_neg = (df[col] < 0).sum()
        if n_neg > 0:
            print(f"    {col}: {n_neg} Zeilen → werden auf 0 gesetzt")
        df[col] = df[col].fillna(0).clip(lower=0)

    # Problem: Viele Länder melden nicht täglich (z.B. Deutschland 2023 oft nur
    # 1x pro Woche). Gesamtzahlen können aber nicht sinken.
    # Lösung: Forward Fill – letzten bekannten Wert weiterziehen, pro Land getrennt.
    for col in CUMUL_COLS:
        df[col] = df.groupby('location')[col].ffill().fillna(0)

    # Problem: Impfquoten wurden anfangs gar nicht gemeldet (z.B. DE Jan 2021 leer).
    # Lösung: gleiche Logik – Quote kann nie sinken, also Forward Fill.
    for col in VAX_COLS:
        df[col] = df.groupby('location')[col].ffill().fillna(0)

    # Problem: BIP und Medianalter sind feste Länderwerte, stehen aber nur in
    # einzelnen Zeilen (Rest leer). Lösung: auf alle Zeilen des Landes füllen.
    for col in ['gdp_per_capita', 'median_age']:
        df[col] = df.groupby('location')[col].ffill().bfill()

    return df


def create_database(df: pd.DataFrame) -> None:
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = duckdb.connect(DB_PATH)
    con.execute("CREATE TABLE covid AS SELECT * FROM df")
    row_count = con.execute("SELECT COUNT(*) FROM covid").fetchone()[0]
    con.close()
    print(f"  DuckDB: {DB_PATH}")
    print(f"  Datensätze: {row_count:,}")


if __name__ == '__main__':
    print("=== Datenaufbereitung ===")
    df = load_and_clean()
    print("=== Lade in DuckDB ===")
    create_database(df)
    print("=== Fertig! ===")
