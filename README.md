# Globale COVID-19 Datenanalyse – Interaktives Dashboard

Ein interaktives Dashboard zur Aufbereitung und Visualisierung globaler COVID-19-Daten
aus dem [Our World in Data](https://github.com/owid/covid-19-data)-Datensatz.
Schwerpunkt: **Zeitreihenanalyse** und **geographische Visualisierung**.

Entstanden im Modul *Datenaufbereitung und Verarbeitung* (THWS).

---

## Idee & Ziel

Der OWID-Rohdatensatz umfasst **rund 430.000 Zeilen aus 237 Ländern** über viereinhalb
Jahre – umfassend, aber unsauber und unübersichtlich. Ziel des Projekts ist eine vollständige
Pipeline **vom Rohdaten-CSV bis zum interaktiven Dashboard**:

1. Daten automatisch bereinigen und in einer Datenbank strukturieren
2. Zeitreihen und eine geographische Weltkarte erstellen
3. Alles in einem Dashboard bündeln, das ohne Programmierkenntnisse bedienbar ist

---

## Funktionen

- **Analysefragen statt Feldnamen** – die Steuerung erfolgt über Fragestellungen
  (z. B. „Welche Länder waren am stärksten betroffen?")
- **Automatische Kurzantwort** zu jeder Frage, bezogen auf die ausgewählten Länder
- **Kennzahlen & Key Insights** (Fälle, Tode, Fallsterblichkeit, Trend der letzten 30 Tage …)
- **Zeitreihen**: globale Entwicklung, Länder- und Kontinentvergleich,
  Log-Skala und einblendbare Pandemie-Ereignisse (WHO, Impfstart, Delta, Omicron)
- **Geographische Weltkarte** (Choropleth) mit Datum-Slider zur Verfolgung der Ausbreitung
- **Impfkampagne** im Ländervergleich
- **Prognose & Backtesting (Bonus)** – Walk-Forward-Backtesting mit Holt-Winters-Modell

---

## Technologie-Stack

| Bereich | Werkzeug |
|---|---|
| Datenaufbereitung | **pandas** |
| Datenhaltung & Abfragen | **DuckDB** (SQL, in-process) |
| Visualisierung | **Plotly** |
| Dashboard | **Streamlit** |
| Prognose | **statsmodels** (Holt-Winters) |

---

## Projektstruktur

```
covid_dashboard/
├── app.py             # Streamlit-Dashboard (Hauptdatei)
├── data_prep.py       # Datenbereinigung + Aufbau der DuckDB-Datenbank
├── queries.py         # SQL-Abfragen gegen DuckDB
├── requirements.txt   # Python-Abhängigkeiten
└── README.md
```

> Hinweis: `covid.duckdb` wird von `data_prep.py` erzeugt und ist daher **nicht** im
> Repository enthalten. Auch die große Rohdaten-CSV ist ausgeschlossen (siehe unten).

---

## Installation & Start

### 1. Repository klonen
```bash
git clone https://github.com/<DEIN-NUTZERNAME>/covid-dashboard.git
cd covid-dashboard
```

### 2. Abhängigkeiten installieren
```bash
pip install -r requirements.txt
```

### 3. Datensatz herunterladen
Die Rohdaten-CSV (~94 MB) ist aus Größengründen nicht im Repo enthalten.
Lade die Datei `owid-covid-data.csv` von Our World in Data herunter:

- Quelle: https://github.com/owid/covid-19-data/tree/master/public/data

Lege die Datei anschließend **direkt in den Projektordner** (neben `app.py`).

### 4. Datenbank aufbauen
```bash
python data_prep.py
```
Dies bereinigt die Daten und erzeugt `covid.duckdb`.

### 5. Dashboard starten
```bash
streamlit run app.py
```
Das Dashboard öffnet sich automatisch im Browser unter `http://localhost:8501`.

---

## Schritte der Datenaufbereitung

Die Bereinigung in `data_prep.py` umfasst:

1. **Spaltenauswahl** – von 67 auf 21 relevante Spalten reduziert
2. **Länderfilter** – Aggregate wie „World" oder „High-income countries" werden über den
   ISO-3-Code (genau drei Großbuchstaben) entfernt → von 429.000 auf 395.000 Zeilen
3. **Negative Tageswerte** (Meldekorrekturen) werden auf 0 gesetzt
4. **Forward Fill** – Lücken bei kumulierten Werten und Impfquoten werden pro Land
   mit dem letzten bekannten Wert gefüllt
5. **Statische Werte** (BIP, Medianalter) werden pro Land vervollständigt

---

## Hinweise & Grenzen

- Die Daten enthalten **Meldeverzögerungen** (besonders an Wochenenden) und unterschiedliche
  Teststrategien je Land – globale Vergleiche sind daher mit Vorsicht zu interpretieren.
- Krankenhaus- und Testdaten sind nur für wenige Länder verfügbar und wurden bewusst
  ausgeklammert, um keine verzerrte „globale" Aussage zu erzeugen.
- Die **Prognose** ist als ehrlicher Bonus gedacht: Klassische Zeitreihenmodelle funktionieren
  in ruhigen Phasen, versagen aber an Wellen-Wendepunkten – diese werden durch externe
  Faktoren (Varianten, Maßnahmen) ausgelöst, die nicht in den historischen Daten stehen.

---

## Datenquelle

Our World in Data – COVID-19 Dataset
<https://github.com/owid/covid-19-data> (CC BY 4.0)
