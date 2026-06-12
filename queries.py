import duckdb
import pandas as pd
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'covid.duckdb')


def _con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(DB_PATH, read_only=True)


def get_countries() -> list[str]:
    con = _con()
    rows = con.execute("SELECT DISTINCT location FROM covid ORDER BY location").fetchall()
    con.close()
    return [r[0] for r in rows]


def get_date_range() -> tuple:
    con = _con()
    row = con.execute("SELECT MIN(date), MAX(date) FROM covid").fetchone()
    con.close()
    return row[0], row[1]


def global_timeline(metric: str, start: str, end: str) -> pd.DataFrame:
    # Alle Länder pro Tag summieren
    con = _con()
    df = con.execute(f"""
        SELECT date, SUM({metric}) AS value
        FROM covid
        WHERE date BETWEEN '{start}' AND '{end}'
        GROUP BY date
        ORDER BY date
    """).df()
    con.close()
    return df


def continent_timeline(metric: str, start: str, end: str) -> pd.DataFrame:
    # Länder pro Kontinent und Tag summieren
    con = _con()
    df = con.execute(f"""
        SELECT date, continent, SUM({metric}) AS value
        FROM covid
        WHERE date BETWEEN '{start}' AND '{end}'
          AND continent IS NOT NULL
        GROUP BY date, continent
        ORDER BY date, continent
    """).df()
    con.close()
    return df


def country_timeline(countries: list, metric: str, start: str, end: str) -> pd.DataFrame:
    # Zeitreihe für ausgewählte Länder
    placeholders = ', '.join(f"'{c}'" for c in countries)
    con = _con()
    df = con.execute(f"""
        SELECT date, location, {metric} AS value
        FROM covid
        WHERE location IN ({placeholders})
          AND date BETWEEN '{start}' AND '{end}'
        ORDER BY location, date
    """).df()
    con.close()
    return df


def latest_snapshot(metric: str) -> pd.DataFrame:
    # Letzter Wert je Land (für KPI-Karten)
    con = _con()
    df = con.execute(f"""
        SELECT iso_code, location, continent, {metric} AS value
        FROM covid
        WHERE {metric} > 0
        QUALIFY ROW_NUMBER() OVER (PARTITION BY location ORDER BY date DESC) = 1
    """).df()
    con.close()
    return df


def snapshot_at_date(metric: str, date: str) -> pd.DataFrame:
    # Letzter bekannter Wert je Land bis zum gewählten Datum
    con = _con()
    df = con.execute(f"""
        SELECT iso_code, location, continent, {metric} AS value
        FROM covid
        WHERE date <= '{date}'
          AND {metric} > 0
        QUALIFY ROW_NUMBER() OVER (PARTITION BY location ORDER BY date DESC) = 1
    """).df()
    con.close()
    return df


def hospital_countries() -> list[str]:
    # Nur Länder die überhaupt ICU-Daten gemeldet haben
    con = _con()
    rows = con.execute("""
        SELECT DISTINCT location
        FROM covid
        WHERE icu_patients_per_million > 0
        ORDER BY location
    """).fetchall()
    con.close()
    return [r[0] for r in rows]


def hospital_timeline(countries: list, metric: str, start: str, end: str) -> pd.DataFrame:
    # Krankenhausdaten für ausgewählte Länder
    placeholders = ', '.join(f"'{c}'" for c in countries)
    con = _con()
    df = con.execute(f"""
        SELECT date, location, {metric} AS value
        FROM covid
        WHERE location IN ({placeholders})
          AND date BETWEEN '{start}' AND '{end}'
          AND {metric} IS NOT NULL
          AND {metric} > 0
        ORDER BY location, date
    """).df()
    con.close()
    return df


def correlation_data() -> pd.DataFrame:
    # BIP, Medianalter und COVID-Kennzahlen je Land für Streudiagramme
    con = _con()
    df = con.execute("""
        SELECT
            location,
            continent,
            MAX(gdp_per_capita)                      AS gdp_per_capita,
            MAX(median_age)                          AS median_age,
            MAX(total_deaths_per_million)            AS deaths_per_million,
            MAX(people_fully_vaccinated_per_hundred) AS vax_pct
        FROM covid
        GROUP BY location, continent
        HAVING gdp_per_capita IS NOT NULL
           AND deaths_per_million > 0
    """).df()
    con.close()
    return df


def kpi_totals() -> dict:
    con = _con()
    row = con.execute("""
        SELECT
            SUM(total_cases)  FILTER (WHERE ROW_NUMBER() OVER (PARTITION BY location ORDER BY date DESC) = 1) AS cases,
            SUM(total_deaths) FILTER (WHERE ROW_NUMBER() OVER (PARTITION BY location ORDER BY date DESC) = 1) AS deaths,
            COUNT(DISTINCT location) AS countries
        FROM covid
    """).fetchone()
    con.close()
    return {'cases': row[0] or 0, 'deaths': row[1] or 0, 'countries': row[2] or 0}
