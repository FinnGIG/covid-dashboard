import streamlit as st
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go
import numpy as np
import datetime
import pandas as pd
import queries

# Modernes, sauberes Plotly-Template (+ deutsches Zahlenformat)
pio.templates["german"] = pio.templates["plotly_white"]
_tpl = pio.templates["german"]
_tpl.layout.separators   = ",."
_tpl.layout.font         = dict(family="Inter, -apple-system, Segoe UI, sans-serif",
                                size=13, color="#475569")
_tpl.layout.paper_bgcolor = "rgba(0,0,0,0)"
_tpl.layout.plot_bgcolor  = "rgba(0,0,0,0)"
_tpl.layout.xaxis = dict(showgrid=False, zeroline=False, showline=False, ticks="",
                         tickfont=dict(color="#94a3b8", size=12))
_tpl.layout.yaxis = dict(showgrid=True, gridcolor="#eef2f7", gridwidth=1,
                         zeroline=False, showline=False, ticks="",
                         tickfont=dict(color="#94a3b8", size=12))
_tpl.layout.legend = dict(font=dict(size=12, color="#475569"))
pio.templates.default = "german"

def de_format(fig):
    """Verhindert K/M im Hover-Tooltip – zeigt volle Zahl in deutschem Format"""
    fig.update_yaxes(hoverformat=",.1f")
    return fig

def fmt_de(n: float, decimals: int = 0) -> str:
    """Deutsches Zahlenformat: 9.581,47"""
    s = f"{n:,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

st.set_page_config(
    page_title="COVID-19 Dashboard",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* Moderne Schrift für die ganze App */
html, body, [class*="css"], .stApp, button, input, select, textarea {
    font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif !important;
}

/* Leichter Seitenhintergrund, damit weiße Karten hervortreten */
.stApp { background-color: #f6f8fc; }

[data-testid="stSidebar"]                { display: none; }
[data-testid="stSidebarCollapsedControl"]{ display: none; }

/* Vollbild-Button rot */
[data-testid="stPlotlyChart"] button[title="View fullscreen"] {
    visibility: visible !important; opacity: 1 !important;
    background-color: #e63946 !important; color: white !important;
    border-radius: 6px !important; width: 32px !important; height: 32px !important;
}

/* Multiselect-Tags blau */
span[data-baseweb="tag"] { background-color: #1d4ed8 !important; border-radius: 6px !important; }

/* Tab-Unterstrich blau */
[data-baseweb="tab-highlight"] { background-color: #1d4ed8 !important; }
[data-baseweb="tab"][aria-selected="true"] { color: #1d4ed8 !important; }

/* Etwas mehr Platz oben damit Titel nicht abgeschnitten wird */
.block-container { padding-top: 2.5rem !important; }

/* Karten/Boxen: weich gerundet, dezenter Schatten (SaaS-Look) */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #ffffff;
    border: 1px solid #eef2f7 !important;
    border-radius: 16px !important;
    box-shadow: 0 1px 2px rgba(16,24,40,0.04), 0 6px 16px rgba(16,24,40,0.05);
}

/* Überschriften moderner: kräftig, dunkles Slate */
h1, h2, h3, h4 {
    font-family: 'Inter', sans-serif !important;
    color: #1e293b !important;
    font-weight: 700 !important;
    letter-spacing: -0.01em;
}
[data-testid="stHeading"] h3, .stSubheader { font-size: 1.05rem !important; }

/* Hover-Effekt für KPI-Karten */
.metric-card {
    transition: box-shadow 0.2s ease, transform 0.2s ease;
    cursor: default;
}
.metric-card:hover {
    box-shadow: 0 8px 22px rgba(16,24,40,0.12) !important;
    transform: translateY(-2px);
}

/* Eingabefelder dezent abrunden */
[data-baseweb="select"] > div, [data-testid="stDateInput"] input {
    border-radius: 10px !important;
}

/* Checkboxen blau */
[data-testid="stCheckbox"] [data-baseweb="checkbox"] > div:first-child {
    background-color: #1d4ed8 !important;
    border-color:     #1d4ed8 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Konstanten ────────────────────────────────────────────────────────────────

# Konsistente Länderfarben über alle Tabs (Punkt 3)
COUNTRY_COLORS = {
    "Germany":        "#1d4ed8",
    "United States":  "#16a34a",
    "India":          "#ea580c",
    "Brazil":         "#9333ea",
    "United Kingdom": "#0891b2",
    "France":         "#ca8a04",
    "Italy":          "#dc2626",
    "Spain":          "#d97706",
    "China":          "#be123c",
    "Russia":         "#7c3aed",
    "Japan":          "#0d9488",
    "Australia":      "#a16207",
}

def metric_card(label: str, value: str, delta: str,
                delta_color: str = "#6b7280",
                accent: str = "#2563eb",
                small: bool = False) -> str:
    """Weiße KPI-Karte mit farbigem Akzentbalken oben"""
    val_size  = "1.5rem" if small else "2rem"
    lbl_size  = "0.75rem" if small else "0.82rem"
    pad       = "10px 14px" if small else "14px 18px"
    return f"""
    <div class="metric-card" style="background:white; border:1px solid #e5e7eb;
                border-top:3px solid {accent}; border-radius:8px;
                padding:{pad}; width:100%; box-sizing:border-box;
                box-shadow:0 1px 3px rgba(0,0,0,0.04);">
        <p style="color:#6b7280; font-size:{lbl_size}; font-weight:600;
                  text-transform:uppercase; letter-spacing:0.04em; margin:0 0 4px 0;">{label}</p>
        <p style="color:#111827; font-size:{val_size}; font-weight:800;
                  margin:0 0 5px 0; line-height:1.1;">{value}</p>
        <p style="color:{delta_color}; font-size:0.78rem; margin:0;">{delta}</p>
    </div>"""

def color_map(countries: list) -> dict:
    return {c: COUNTRY_COLORS[c] for c in countries if c in COUNTRY_COLORS}

# Konsistente Kontinentfarben für Streudiagramme
CONTINENT_COLORS = {
    "Europe":        "#1d4ed8",   # Blau
    "North America": "#16a34a",   # Grün
    "Asia":          "#ea580c",   # Orange
    "Africa":        "#ca8a04",   # Gold
    "South America": "#9333ea",   # Lila
    "Oceania":       "#0891b2",   # Türkis
}

def add_event_lines(fig, events: dict, start: str, end: str) -> None:
    """Ereignislinien als add_shape + add_annotation (zuverlässiger als add_vline)"""
    for name, date in events.items():
        if start <= date <= end:
            fig.add_shape(
                type="line", x0=date, x1=date, y0=0, y1=1,
                yref="paper", line=dict(dash="dash", color="#9ca3af", width=1),
            )
            fig.add_annotation(
                x=date, y=0.97, yref="paper", text=name,
                showarrow=False, xanchor="left", yanchor="top",
                font=dict(size=10, color="#6b7280"),
                bgcolor="rgba(255,255,255,0.75)",
            )

# Schlüsselereignisse der Pandemie (Punkt 6)
EVENTS = {
    "WHO Pandemieerklärung": "2020-03-11",
    "Impfstart (UK)":        "2020-12-08",
    "Delta-Welle":           "2021-05-01",
    "Omicron":               "2021-11-24",
}

# Fragestellungen → (Datenbankfeld, Achsenbeschriftung)
QUESTIONS = {
    "Wie schnell breitet sich COVID aus?":         ("new_cases_smoothed",                  "Neue Fälle (7-Tage-Schnitt)"),
    "Wie viele Todesfälle gab es?":                ("new_deaths_smoothed",                 "Neue Todesfälle (7-Tage-Schnitt)"),
    "Welche Länder waren am stärksten betroffen?": ("total_cases_per_million",             "Gesamtfälle pro Million"),
    "Wie hoch war die Sterblichkeit?":             ("total_deaths_per_million",            "Gesamttote pro Million"),
    "Wie schnell wurde geimpft?":                  ("new_vaccinations_smoothed",           "Neue Impfungen (7-Tage-Schnitt)"),
}

COLOR_PRIMARY = "#1d4ed8"
COLOR_SEQ     = ["#1d4ed8", "#2563eb", "#3b82f6", "#60a5fa", "#06b6d4", "#0891b2"]

# ── Cache-Funktionen ──────────────────────────────────────────────────────────
@st.cache_data
def cached_countries():
    return queries.get_countries()

@st.cache_data
def cached_date_range():
    return queries.get_date_range()

@st.cache_data
def cached_global(metric, start, end):
    return queries.global_timeline(metric, start, end)

@st.cache_data
def cached_countries_timeline(countries_tuple, metric, start, end):
    return queries.country_timeline(list(countries_tuple), metric, start, end)

@st.cache_data
def cached_snapshot(metric):
    return queries.latest_snapshot(metric)

@st.cache_data
def cached_snapshot_at_date(metric, date):
    return queries.snapshot_at_date(metric, date)

@st.cache_data
def cached_continent(metric, start, end):
    return queries.continent_timeline(metric, start, end)

@st.cache_data
def cached_correlation():
    return queries.correlation_data()

@st.cache_data
def cached_hospital_countries():
    return queries.hospital_countries()

@st.cache_data
def cached_hospital_timeline(countries_tuple, metric, start, end):
    return queries.hospital_timeline(list(countries_tuple), metric, start, end)

# ── Titel ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex; align-items:center; gap:20px;
            background:linear-gradient(to right, #eff6ff, #f5f8ff);
            border-left:4px solid #1d4ed8; border-radius:0 8px 8px 0;
            padding:12px 20px; margin-bottom:12px;">
    <div>
        <div style="color:#1d4ed8; font-size:1.55rem; font-weight:800; margin:0 0 2px 0;
                    line-height:1.2;">Globale COVID-19 Datenanalyse</div>
        <div style="color:#9ca3af; font-size:0.78rem; margin:0;">
            430.000 Datenpunkte &nbsp;·&nbsp; 237 Länder &nbsp;·&nbsp;
            Jan 2020 – Aug 2024 &nbsp;·&nbsp; Our World in Data
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Filter-Leiste ─────────────────────────────────────────────────────────────
all_countries      = cached_countries()
DEFAULT            = ["Germany", "United States", "India", "Brazil", "United Kingdom"]
min_date, max_date = cached_date_range()

with st.container(border=True):
    f1, f2, f3 = st.columns([1.2, 2.5, 1.5])
    with f1:
        question = st.selectbox(
            "Analysefrage",
            list(QUESTIONS.keys()),
            help="Wähle eine Fragestellung – die Visualisierungen passen sich automatisch an.",
        )
        metric, metric_label = QUESTIONS[question]
    with f2:
        selected = st.multiselect(
            "Länder vergleichen",
            all_countries,
            default=[c for c in DEFAULT if c in all_countries],
            help="Mehrere Länder für den direkten Vergleich auswählen.",
        )
    with f3:
        date_range = st.date_input(
            "Zeitraum",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            format="DD.MM.YYYY",
        )

start = str(date_range[0]) if len(date_range) > 0 else str(min_date)
end   = str(date_range[1]) if len(date_range) > 1 else str(max_date)

start_fmt = datetime.datetime.strptime(start, "%Y-%m-%d").strftime("%d.%m.%Y")
end_fmt   = datetime.datetime.strptime(end,   "%Y-%m-%d").strftime("%d.%m.%Y")

if selected:
    preview = ", ".join(selected[:4]) + (f" +{len(selected)-4} weitere" if len(selected) > 4 else "")
    st.markdown(f"""
    <div style="background:#eff6ff; border:1px solid #bfdbfe; border-radius:8px;
                padding:10px 16px; font-size:0.875rem; color:#1e40af; margin-bottom:4px;">
        <strong>Aktueller Vergleich:</strong> {preview}
        &nbsp;·&nbsp; {start_fmt} – {end_fmt}
        &nbsp;·&nbsp; {question}
    </div>
    """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
#  BERECHNUNGEN (vor dem Layout, damit die Werte in den Spalten verfügbar sind)
# ════════════════════════════════════════════════════════════════════════════
snap_cases  = cached_snapshot("total_cases")
snap_deaths = cached_snapshot("total_deaths")
total_cases  = snap_cases["value"].sum()
total_deaths = snap_deaths["value"].sum()
n_countries  = snap_cases["location"].nunique()
cfr          = (total_deaths / total_cases * 100) if total_cases > 0 else 0

# Trend: letzte 30 Tage vs. vorherige 30 Tage
try:
    end_dt  = datetime.datetime.strptime(end, "%Y-%m-%d")
    mid_dt  = end_dt - datetime.timedelta(days=30)
    pre_dt  = end_dt - datetime.timedelta(days=60)
    rc = cached_global("new_cases_smoothed",  mid_dt.strftime("%Y-%m-%d"), end)
    pc = cached_global("new_cases_smoothed",  pre_dt.strftime("%Y-%m-%d"), mid_dt.strftime("%Y-%m-%d"))
    rd = cached_global("new_deaths_smoothed", mid_dt.strftime("%Y-%m-%d"), end)
    pd_ = cached_global("new_deaths_smoothed", pre_dt.strftime("%Y-%m-%d"), mid_dt.strftime("%Y-%m-%d"))
    cases_trend  = (rc["value"].mean()  - pc["value"].mean())  / pc["value"].mean()  * 100 if pc["value"].mean()  > 0 else 0
    deaths_trend = (rd["value"].mean() - pd_["value"].mean()) / pd_["value"].mean() * 100 if pd_["value"].mean() > 0 else 0
except Exception:
    cases_trend  = 0
    deaths_trend = 0

c_arrow = "↓" if cases_trend  < 0 else "↑"
d_arrow = "↓" if deaths_trend < 0 else "↑"
c_color = "#16a34a" if cases_trend  < 0 else "#dc2626"
d_color = "#16a34a" if deaths_trend < 0 else "#dc2626"

global_df = cached_global(metric, start, end)

# Key-Insight-Werte vorberechnen
if not global_df.empty and global_df["value"].max() > 0:
    peak_row  = global_df.loc[global_df["value"].idxmax()]
    peak_val  = peak_row["value"]
    peak_date = pd.to_datetime(peak_row["date"]).strftime("%d.%m.%Y")
    peak_str  = f"{fmt_de(peak_val/1e6, 1)} Mio." if peak_val >= 1e6 else fmt_de(peak_val, 0)
else:
    peak_str, peak_date = "–", ""

snap_dm = cached_snapshot("total_deaths_per_million")
if not snap_dm.empty:
    worst = snap_dm.loc[snap_dm["value"].idxmax()]
    worst_str, worst_loc = fmt_de(worst["value"], 0), worst["location"]
else:
    worst_str, worst_loc = "–", ""

snap_v = cached_snapshot("people_fully_vaccinated_per_hundred")
if not snap_v.empty:
    avg_vax_str = f"{fmt_de(snap_v[snap_v['value'] > 0]['value'].mean(), 1)} %"
else:
    avg_vax_str = "–"

if metric in ("new_cases_smoothed", "new_deaths_smoothed"):
    t = cases_trend if metric == "new_cases_smoothed" else deaths_trend
    t_arrow = "↓" if t < 0 else "↑"
    t_color = "#16a34a" if t < 0 else "#dc2626"
    trend_str, trend_delta = f"{fmt_de(t, 0)} %", f"{t_arrow} vs. vorherige 30 Tage"
else:
    t_color = "#6b7280"
    trend_str, trend_delta = "–", "Nur für Tages-Metriken"

# Kurzantwort – globaler Überblick je Frage (Fallback ohne Länderauswahl)
GLOBAL_ANSWERS = {
    "Wie schnell breitet sich COVID aus?":
        f"Die Ausbreitung verlief in mehreren Wellen. Der globale Höchststand lag bei "
        f"{peak_str} neuen Fällen (7-Tage-Schnitt) am {peak_date}.",
    "Wie viele Todesfälle gab es?":
        f"Weltweit wurden rund {fmt_de(total_deaths/1e6, 2)} Mio. Todesfälle erfasst – "
        f"bei {fmt_de(total_cases/1e6, 0)} Mio. bestätigten Fällen.",
    "Welche Länder waren am stärksten betroffen?":
        f"Pro Million Einwohner war {worst_loc} am stärksten betroffen ({worst_str} Tote/Mio.).",
    "Wie hoch war die Sterblichkeit?":
        f"Die Fallsterblichkeit liegt bei {fmt_de(cfr, 2)} % der bestätigten Fälle.",
    "Wie schnell wurde geimpft?":
        f"Die Impfkampagnen starteten Ende 2020. Im weltweiten Schnitt sind "
        f"{avg_vax_str} der Bevölkerung vollständig geimpft.",
}

# Konfiguration für die länderbezogene Antwort:
# (Datenfeld, "peak"=Höchstwert / "last"=letzter Wert, Nachkommastellen, Einheit, Vergleichssatz)
ANSWER_CFG = {
    "Wie schnell breitet sich COVID aus?":
        ("new_cases_smoothed", "peak", 0, " Fälle/Tag",
         "hatte den höchsten Tagespeak"),
    "Wie viele Todesfälle gab es?":
        ("total_deaths", "last", 0, " Tote",
         "verzeichnete die meisten Todesfälle"),
    "Welche Länder waren am stärksten betroffen?":
        ("total_cases_per_million", "last", 0, " Fälle/Mio.",
         "war pro Million am stärksten betroffen"),
    "Wie hoch war die Sterblichkeit?":
        ("total_deaths_per_million", "last", 0, " Tote/Mio.",
         "hatte die höchste Sterberate pro Million"),
    "Wie schnell wurde geimpft?":
        ("people_fully_vaccinated_per_hundred", "last", 1, " %",
         "erreichte die höchste Impfquote"),
}

def build_country_answer(question, countries, start, end):
    """Baut Vergleichssatz + Einzelwerte je Land für die gewählte Frage."""
    field, agg, dec, unit, phrase = ANSWER_CFG[question]
    df = cached_countries_timeline(tuple(countries), field, start, end)
    if df.empty:
        return None, None
    werte = []
    for c in countries:
        cd = df[df["location"] == c]
        if cd.empty:
            continue
        v = cd["value"].max() if agg == "peak" else cd.sort_values("date")["value"].iloc[-1]
        if v is not None and not pd.isna(v):
            werte.append((c, float(v)))
    if not werte:
        return None, None
    werte.sort(key=lambda x: x[1], reverse=True)
    top_land, top_val = werte[0]
    vergleich = f"Unter deiner Auswahl {phrase} <strong>{top_land}</strong> mit {fmt_de(top_val, dec)}{unit}."
    einzel = " · ".join(f"{c}: {fmt_de(v, dec)}{unit}" for c, v in werte)
    return vergleich, einzel

# Antwort rendern: mit Ländern → Vergleich + Einzelwerte, sonst globaler Überblick
vergleich, einzel = (None, None)
if selected:
    try:
        vergleich, einzel = build_country_answer(question, selected, start, end)
    except Exception:
        vergleich, einzel = None, None

def render_answer_box(haupttext: str, einzeltext: str = "") -> None:
    extra = (f"<div style='color:#3f6212; font-size:0.9rem; margin-top:6px; "
             f"padding-top:6px; border-top:1px solid #bbf7d0;'>{einzeltext}</div>") if einzeltext else ""
    st.markdown(f"""
    <div style="background:linear-gradient(to right,#dcfce7,#f0fdf4);
                border:1px solid #86efac; border-left:6px solid #16a34a;
                border-radius:10px; padding:14px 20px; margin:6px 0 10px 0;
                box-shadow:0 2px 10px rgba(22,163,74,0.12);">
        <div style="color:#15803d; font-size:0.72rem; font-weight:700;
                    text-transform:uppercase; letter-spacing:0.06em; margin-bottom:4px;">
            Kurzantwort auf deine Analysefrage
        </div>
        <div style="color:#14532d; font-size:1.02rem; line-height:1.45;">{haupttext}</div>
        {extra}
    </div>
    """, unsafe_allow_html=True)

if vergleich:
    render_answer_box(vergleich, einzel)
else:
    answer = GLOBAL_ANSWERS.get(question, "")
    if answer:
        render_answer_box(answer)

st.divider()

# ════════════════════════════════════════════════════════════════════════════
#  EINSEITIGES LAYOUT – links Zeitreihen, rechts Kennzahlen + Karte + Impfung
# ════════════════════════════════════════════════════════════════════════════
col_left, col_right = st.columns(2, gap="large")

# ── LINKS: Steuerung + Globale Entwicklung + Länder-/Kontinentvergleich ───────
with col_left:
    with st.container(border=True):
        st.subheader("Globale Entwicklung")
        ctrl1, ctrl2 = st.columns(2)
        with ctrl1:
            use_log_ts = st.checkbox(
                "Log-Skala",
                key="log_ts",
                help="Gilt für Länder- und Kontinentvergleich. Logarithmische Skala zeigt relative "
                     "Wachstumsraten besser bei stark unterschiedlichen Größenordnungen.",
            )
        with ctrl2:
            show_events = st.checkbox(
                "Ereignisse einblenden",
                value=True,
                help="Zeigt wichtige Pandemie-Ereignisse als vertikale Markierungen.",
            )
        fig_global = px.area(
            global_df, x="date", y="value",
            labels={"date": "Datum", "value": metric_label},
            color_discrete_sequence=[COLOR_PRIMARY],
        )
        if show_events:
            add_event_lines(fig_global, EVENTS, start, end)
        fig_global.update_traces(line=dict(width=2.5),
                                 fillcolor="rgba(29,78,216,0.10)")
        fig_global.update_layout(showlegend=False, height=300, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(de_format(fig_global), use_container_width=True)

    with st.container(border=True):
        st.subheader("Ländervergleich")
        if selected:
            country_df = cached_countries_timeline(tuple(selected), metric, start, end)
            fig_c = px.line(
                country_df, x="date", y="value", color="location",
                color_discrete_map=color_map(selected),
                labels={"date": "Datum", "value": metric_label, "location": "Land"},
            )
            if use_log_ts:
                fig_c.update_yaxes(type="log")
            fig_c.update_traces(line=dict(width=2.5))
            fig_c.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0),
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
            st.plotly_chart(de_format(fig_c), use_container_width=True)
        else:
            st.info("Oben mindestens ein Land auswählen.")

    with st.container(border=True):
        st.subheader("Kontinentvergleich")
        cont_df = cached_continent(metric, start, end)
        fig_cont = px.line(
            cont_df, x="date", y="value", color="continent",
            color_discrete_map=CONTINENT_COLORS,
            labels={"date": "Datum", "value": metric_label, "continent": "Kontinent"},
        )
        if use_log_ts:
            fig_cont.update_yaxes(type="log")
        if show_events:
            add_event_lines(fig_cont, EVENTS, start, end)
        fig_cont.update_traces(line=dict(width=2.5))
        fig_cont.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0),
                               legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
        st.plotly_chart(de_format(fig_cont), use_container_width=True)

# ── RECHTS: Kennzahlen + Weltkarte + Impfkampagne ─────────────────────────────
with col_right:
    # Kennzahlen (8 Karten, 4 pro Reihe)
    with st.container(border=True):
        st.markdown("<p style='color:#9ca3af; font-size:0.78rem; margin:0 0 8px 0; font-weight:600; text-transform:uppercase; letter-spacing:0.05em;'>Kennzahlen</p>", unsafe_allow_html=True)
        r1 = st.columns(4)
        with r1[0]: st.markdown(metric_card("Bestätigte Fälle", f"{fmt_de(total_cases/1e6, 0)} Mio.",
            f"{c_arrow} {cases_trend:+.0f}% (30 T.)", c_color, accent="#2563eb", small=True), unsafe_allow_html=True)
        with r1[1]: st.markdown(metric_card("Todesfälle", f"{fmt_de(total_deaths/1e6, 2)} Mio.",
            f"{d_arrow} {deaths_trend:+.0f}% (30 T.)", d_color, accent="#dc2626", small=True), unsafe_allow_html=True)
        with r1[2]: st.markdown(metric_card("Fallsterblichkeit", f"{fmt_de(cfr, 2)} %",
            "Tode / Fälle", accent="#9333ea", small=True), unsafe_allow_html=True)
        with r1[3]: st.markdown(metric_card("Erfasste Länder", str(n_countries),
            "von 237 gesamt", accent="#16a34a", small=True), unsafe_allow_html=True)

        st.write("")
        r2 = st.columns(4)
        with r2[0]: st.markdown(metric_card("Globaler Peak", peak_str, peak_date,
            accent="#f97316", small=True), unsafe_allow_html=True)
        with r2[1]: st.markdown(metric_card("Höchste Tode/Mio.", worst_str, worst_loc,
            accent="#64748b", small=True), unsafe_allow_html=True)
        with r2[2]: st.markdown(metric_card("Ø Impfquote", avg_vax_str, "Vollständig geimpft",
            accent="#0d9488", small=True), unsafe_allow_html=True)
        with r2[3]: st.markdown(metric_card("Trend 30 Tage", trend_str, trend_delta,
            t_color, accent="#d97706", small=True), unsafe_allow_html=True)

    # Weltkarte
    with st.container(border=True):
        st.subheader(f"Weltkarte – {metric_label}")
        map_date = st.slider(
            "Datum wählen",
            min_value=datetime.date(2020, 1, 1),
            max_value=datetime.date(2024, 8, 14),
            value=datetime.date(2024, 8, 14),
            step=datetime.timedelta(days=7),
            format="DD.MM.YYYY",
        )
        use_log = st.checkbox("Log-Skala", value=True, key="map_log",
            help="Macht auch kleinere Länder farblich sichtbar.")

        map_df  = cached_snapshot_at_date(metric, str(map_date)).dropna(subset=["value"])
        max_ref = cached_snapshot(metric)["value"].quantile(0.98)
        map_df  = map_df.copy()
        if use_log:
            map_df["color_val"] = np.log1p(map_df["value"])
            range_c   = (0, np.log1p(max_ref))
            bar_title = f"{metric_label}<br>(Log)"
        else:
            map_df["color_val"] = map_df["value"]
            range_c   = (0, max_ref)
            bar_title = metric_label

        fig_map = px.choropleth(
            map_df,
            locations="iso_code", color="color_val", hover_name="location",
            hover_data={"value": ":,.0f", "continent": True, "color_val": False, "iso_code": False},
            color_continuous_scale="Reds", range_color=range_c,
            labels={"value": metric_label, "continent": "Kontinent", "color_val": ""},
            projection="natural earth",
        )
        fig_map.update_geos(
            showframe=False, projection_type="natural earth",
            lataxis_range=[-90, 90], lonaxis_range=[-180, 180], showlakes=False,
            showcoastlines=True, coastlinecolor="#e2e8f0", coastlinewidth=0.6,
            showland=True, landcolor="#f1f5f9",
            showcountries=True, countrycolor="#ffffff", countrywidth=0.5,
        )
        fig_map.update_layout(height=360, margin=dict(l=0, r=0, t=10, b=0),
            coloraxis_colorbar=dict(title=bar_title, thickness=12,
                                    outlinewidth=0, tickfont=dict(color="#94a3b8")))
        st.plotly_chart(fig_map, use_container_width=True,
                        config={"scrollZoom": True, "doubleClick": "reset", "displayModeBar": True})
        st.caption(f"Scrollen = Zoom · Doppelklick = Reset · Stand: {map_date.strftime('%d.%m.%Y')}")

    # Impfkampagne
    with st.container(border=True):
        st.subheader("Impffortschritt (vollständig geimpft, %)")
        if selected:
            vax_df = cached_countries_timeline(
                tuple(selected), "people_fully_vaccinated_per_hundred", start, end
            )
            if not vax_df.empty:
                latest_vax = vax_df.sort_values("date").groupby("location").last().reset_index()
                best = latest_vax.loc[latest_vax["value"].idxmax()]
                st.success(f"Höchste Impfquote: **{best['location']}** mit **{best['value']:.1f} %**")
            fig_vax = px.line(
                vax_df, x="date", y="value", color="location",
                color_discrete_map=color_map(selected),
                labels={"date": "Datum", "value": "Vollständig Geimpfte (%)", "location": "Land"},
                range_y=[0, 100],
            )
            fig_vax.update_traces(line=dict(width=2.5))
            fig_vax.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0),
                                  legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
            st.plotly_chart(de_format(fig_vax), use_container_width=True)
        else:
            st.info("Oben mindestens ein Land auswählen.")


# ── Walk-Forward-Backtesting (gecached) ───────────────────────────────────────
@st.cache_data
def run_backtest(country: str, start: str, end: str, cutoff_str: str, horizon: int):
    """Rollierendes Backtesting: an jedem Testpunkt h Schritte vorausschauen,
    Modell jeweils nur auf den davor verfügbaren Daten neu anpassen."""
    import warnings
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    df = queries.country_timeline([country], "new_cases_smoothed", start, end)
    if df.empty:
        return {"error": "empty"}

    s = df.set_index("date")["value"].sort_index()
    s.index = pd.to_datetime(s.index)
    s = s.resample("W").mean().fillna(0)
    idx, vals = list(s.index), s.values
    n = len(s)
    cutoff = pd.to_datetime(cutoff_str)
    cut_pos = sum(1 for d in idx if d <= cutoff)   # Anzahl Trainingspunkte

    if cut_pos < 10 or n - cut_pos < 3:
        return {"error": "toofew"}

    pred_dates, preds, actuals, naive = [], [], [], []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for t in range(cut_pos, n):
            train_end = t - horizon          # letzter erlaubter Trainingsindex (inkl.)
            if train_end < 9:                # mind. 10 Trainingspunkte
                continue
            try:
                m  = ExponentialSmoothing(vals[:train_end + 1], trend="add",
                                          damped_trend=True).fit()
                fc = m.forecast(horizon)
                preds.append(float(fc[-1]))
                actuals.append(float(vals[t]))
                naive.append(float(vals[train_end]))   # naive: letzter bekannter Wert
                pred_dates.append(idx[t])
            except Exception:
                continue

    if len(preds) < 3:
        return {"error": "tooshort"}

    preds, actuals, naive = np.array(preds), np.array(actuals), np.array(naive)
    err  = actuals - preds
    mae  = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    mask = actuals != 0
    mape = float(np.mean(np.abs(err[mask] / actuals[mask])) * 100) if mask.any() else float("nan")
    naive_mae = float(np.mean(np.abs(actuals - naive)))

    return {
        "train_dates": idx[:cut_pos], "train_vals": vals[:cut_pos].tolist(),
        "test_dates":  idx[cut_pos:], "test_vals":  vals[cut_pos:].tolist(),
        "pred_dates":  pred_dates,    "pred_vals":  preds.tolist(),
        "mae": mae, "rmse": rmse, "mape": mape, "naive_mae": naive_mae,
        "all_dates": idx,
    }

# ── Prognose & Backtesting (Bonus) ────────────────────────────────────────────
with st.expander("Prognose & Backtesting (Bonus) – Walk-Forward", expanded=False):
    st.caption(
        "Rollierendes Backtesting: Das Modell sagt immer nur wenige Wochen voraus, wird dann mit den "
        "echten Werten abgeglichen und Schritt für Schritt weitergeschoben. Land + neue Fälle (Wochenmittel)."
    )

    fc1, fc2, fc3 = st.columns([1.4, 2, 1])
    with fc1:
        fc_country = st.selectbox(
            "Land", all_countries,
            index=all_countries.index("Germany") if "Germany" in all_countries else 0,
            key="fc_country",
        )
    with fc3:
        horizon = st.selectbox("Horizont", [1, 2, 4], index=1, key="fc_horizon",
            format_func=lambda h: f"{h} Woche" if h == 1 else f"{h} Wochen",
            help="Wie viele Wochen schaut das Modell jeweils voraus?")

    # Wochenraster für den Cutoff-Slider
    fc_df = cached_countries_timeline((fc_country,), "new_cases_smoothed", start, end)
    if fc_df.empty or len(fc_df) < 40:
        st.info("Zu wenige Datenpunkte im gewählten Zeitraum für ein Backtesting.")
    else:
        s_idx = fc_df.set_index("date")["value"].sort_index()
        s_idx.index = pd.to_datetime(s_idx.index)
        weeks = list(s_idx.resample("W").mean().index)
        with fc2:
            cutoff = st.select_slider(
                "Cutoff (Beginn des Testzeitraums)",
                options=weeks,
                value=weeks[int(len(weeks) * 0.6)],
                format_func=lambda d: d.strftime("%d.%m.%Y"),
                key="fc_cutoff",
                help="Ab hier wird getestet. Tipp: direkt vor eine Welle legen.",
            )

        res = run_backtest(fc_country, start, end, cutoff.strftime("%Y-%m-%d"), horizon)

        if "error" in res:
            st.info("Cutoff bitte so wählen, dass Training und Test genügend Punkte haben.")
        else:
            fig_fc = go.Figure()
            fig_fc.add_trace(go.Scatter(x=res["train_dates"], y=res["train_vals"],
                name="Training", line=dict(color="#1d4ed8", width=2)))
            fig_fc.add_trace(go.Scatter(x=res["test_dates"], y=res["test_vals"],
                name="Test (echt)", line=dict(color="#0f172a", width=2)))
            fig_fc.add_trace(go.Scatter(x=res["pred_dates"], y=res["pred_vals"],
                name=f"Prognose ({horizon} Wo. voraus)",
                line=dict(color="#e63946", width=2, dash="dash")))
            fig_fc.add_shape(type="line", x0=cutoff, x1=cutoff, y0=0, y1=1, yref="paper",
                line=dict(color="#9ca3af", width=1, dash="dot"))
            fig_fc.add_annotation(x=cutoff, y=1, yref="paper", text="Cutoff",
                showarrow=False, xanchor="left", yanchor="top",
                font=dict(size=10, color="#6b7280"))
            fig_fc.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
                yaxis_title="Neue Fälle (Wochenmittel)")
            st.plotly_chart(de_format(fig_fc), use_container_width=True)

            mae, rmse, mape, naive_mae = res["mae"], res["rmse"], res["mape"], res["naive_mae"]
            better = "besser" if mae < naive_mae else "schlechter"
            bcolor = "#16a34a" if mae < naive_mae else "#dc2626"
            st.markdown("<p style='color:#64748b; font-size:0.8rem; margin:6px 0 4px 0;'>"
                        "Fehlermaße der Prognose (kleiner = besser):</p>", unsafe_allow_html=True)
            e1, e2, e3, e4 = st.columns(4)
            with e1: st.markdown(metric_card("Mittlerer Fehler", fmt_de(mae, 0),
                "MAE · Ø Abweichung in Fällen", accent="#2563eb", small=True), unsafe_allow_html=True)
            with e2: st.markdown(metric_card("Fehler mit Ausreißern", fmt_de(rmse, 0),
                "RMSE · bestraft große Fehler stärker", accent="#9333ea", small=True), unsafe_allow_html=True)
            with e3: st.markdown(metric_card("Prozentualer Fehler", f"{fmt_de(mape, 1)} %" if not np.isnan(mape) else "–",
                "MAPE · Ø Abweichung in Prozent", accent="#d97706", small=True), unsafe_allow_html=True)
            with e4: st.markdown(metric_card("Modell vs. naive Vorhersage", better,
                f"Naiv = letzter Wert · MAE: {fmt_de(naive_mae, 0)}", bcolor, accent="#0d9488", small=True), unsafe_allow_html=True)

            st.caption(
                "In ruhigen Phasen folgt die Prognose den echten Werten gut. An den Wellen-Wendepunkten "
                "bricht sie sichtbar weg – neue Wellen entstehen durch externe Faktoren (Varianten, Maßnahmen), "
                "die nicht in den Daten stehen. Genau das macht das Backtesting sichtbar."
            )

# ── Datenqualität (Punkt 12) ──────────────────────────────────────────────────
with st.expander("Datengrundlage & Qualitätshinweise", expanded=False):
    q1, q2, q3 = st.columns(3)
    q1.markdown("""
**Quelle**
- Our World in Data (OWID)
- github.com/owid/covid-19-data
- Letzte Aktualisierung: 14. August 2024
""")
    q2.markdown("""
**Datenverfügbarkeit**
- Fallzahlen & Tode: ~95 % vollständig
- Impfdaten: ~45 % vollständig
- Krankenhausdaten: ~13 % (nur reiche Länder)
- Testdaten: ~30 % – nicht verwendet
""")
    q3.markdown("""
**Bekannte Einschränkungen**
- Meldeverzögerungen (bes. Wochenenden)
- Unterschiedliche Teststrategien je Land
- Nachmeldungen können negative Tageswerte erzeugen
- Nicht alle Länder melden gleich zuverlässig
""")
