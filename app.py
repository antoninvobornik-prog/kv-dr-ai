import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# --- KONFIGURACE ---
st.set_page_config(page_title="Kvádr 2.0", layout="wide", initial_sidebar_state="collapsed")

# Inicializace stavů
if "page" not in st.session_state: st.session_state.page = "Domů"
if "news_index" not in st.session_state: st.session_state.news_index = 0

# --- EXTRÉMNĚ KOMPAKTNÍ CSS ---
st.markdown("""
<style>
    .stApp { background: #070b14; color: white; }
    header {visibility: hidden;}
    
    /* Zmenšení hlavního nadpisu */
    .main-title {
        font-size: 1.2rem !important;
        font-weight: 800;
        text-align: center;
        margin: 5px 0;
        color: #3b82f6;
    }

    /* Kompaktní tlačítko AI */
    .stButton>button {
        padding: 5px 10px !important;
        font-size: 0.8rem !important;
        border-radius: 8px !important;
        height: auto !important;
    }

    /* Počasí - Mikro karty v řadě */
    .weather-container {
        display: flex;
        overflow-x: auto;
        gap: 6px;
        padding: 5px 0;
    }
    .weather-card {
        min-width: 75px;
        background: rgba(255, 255, 255, 0.05);
        padding: 6px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .w-city { font-size: 0.6rem; opacity: 0.7; text-transform: uppercase; }
    .w-temp { font-size: 1.1rem; font-weight: bold; margin: 2px 0; }
    .w-icon { font-size: 0.9rem; }

    /* Bubliny aktualit - zmenšení */
    .stAlert {
        padding: 8px !important;
        font-size: 0.75rem !important;
        border-radius: 10px !important;
    }

    /* Tabulka - zmenšení textu */
    .styled-table { font-size: 0.7rem !important; width: 100%; }
    
    /* Spodní lišta - drobnější */
    .news-ticker {
        position: fixed; bottom: 0; left: 0; width: 100%;
        background: #001a41; padding: 10px;
        font-size: 0.75rem; text-align: center;
        border-top: 1px solid #3b82f6; z-index: 99;
    }

    /* Skrytí Streamlit prvků pro víc místa */
    div[data-testid="stExpander"] { margin-bottom: 0px !important; }
</style>
""", unsafe_allow_html=True)

# --- FUNKCE DATA ---
@st.cache_data(ttl=600)
def nacti_pocasi():
    mesta = {"N.Město": (50.34, 16.15), "Rychnov": (50.16, 16.27), "Bělá": (50.53, 14.80), "Praha": (50.07, 14.43), "Hradec": (50.21, 15.83)}
    res = {}
    mapping = {0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️", 45: "🌫️", 51: "🌦️", 61: "🌧️", 71: "❄️", 80: "🌧️", 95: "⚡"}
    for m, (lat, lon) in mesta.items():
        try:
            r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&daily=temperature_2m_max,temperature_2m_min&timezone=auto").json()
            res[m] = {"t": f"{round(r['current']['temperature_2m'])}°", "i": mapping.get(r['current']['weathercode'], "☁️")}
        except: res[m] = {"t": "??", "i": "❓"}
    return res

def nacti_gsheets(list_name):
    try:
        sid = st.secrets["GSHEET_URL"].split("/d/")[1].split("/")[0]
        url = f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(list_name)}"
        return pd.read_csv(url)
    except: return pd.DataFrame(columns=['zprava'])

# --- LOGIKA STRÁNKY ---
if st.session_state.page == "Domů":
    st.markdown('<div class="main-title">KVÁDR 2.0</div>', unsafe_allow_html=True)
    
    # AI Tlačítko (Kompaktní)
    if st.button("💬 AI ASISTENT", use_container_width=True):
        st.session_state.page = "AI"; st.rerun()

    # Počasí (Mikro karty)
    w_data = nacti_pocasi()
    w_html = '<div class="weather-container">'
    for m, d in w_data.items():
        w_html += f'<div class="weather-card"><div class="w-city">{m}</div><div class="w-temp">{d["t"]}</div><div class="w-icon">{d["i"]}</div></div>'
    w_html += '</div>'
    st.markdown(w_html, unsafe_allow_html=True)

    # Aktuality (Zmenšené bubliny)
    df_ozn = nacti_gsheets("List 2")
    for z in df_ozn['zprava'].dropna()[:2]: # Jen první dvě pro místo
        st.info(z)

    # RSS Ticker (Drobný dole)
    try:
        rss = ET.fromstring(requests.get("https://ct24.ceskatelevize.cz/rss/hlavni-zpravy").content)
        zpravy = [i.find('title').text for i in rss.findall('.//item')[:5]]
        idx = st.session_state.news_index % len(zpravy)
        st.markdown(f'<div class="news-ticker">🗞️ {zpravy[idx]}</div>', unsafe_allow_html=True)
    except: pass

    time.sleep(10)
    st.session_state.news_index += 1
    st.rerun()

else:
    # AI Chat sekce (zjednodušená pro mobil)
    if st.button("⬅ ZPĚT"): st.session_state.page = "Domů"; st.rerun()
    st.caption("Kvádr AI - zadejte dotaz")
    # ... zbytek chatovací logiky (stejný jako dříve, jen s menším písmem v CSS)
