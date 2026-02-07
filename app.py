import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import time

# =================================================================
# 1. KONFIGURACE A STYLOVÁNÍ
# =================================================================
st.set_page_config(
    page_title="KVÁDR PORTÁL 2.0",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Nastavení Gemini API
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

WEATHER_MAP = {
    0: ("Jasno", "☀️"), 1: ("Skoro jasno", "🌤️"), 2: ("Polojasno", "⛅"), 3: ("Zataženo", "☁️"),
    45: ("Mlha", "🌫️"), 51: ("Mrholení", "🌦️"), 61: ("Déšť", "🌧️"), 71: ("Sněžení", "❄️"),
    80: ("Přeháňky", "🌧️"), 95: ("Bouřka", "⚡")
}

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@600;700&display=swap');
    
    section[data-testid="stSidebar"] {display: none;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .stApp {
        background: #020617;
        color: #f8fafc;
        font-family: 'Rajdhani', sans-serif;
    }

    .portal-header {
        text-align: center;
        padding: 15px;
        background: #1e3a8a;
        border-bottom: 3px solid #3b82f6;
        margin-bottom: 20px;
        border-radius: 0 0 20px 20px;
    }
    .portal-header h1 { color: white; text-transform: uppercase; margin: 0; }

    .weather-card {
        background: #1e293b;
        border: 2px solid #3b82f6;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
    }
    .weather-temp {
        font-size: 38px;
        font-weight: 800;
        color: #ffffff !important;
        margin: 5px 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }
    .weather-city { color: #60a5fa; font-weight: bold; text-transform: uppercase; }

    .news-bubble {
        position: fixed;
        bottom: 55px;
        left: 20px;
        right: 20px;
        background: #2563eb;
        color: white;
        padding: 14px 25px;
        border-radius: 50px;
        border: 2px solid #93c5fd;
        z-index: 1000;
        text-align: center;
        font-weight: 600;
        font-size: 17px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.6);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .stButton>button {
        background: #e11d48;
        color: white;
        border-radius: 12px;
        border: none;
        padding: 18px;
        font-weight: bold;
        width: 100%;
        transition: 0.3s;
    }
    .stButton>button:hover { background: #be123c; transform: scale(1.01); }
</style>
""", unsafe_allow_html=True)

# =================================================================
# 2. CACHE A LOGIKA (10 MINUT POČASÍ)
# =================================================================
@st.cache_data(ttl=600)
def get_weather(lat, lon):
    try:
        r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=auto", timeout=5).json()
        return r
    except: return None

@st.cache_data(ttl=300)
def get_news_list():
    try:
        rss = ET.fromstring(requests.get("https://ct24.ceskatelevize.cz/rss/hlavni-zpravy", timeout=5).content)
        return [item.find('title').text for item in rss.findall('.//item')][:15]
    except: return ["Zprávy se načítají..."]

# =================================================================
# 3. STRÁNKY
# =================================================================
if "page" not in st.session_state: st.session_state.page = "Domů"
if "news_idx" not in st.session_state: st.session_state.news_idx = 0

# --- DOMOVSKÁ STRÁNKA ---
if st.session_state.page == "Domů":
    st.markdown('<div class="portal-header"><h1>KVÁDR PORTÁL 2.0</h1></div>', unsafe_allow_html=True)

    if st.button("💬 OTEVŘÍT KVÁDR AI"):
        st.session_state.page = "Chat"
        st.rerun()

    st.write("")
    
    mesta = {"Nové Město": (50.34, 16.15), "Rychnov": (50.16, 16.27), "Bělá": (50.76, 15.05), "Praha": (50.07, 14.43)}
    cols = st.columns(4)
    
    for i, (name, coords) in enumerate(mesta.items()):
        data = get_weather(coords[0], coords[1])
        if data:
            t = int(round(data['current']['temperature_2m']))
            stav, icon = WEATHER_MAP.get(data['current']['weathercode'], ("-", "🌡️"))
            with cols[i]:
                st.markdown(f'<div class="weather-card"><div class="weather-city">{name}</div><div class="weather-temp">{t}°</div><div>{icon} {stav}</div></div>', unsafe_allow_html=True)

    st.write("")
    with st.expander("📊 DETAILNÍ PŘEDPOVĚĎ"):
        vyber = st.selectbox("Vyberte město:", list(mesta.keys()))
        d = get_weather(mesta[vyber][0], mesta[vyber][1])
        if d:
            df = pd.DataFrame({
                "Datum": [datetime.strptime(day, "%Y-%m-%d").strftime("%d.%m.") for day in d['daily']['time']],
                "Stav": [WEATHER_MAP.get(c, ("?", ""))[0] for c in d['daily']['weathercode']],
                "Max (°C)": [int(round(temp)) for temp in d['daily']['temperature_2m_max']],
                "Min (°C)": [int(round(temp)) for temp in d['daily']['temperature_2m_min']]
            })
            st.table(df)

    st.markdown("### 📌 OZNÁMENÍ")
    try:
        s_id = st.secrets["GSHEET_URL"].split("/d/")[1].split("/")[0]
        url = f"https://docs.google.com/spreadsheets/d/{s_id}/gviz/tq?tqx=out:csv&sheet=List%202"
        for msg in pd.read_csv(url).dropna()['zprava']: st.info(f"**{msg}**")
    except: st.write("Žádná nová oznámení.")

    # ROTACE ZPRÁV (7 SEKUND)
    news = get_news_list()
    st.session_state.news_idx = (st.session_state.news_idx + 1) % len(news)
    st.markdown(f'<div class="news-bubble">ZPRÁVY: {news[st.session_state.news_idx]}</div>', unsafe_allow_html=True)

    time.sleep(7)
    st.rerun()

# --- CHAT STRÁNKA ---
else:
    st.markdown("<h2 style='text-align: center; color: #60a5fa;'>🤖 KVÁDR AI ASISTENT</h2>", unsafe_allow_html=True)
    if st.button("🏠 ZPĚT NA PORTÁL"):
        st.session_state.page = "Domů"
        st.rerun()

    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if p := st.chat_input("Napište dotaz..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        with st.chat_message("assistant"):
            try:
                model = genai.GenerativeModel('gemini-pro')
                resp = model.generate_content(f"Jsi asistent Kvádr. Odpověz česky: {p}").text
                st.markdown(resp)
                st.session_state.messages.append({"role": "assistant", "content": resp})
            except: st.write("AI je zaneprázdněna.")
