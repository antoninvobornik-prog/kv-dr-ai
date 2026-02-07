import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# =================================================================
# 1. HLAVNÍ KONFIGURACE A DESIGN (CSS)
# =================================================================
st.set_page_config(
    page_title="Kvádr Portál 2.0",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Skrytí Streamlit prvků a definice vlastního UI
st.markdown("""
<style>
    /* Skrytí postranního panelu a patičky */
    section[data-testid="stSidebar"] {display: none;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Pozadí celé aplikace */
    .stApp {
        background: linear-gradient(180deg, #0f172a 0%, #020617 100%);
        color: #f8fafc;
    }

    /* Kontejner pro horizontální scroll počasí */
    .weather-container {
        display: flex;
        flex-direction: row;
        overflow-x: auto;
        gap: 15px;
        padding: 20px 10px;
        scrollbar-width: none;
        -webkit-overflow-scrolling: touch;
    }
    .weather-container::-webkit-scrollbar { display: none; }

    /* Karta počasí - GLASSMORPHISM DESIGN */
    .weather-card {
        flex: 0 0 auto;
        width: 130px;
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 15px 10px;
        text-align: center;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        transition: transform 0.3s ease;
    }
    
    .weather-card:active { transform: scale(0.95); }

    .city-label { 
        font-size: 13px; 
        color: #60a5fa; 
        font-weight: 700; 
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .temp-value { 
        font-size: 32px; 
        font-weight: 900; 
        color: #ffffff;
        margin: 5px 0;
    }
    .status-text { 
        font-size: 11px; 
        opacity: 0.8; 
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .extra-info {
        font-size: 9px;
        color: #94a3b8;
        margin-top: 8px;
        border-top: 1px solid rgba(255,255,255,0.1);
        padding-top: 5px;
    }

    /* NEWS TICKER - PLOVOUCÍ LIŠTA POSUNUTÁ NAHORU */
    .news-ticker-fixed {
        position: fixed;
        bottom: 110px; /* Výrazný odstup od ovládacích prvků mobilu */
        left: 15px;
        right: 15px;
        background: rgba(30, 58, 138, 0.9);
        backdrop-filter: blur(15px);
        color: white;
        padding: 15px 20px;
        border-radius: 25px;
        border: 1px solid #3b82f6;
        z-index: 99999;
        text-align: center;
        font-size: 14px;
        font-weight: 600;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
    }

    /* Tlačítka */
    .stButton>button {
        border-radius: 15px;
        height: 55px;
        font-weight: bold;
        background: linear-gradient(90deg, #2563eb, #7c3aed);
        border: none;
        color: white;
        font-size: 16px;
        box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# =================================================================
# 2. LOGIKA PRO DATA (POČASÍ A GOOGLE SHEETS)
# =================================================================

def get_weather_icon(code):
    icons = {
        0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️", 
        45: "🌫️", 48: "🌫️", 51: "🌦️", 53: "🌦️", 
        61: "🌧️", 63: "🌧️", 71: "❄️", 80: "🌧️", 95: "⚡"
    }
    return icons.get(code, "🌡️")

def get_weather_desc(code):
    desc = {
        0: "Jasno", 1: "Skoro jasno", 2: "Polojasno", 3: "Zataženo", 
        45: "Mlha", 51: "Mrholení", 61: "Déšť", 71: "Sněžení", 80: "Přeháňky", 95: "Bouřka"
    }
    return desc.get(code, "Neznámé")

@st.cache_data(ttl=600)
def fetch_all_weather():
    mesta = {
        "Nové Město": (50.34, 16.15),
        "Rychnov": (50.16, 16.27),
        "Bělá": (50.53, 14.80),
        "Praha": (50.07, 14.43),
        "Hradec": (50.21, 15.83)
    }
    results = []
    for m, (lat, lon) in mesta.items():
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weathercode,wind_speed_10m&timezone=auto"
            r = requests.get(url, timeout=5).json()
            curr = r['current']
            results.append({
                "city": m,
                "temp": f"{round(curr['temperature_2m'])}°",
                "desc": f"{get_weather_desc(curr['weathercode'])} {get_weather_icon(curr['weathercode'])}",
                "wind": f"{round(curr['wind_speed_10m'])} km/h",
                "hum": f"{curr['relative_humidity_2m']}%"
            })
        except:
            results.append({"city": m, "temp": "--", "desc": "Chyba", "wind": "0", "hum": "0"})
    return results

def load_google_sheet(sheet_name):
    try:
        sheet_id = st.secrets["GSHEET_URL"].split("/d/")[1].split("/")[0]
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(sheet_name)}"
        return pd.read_csv(url)
    except:
        return pd.DataFrame(columns=['zprava'])

# =================================================================
# 3. NAVIGACE A STAVY
# =================================================================
if "page" not in st.session_state: st.session_state.page = "Domů"
if "news_idx" not in st.session_state: st.session_state.news_idx = 0

def switch_page(target):
    st.session_state.page = target
    st.rerun()

# =================================================================
# 4. RENDEROVÁNÍ STRÁNKY
# =================================================================

if st.session_state.page == "Domů":
    # Horní Logo/Název
    st.markdown("<h1 style='text-align:center; font-size: 28px; margin-bottom: 20px;'>🏙️ KVÁDR PORTÁL 2.0</h1>", unsafe_allow_html=True)

    # Hlavní tlačítko AI
    if st.button("💬 OTEVŘÍT AI ASISTENTA", use_container_width=True):
        switch_page("AI Chat")

    st.write("") # Mezera

    # --- SEKCE POČASÍ (OPRAVENÁ) ---
    weather_data = fetch_all_weather()
    
    # Skládání HTML do jednoho bloku, aby Streamlit nic nerozbil
    weather_html = '<div class="weather-container">'
    for w in weather_data:
        weather_html += f"""
        <div class="weather-card">
            <div class="city-label">{w['city']}</div>
            <div class="temp-value">{w['temp']}</div>
            <div class="status-text">{w['desc']}</div>
            <div class="extra-info">💨 {w['wind']} | 💧 {w['hum']}</div>
        </div>
        """
    weather_html += '</div>'
    
    # Klíčový řádek: unsafe_allow_html=True zajistí zobrazení buněk
    st.markdown(weather_html, unsafe_allow_html=True)

    # --- AKTUALITY Z LISTU 2 ---
    st.write("---")
    st.markdown("### 🔔 Oznámení")
    news_df = load_google_sheet("List 2")
    for _, row in news_df.dropna(subset=['zprava']).iterrows():
        st.info(row['zprava'])

    # --- NEWS TICKER (RSS) ---
    try:
        rss_url = "https://ct24.ceskatelevize.cz/rss/hlavni-zpravy"
        rss_res = requests.get(rss_url, timeout=5)
        root = ET.fromstring(rss_res.content)
        items = [i.find('title').text for i in root.findall('.//item')[:10]]
        
        current_msg = items[st.session_state.news_idx % len(items)]
        
        st.markdown(f"""
            <div class="news-ticker-fixed">
                🗞️ {current_msg}
            </div>
        """, unsafe_allow_html=True)
    except:
        st.markdown('<div class="news-ticker-fixed">🗞️ Zprávy se nepodařilo načíst.</div>', unsafe_allow_html=True)

    # Automatické osvěžení každých 8 sekund pro ticker
    time.sleep(8)
    st.session_state.news_idx += 1
    st.rerun()

# =================================================================
# 5. STRÁNKA CHATU (AI ASISTENT)
# =================================================================
else:
    st.markdown("### 🤖 Kvádr AI Asistent")
    if st.button("🏠 NÁVRAT NA PORTÁL", use_container_width=True):
        switch_page("Domů")
    
    st.write("---")
    st.info("Zde můžete pokládat dotazy ohledně projektu Kvádr.")
    
    # Zde by pokračovala logika chatu z předchozích verzí...
    # (Pro zachování délky a funkčnosti doporučuji ponechat stávající Gemini integraci)
