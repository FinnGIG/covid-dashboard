# Datenaufbereitung und Visualisierung globaler COVID-19-Daten, Alin Finn [6624015]

Modul: Datenaufbereitung und Verarbeitung · THWS Würzburg

Dashboard lokal starten: `streamlit run app.py` (siehe Abschnitt Installation)

## Projektbeschreibung

Dieses Projekt bereitet den globalen COVID-19-Datensatz von Our World in Data auf und
visualisiert ihn in einem interaktiven Dashboard. Ziel ist es, die Rohdaten systematisch zu
verstehen, nach den Dimensionen der Datenqualität zu prüfen, Auffälligkeiten (aggregierte
Einträge, Meldelücken, fehlende Werte) zu dokumentieren und die bereinigten Daten für die
Zeitreihenanalyse und die geographische Visualisierung aufzubereiten. Die Ergebnisse werden in
einem interaktiven Streamlit-Dashboard dargestellt und in einer DuckDB-Datenbank gespeichert.

Technologien: Python · Pandas · DuckDB · Plotly · Streamlit · statsmodels

## Datensatz

Name: COVID-19 Dataset (Our World in Data)
Quelle: https://github.com/owid/covid-19-data
Zeitraum: 01. Januar 2020 – 14. August 2024
Umfang: 429.435 Zeilen · 67 Spalten · 94 MB

Hinweis: Die CSV-Datei ist mit rund 94 MB zu groß für GitHub (das Limit liegt bei 100 MB, ab
50 MB gibt es Warnungen) und ist deshalb nicht im Repository enthalten. Sie wird wie im Abschnitt
Installation beschrieben von Our World in Data heruntergeladen und in den Projektordner gelegt.

### Spalten

Aus den 67 Spalten des Rohdatensatzes werden 21 für die Analyse relevante Spalten verwendet:

| Spalte | Typ | Beschreibung |
|---|---|---|
| iso_code | Nominal | ISO-3-Ländercode (z. B. DEU, USA). Aggregate beginnen mit `OWID_`. |
| continent | Nominal | Kontinent. Leer bei aggregierten Einträgen. |
| location | Nominal | Name des Landes bzw. der Region. |
| date | Datum | Meldedatum. |
| new_cases / new_cases_smoothed | Numerisch | Neue Fälle pro Tag bzw. als 7-Tage-Schnitt. |
| new_deaths / new_deaths_smoothed | Numerisch | Neue Todesfälle pro Tag bzw. als 7-Tage-Schnitt. |
| total_cases / total_deaths | Numerisch | Kumulierte Fälle bzw. Todesfälle. |
| total_cases_per_million / total_deaths_per_million | Numerisch | Kumulierte Werte pro Million Einwohner (für Vergleiche). |
| new_vaccinations_smoothed | Numerisch | Neue Impfungen pro Tag (7-Tage-Schnitt). |
| people_vaccinated_per_hundred | Numerisch | Anteil mindestens einmal Geimpfter in Prozent. |
| people_fully_vaccinated_per_hundred | Numerisch | Anteil vollständig Geimpfter in Prozent. |
| population | Numerisch | Einwohnerzahl. |
| gdp_per_capita | Numerisch | Bruttoinlandsprodukt pro Kopf. |
| median_age | Numerisch | Medianalter der Bevölkerung. |
| icu_patients_per_million | Numerisch | Intensivpatienten pro Million (nur wenige Länder). |
| hosp_patients_per_million | Numerisch | Krankenhauspatienten pro Million (nur wenige Länder). |
| weekly_hosp_admissions_per_million | Numerisch | Wöchentliche Krankenhausaufnahmen pro Million. |

## 1. Daten laden

```python
import pandas as pd
import duckdb

# Nur die 21 relevanten Spalten einlesen statt aller 67
df = pd.read_csv(
    "owid-covid-data.csv",
    parse_dates=["date"],   # date direkt als Datum einlesen (für .dt-Operationen)
    usecols=KEEP_COLS,      # nur benötigte Spalten laden -> schneller, weniger Speicher
)
```

Ausgabe:

```
Rohdaten: 429.435 Zeilen, 21 Spalten
Zeitraum: 2020-01-01 - 2024-08-14
Locations gesamt: 255
```

## 2. Erster Blick und Datenqualität

Der Datensatz wird nach den klassischen Dimensionen der Datenqualität geprüft.

### Vollständigkeit – Sind alle Werte vorhanden?

```python
print(df.isnull().sum())
# isnull() liefert True für jeden fehlenden Wert, .sum() zählt sie je Spalte
```

Ausgabe (Auszug):

```
new_cases                                19.276   ( 4%)
total_cases                              17.631   ( 4%)
new_deaths                               18.827   ( 4%)
people_fully_vaccinated_per_hundred     351.374   (82%)
icu_patients_per_million                390.319   (91%)
gdp_per_capita                          101.143   (24%)
```

Auffälligkeit: Fall- und Todeszahlen sind fast vollständig (rund 4 % fehlend), Impf- und
Krankenhausdaten dagegen sehr lückenhaft (82 % bzw. 91 %). Die Krankenhausdaten werden deshalb
nicht im Hauptdashboard verwendet, da sie fast nur für wohlhabende Länder vorliegen und sonst
eine verzerrte „globale" Aussage entstünde.

### Eindeutigkeit – Gibt es Duplikate?

```python
print(f"Duplikate: {df.duplicated().sum():,}")
```

Ausgabe:

```
Duplikate: 0
```

### Validität – Entsprechen die Werte den erlaubten Formaten?

Ein gültiger Ländercode besteht laut ISO 3166 aus genau drei Großbuchstaben. Aggregierte
Einträge von Our World in Data verletzen dieses Format:

```python
ungueltige = df[~df["iso_code"].str.match(r"^[A-Z]{3}$", na=False)]
# ^[A-Z]{3}$ = genau drei Großbuchstaben
# ~ = alle Einträge, die NICHT diesem Muster entsprechen
print(sorted(ungueltige["location"].unique()))
```

Ausgabe:

```
['Africa', 'Asia', 'England', 'Europe', 'European Union (27)',
 'High-income countries', 'Kosovo', 'Low-income countries',
 'Lower-middle-income countries', 'North America', 'Northern Cyprus',
 'Northern Ireland', 'Oceania', 'Scotland', 'South America',
 'Upper-middle-income countries', 'Wales', 'World']
```

Herausforderung: Diese 18 Einträge sind keine Länder, sondern Summen (z. B. „World" oder
„High-income countries"). Würde man sie behalten, würden Fälle mehrfach gezählt – einmal beim
Land, einmal in der Kontinent-Summe, einmal in „World".

### Richtigkeit – Sind die Werte plausibel?

Tageswerte (neue Fälle/Tode) können durch nachträgliche Korrekturen negativ werden. In der
verwendeten Datensatzversion hat Our World in Data diese bereits bereinigt – der Code fängt sie
dennoch als Absicherung ab und setzt sie auf 0.

### Konsistenz – Stimmen die Werte überein?

```python
print(df["continent"].value_counts(dropna=False))
```

Ausgabe:

```
Africa           95.419
Europe           91.031
Asia             84.199
North America    68.638
Oceania          40.183
NaN              26.525   <- aggregierte Einträge ohne Kontinent
South America    23.440
```

Sechs gültige Kontinente. Die 26.525 Zeilen ohne Kontinent entsprechen genau den aggregierten
Einträgen aus dem Validitätscheck.

### Aktualität – Wie aktuell sind die Daten?

Zeitraum: 01.01.2020 – 14.08.2024 (rund viereinhalb Jahre, alle Pandemiephasen enthalten).

## 3. Datenbereinigung

Die Bereinigung erfolgt in `data_prep.py`.

### Aggregate entfernen

```python
real_countries = df["iso_code"].str.match(r"^[A-Z]{3}$", na=False)
df = df[real_countries].copy()
```

Ausgabe:

```
Nach Filter: 395.311 Zeilen, 237 Länder
```

### Negative Tageswerte abfangen

```python
for col in FLOW_COLS:   # new_cases, new_deaths, new_cases_smoothed, ...
    df[col] = df[col].fillna(0).clip(lower=0)
    # fillna(0)      -> fehlende Tageswerte als 0 behandeln
    # clip(lower=0)  -> negative Korrekturen auf 0 setzen
```

### Lücken bei kumulierten Werten füllen

Kumulierte Werte (Gesamtfälle, Gesamttote) können logisch nicht sinken. Meldelücken (z. B. am
Wochenende) werden mit dem letzten bekannten Wert je Land aufgefüllt.

```python
for col in CUMUL_COLS:
    df[col] = df.groupby("location")[col].ffill().fillna(0)
    # groupby("location") -> pro Land getrennt, damit keine Werte überspringen
    # ffill()             -> letzten bekannten Wert weiterziehen (Forward Fill)
```

Beispiel Deutschland (kumulierte Fälle bleiben in den Lücken stabil):

```
date        new_cases   total_cases
2023-06-04      2.767    38.430.723
2023-06-05          0    38.430.723   <- aufgefüllt
2023-06-11      2.392    38.433.115
```

### Impfquoten und statische Werte füllen

```python
for col in VAX_COLS:            # Impfquoten – steigen nur, sinken nie
    df[col] = df.groupby("location")[col].ffill().fillna(0)

for col in ["gdp_per_capita", "median_age"]:   # feste Länderwerte
    df[col] = df.groupby("location")[col].ffill().bfill()
```

## 4. Datenhaltung in DuckDB

Der bereinigte DataFrame wird in eine DuckDB-Datenbank geschrieben. Alle Abfragen des Dashboards
laufen anschließend über SQL (`queries.py`).

```python
con = duckdb.connect("covid.duckdb")
con.execute("CREATE TABLE covid AS SELECT * FROM df")
# Erstellt die Tabelle direkt aus dem Python-DataFrame
```

Ausgabe:

```
DuckDB: covid.duckdb
Datensätze: 395.311
```

Beispielabfrage – globale Zeitreihe (alle Länder pro Tag summiert):

```sql
SELECT date, SUM(new_cases_smoothed) AS value
FROM covid
WHERE date BETWEEN '2020-01-01' AND '2024-08-14'
GROUP BY date
ORDER BY date
```

## 5. Dashboard

Das Streamlit-Dashboard (`app.py`) gliedert sich in:

- Filterleiste: Steuerung über Analysefragen statt technischer Feldnamen, Länderauswahl, Zeitraum
- Kennzahlen: Fälle, Todesfälle, Fallsterblichkeit, Trend der letzten 30 Tage, globaler Peak
- Zeitreihen: globale Entwicklung, Länder- und Kontinentvergleich, Log-Skala, Ereignis-Marker
  (WHO-Pandemieerklärung, Impfstart, Delta, Omicron)
- Weltkarte: Choropleth-Karte mit Datum-Slider zur Verfolgung der globalen Ausbreitung
- Impfkampagne: Impffortschritt im Ländervergleich
- Prognose und Backtesting (Bonus): Walk-Forward-Backtesting mit Holt-Winters-Modell

## Installation und Start

```bash
# 1. Repository klonen
git clone https://github.com/FinnGIG/covid-dashboard.git
cd covid-dashboard

# 2. Abhängigkeiten installieren
pip install -r requirements.txt

# 3. Datensatz herunterladen (~94 MB, nicht im Repo enthalten)
#    von https://github.com/owid/covid-19-data/tree/master/public/data
#    die Datei "owid-covid-data.csv" in den Projektordner legen

# 4. Datenbank aufbauen (erzeugt covid.duckdb)
python data_prep.py

# 5. Dashboard starten
streamlit run app.py
```

Das Dashboard öffnet sich anschließend im Browser unter http://localhost:8501.

## Dateien

```
covid_dashboard/
├── app.py             Streamlit-Dashboard
├── data_prep.py       Datenbereinigung und Aufbau der DuckDB-Datenbank
├── queries.py         SQL-Abfragen gegen DuckDB
├── requirements.txt   Python-Abhängigkeiten
└── README.md
```

Hinweis: Die Rohdaten-CSV (~94 MB) und die erzeugte Datenbank `covid.duckdb` sind nicht im
Repository enthalten. Die CSV wird wie oben beschrieben heruntergeladen, die Datenbank von
`data_prep.py` erzeugt.

## Datenquelle

Our World in Data – COVID-19 Dataset · https://github.com/owid/covid-19-data · Lizenz CC BY 4.0
