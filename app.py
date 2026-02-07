import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# =================================================================
# 1. KONFIGURACE
# =================================================================
st.set_page_config(page_title="Kvádr 2.0", layout="wide", initial_sidebar_state="collapsed")

# Skrytí postranního panelu
st.markdown("<style>section[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)

if "page" not in st.session_state: st.session_state.page = "Domů"
if "news_index" not in st.session_state: st.session_state.news_index = 0

# =================================================================
# 2. OPRAVENÉ STYLY (CSS)
# =================================================================
st.markdown("""
<style>
    .stApp { background: radial-gradient(circle at center, #1a2c4e 0%, #070b14 100%); color: white; }
    
    /* Horizontální scrollovací pás */
    .weather-wrapper {
        display: flex;
        overflow-x: auto;
        gap: 10px;
        padding: 10px 0;
        scrollbar-width: none;
        -webkit-overflow-scrolling: touch;
    }
    .weather-wrapper::-webkit-scrollbar { display: none; }
    
    /* Samostatná karta počasí */
    .weather-box {
        flex: 0 0 auto;
        width: 105px;
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 15px;
        padding: 12px 5px;
        text-align: center;
    }
    
    .city-name { font-size: 11px; color: #3b82f6; font-weight: bold; margin-bottom: 5px; }
    .city-temp { font-size: 26px; font-weight: 800; line-height: 1; }
    .city-desc { font-size: 10px; opacity: 0.8; margin-top: 5px; }

    /* NEWS TICKER - POSUNUTÝ NAHORU, aby nezavazela tlačítka mobilu */
    .news-float {
        position: fixed;
        bottom: 85px; /* Výrazný posun nahoru od spodní hrany */
        left: 10px;
        right: 10px;
        background: #002d6e;
        color: white;
        padding: 15px;
        border-radius: 20px;
        border: 2px solid #3b82f6;
        z-index: 9999;
        text-align: center;
        font-weight: bold;
        box-shadow: 0 4px 20px rgba(0,0,0,0.6);
    }
</style>
""", unsafe_allow_html=True)

# =================================================================
# 3. FUNKCE PRO DATA
# =================================================================
def get_weather_data():
    mesta = {"Nové Město": (50.34, 16.15), "Rychnov": (50.16, 16.27), "Bělá": (50.53, 14.80), "Praha": (50.07, 14.43), "Hradec": (50.21, 15.83)}
    results = []
    mapping = {0:"Jasno ☀️",1:"Jasno 🌤️",2:"Polojasno ⛅",3:"Zataženo ☁️",45:"Mlha 🌫️",51:"Mrholení 🌦️",61:"Déšť 🌧️",71:"Sněžení ❄️",80:"Přeháňky 🌧️",95:"Bouřka ⚡"}
    
    for m, (lat, lon) in mesta.items():
        try:
            r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&timezone=auto").json()
            results.append({
                "mesto": m,
                "temp": f"{round(r['current']['temperature_2m'])}°",
                "stav": mapping.get(r['current']['weathercode'], "Neznámé")
            })
        except:
            results.append({"mesto": m, "temp": "??", "stav": "Chyba"})
    return results

# =================================================================
# 4. VYKRESLENÍ STRÁNKY
# =================================================================
if st.session_state.page == "Domů":
    st.markdown("<h2 style='text-align:center;'>🏙️ Kvádr Portál</h2>", unsafe_allow_html=True)
    
    if st.button("💬 OTEVŘÍT AI ASISTENTA 2.0", use_container_width=True, type="primary"):
        st.session_state.page = "AI Chat"; st.rerun()

    # VYKRESLENÍ POČASÍ - Zde je ta oprava (unsafe_allow_html=True)
    weather_list = get_weather_data()
    
    html_content = '<div class="weather-wrapper">'
    for w in weather_list:
        html_content += f'''
        <div class="weather-box">
            <div class="city-name">{w["mesto"]}</div>
            <div class="city-temp">{w["temp"]}</div>
            <div class="city-desc">{w["stav"]}</div>
        </div>
        '''
    html_content += '</div>'
    
    # Tato funkce vykreslí HTML správně a ne jako text
    st.markdown(html_content, unsafe_allow_html=True)

    st.write("---")

    # ZPRÁVY - Zobrazení v plovoucí liště nad tlačítky
    try:
        rss = ET.fromstring(requests.get("https://ct24.ceskatelevize.cz/rss/hlavni-zpravy").content)
        zpravy = [i.find('title').text for i in rss.findall('.//item')[:10]]
        aktualni_zprava = zpravy[st.session_state.news_index % len(zpravy)]
        
        st.markdown(f'''
            <div class="news-float">
                🗞️ {aktualni_zprava}
            </div>
        ''', unsafe_allow_html=True)
    except:
        pass

    # Automatická obnova pro ticker
    time.sleep(8)
    st.session_state.news_index += 1
    st.rerun()
