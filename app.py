import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import time

# --- KONFIGURACE ---
st.set_page_config(page_title="KVÁDR PORTÁL 2.0", layout="wide", initial_sidebar_state="collapsed")

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    if "ai_model" not in st.session_state:
        try:
            available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            st.session_state.ai_model = next((m for m in available if "1.5-flash" in m), available[0])
        except: st.session_state.ai_model = "models/gemini-1.5-flash"

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@600;700&display=swap');
    section[data-testid="stSidebar"], footer, header {display: none;}
    .stApp { background: #020617; color: #f8fafc; font-family: 'Rajdhani', sans-serif; }
    .portal-header { text-align: center; padding: 15px; background: #1e3a8a; border-bottom: 3px solid #3b82f6; border-radius: 0 0 20px 20px; margin-bottom: 10px; }
    .portal-header h1 { font-size: 2rem; margin: 0; }
    
    /* Zmenšené karty počasí */
    .weather-card {
        background: #1e293b; border: 1px solid #3b82f6; border-radius: 10px;
        padding: 10px; text-align: center; margin-bottom: 5px;
    }
    .city-name { color: #60a5fa; font-size: 1rem; font-weight: bold; }
    .temp-val { font-size: 1.8rem; font-weight: 800; color: white; }
    .status-small { font-size: 0.8rem; color: #94a3b8; }

    .news-bubble {
        position: fixed; bottom: 30px; left: 5%; right: 5%;
        background: #2563eb; color: white; padding: 10px;
        border-radius: 30px; text-align: center; z-index: 9999;
    }
    .stInfo { background-color: #1e3a8a !important; color: white !important; border: 1px solid #3b82f6 !important; }
</style>
""", unsafe_allow_html=True)

DNY_CZ = {"Monday":"Pondělí","Tuesday":"Úterý","Wednesday":"Středa","Thursday":"Čtvrtek","Friday":"Pátek","Saturday":"Sobota","Sunday":"Neděle"}
W_DESC = {0:"Jasno ☀️", 1:"Skoro jasno 🌤️", 2:"Polojasno ⛅", 3:"Zataženo ☁️", 45:"Mlha 🌫️", 61:"Déšť 🌧️", 95:"Bouřka ⚡"}

@st.cache_data(ttl=600)
def get_weather(lat, lon):
    try: return requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=auto").json()
    except: return None

@st.cache_data(ttl=300)
def get_news():
    try:
        r = requests.get("https://ct24.ceskatelevize.cz/rss/hlavni-zpravy")
        return [item.find('title').text for item in ET.fromstring(r.content).findall('.//item')]
    except: return ["Zprávy nedostupné."]

# --- HLAVNÍ LOGIKA ---
if "page" not in st.session_state: st.session_state.page = "Domů"
if "news_idx" not in st.session_state: st.session_state.news_idx = 0

if st.session_state.page == "Domů":
    st.markdown('<div class="portal-header"><h1>KVÁDR PORTÁL 2.0</h1></div>', unsafe_allow_html=True)

    # 1. LIST 2 - OZNÁMENÍ (HLAVNÍ PRIORITA NAHOŘE)
    try:
        sheet_id = st.secrets["GSHEET_URL"].split("/d/")[1].split("/")[0]
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=List%202"
        oznameni = pd.read_csv(url).dropna(subset=['zprava'])
        for msg in oznameni['zprava']:
            st.info(f"📌 {msg}")
    except:
        st.write("Žádná aktuální oznámení z Listu 2.")

    # 2. MENŠÍ POČASÍ
    mesta = {"Nové Město": (50.34, 16.15), "Rychnov": (50.16, 16.27), "Bělá": (50.76, 15.05), "Praha": (50.07, 14.43)}
    cols = st.columns(4)
    for i, (name, coords) in enumerate(mesta.items()):
        d = get_weather(coords[0], coords[1])
        if d:
            t = int(round(d['current']['temperature_2m']))
            s = W_DESC.get(d['current']['weathercode'], "Oblačno")
            with cols[i]:
                st.markdown(f'<div class="weather-card"><div class="city-name">{name}</div><div class="temp-val">{t}°C</div><div class="status-small">{s}</div></div>', unsafe_allow_html=True)

    if st.button("💬 OTEVŘÍT KVÁDR AI", use_container_width=True):
        st.session_state.page = "Chat"
        st.rerun()

    # 3. ZPRÁVY (ROTACE)
    news = get_news()
    st.session_state.news_idx = (st.session_state.news_idx + 1) % len(news)
    st.markdown(f'<div class="news-bubble"><b>INFO:</b> {news[st.session_state.news_idx]}</div>', unsafe_allow_html=True)
    
    time.sleep(7)
    st.rerun()

# --- CHAT ---
else:
    st.markdown("<div class='portal-header'><h1>🤖 KVÁDR ASISTENT</h1></div>", unsafe_allow_html=True)
    if st.button("🏠 ZPĚT"):
        st.session_state.page = "Domů"
        st.rerun()

    if "msgs" not in st.session_state:
        st.session_state.msgs = [{"role": "assistant", "content": "Ahoj! Jsem Kvádr mozek, tvůj inteligentní asistent. Jak ti můžu dnes pomoci?"}]

    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if p := st.chat_input("Zeptej se..."):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        with st.chat_message("assistant"):
            try:
                mod = genai.GenerativeModel(st.session_state.ai_model)
                # Přísnější instrukce pro model
                res = mod.generate_content(f"Jsi Kvádr mozek, oficiální asistent portálu Kvádr. Buď přátelský, představ se, pokud je to potřeba, a odpověz česky: {p}").text
                st.markdown(res)
                st.session_state.msgs.append({"role": "assistant", "content": res})
            except: st.error("AI je zaneprázdněna.")
