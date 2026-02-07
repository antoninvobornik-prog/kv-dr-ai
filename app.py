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
    
    .portal-header { text-align: center; padding: 15px; background: linear-gradient(90deg, #1e3a8a, #3b82f6); border-bottom: 4px solid #60a5fa; border-radius: 0 0 20px 20px; margin-bottom: 10px; }
    
    /* EXTRÉMNÍ TLAČÍTKO AI */
    .stButton>button {
        background: linear-gradient(45deg, #ef4444, #dc2626) !important;
        color: white !important;
        font-size: 28px !important;
        font-weight: 800 !important;
        height: 80px !important;
        border-radius: 20px !important;
        border: 4px solid white !important;
        box-shadow: 0 0 25px rgba(239, 68, 68, 0.6) !important;
        text-transform: uppercase;
        letter-spacing: 2px;
        transition: 0.3s;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(1); box-shadow: 0 0 25px rgba(239, 68, 68, 0.6); }
        50% { transform: scale(1.02); box-shadow: 0 0 45px rgba(239, 68, 68, 0.9); }
        100% { transform: scale(1); box-shadow: 0 0 25px rgba(239, 68, 68, 0.6); }
    }

    /* Karty počasí - kompaktní */
    .weather-card { background: #1e293b; border: 1px solid #3b82f6; border-radius: 12px; padding: 10px; text-align: center; }
    .city-name { color: #60a5fa; font-size: 1rem; font-weight: bold; }
    .temp-val { font-size: 1.8rem; font-weight: 800; color: white; }

    /* POSUNUTÝ PANEL ZPRÁV */
    .news-bubble {
        position: fixed; bottom: 80px; left: 5%; right: 5%;
        background: #2563eb; color: white; padding: 15px;
        border-radius: 40px; text-align: center; z-index: 9999;
        font-size: 1.2rem; font-weight: 700; border: 2px solid white;
        box-shadow: 0 10px 30px rgba(0,0,0,0.8);
    }
    .stInfo { background-color: #1e3a8a !important; color: white !important; border: 2px solid #3b82f6 !important; font-size: 1.1rem !important; }
</style>
""", unsafe_allow_html=True)

W_DESC = {0:"Jasno ☀️", 1:"Skoro jasno 🌤️", 2:"Polojasno ⛅", 3:"Zataženo ☁️", 45:"Mlha 🌫️", 61:"Déšť 🌧️", 95:"Bouřka ⚡"}

@st.cache_data(ttl=600)
def get_weather(lat, lon):
    try: return requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&timezone=auto").json()
    except: return None

@st.cache_data(ttl=300)
def get_news():
    try:
        r = requests.get("https://ct24.ceskatelevize.cz/rss/hlavni-zpravy")
        return [item.find('title').text for item in ET.fromstring(r.content).findall('.//item')]
    except: return ["Zprávy momentálně nejsou dostupné."]

# --- NAVIGACE ---
if "page" not in st.session_state: st.session_state.page = "Domů"
if "news_idx" not in st.session_state: st.session_state.news_idx = 0

if st.session_state.page == "Domů":
    st.markdown('<div class="portal-header"><h1>KVÁDR PORTÁL 2.0</h1></div>', unsafe_allow_html=True)

    # 1. LIST 2 OZNÁMENÍ (ZŮSTÁVÁ NAHOŘE)
    try:
        sheet_id = st.secrets["GSHEET_URL"].split("/d/")[1].split("/")[0]
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=List%202"
        oznameni = pd.read_csv(url).dropna(subset=['zprava'])
        for msg in oznameni['zprava']:
            st.info(f"📢 {msg}")
    except:
        st.write("Aktuálně bez prioritních oznámení.")

    # 2. POČASÍ (PŘEHLEDNÉ KARTY)
    mesta = {"Nové Město": (50.34, 16.15), "Rychnov": (50.16, 16.27), "Bělá": (50.76, 15.05), "Praha": (50.07, 14.43)}
    cols = st.columns(4)
    for i, (name, coords) in enumerate(mesta.items()):
        d = get_weather(coords[0], coords[1])
        if d:
            t = int(round(d['current']['temperature_2m']))
            s = W_DESC.get(d['current']['weathercode'], "Oblačno")
            with cols[i]:
                st.markdown(f'<div class="weather-card"><div class="city-name">{name}</div><div class="temp-val">{t}°C</div><div style="font-size:0.8rem; color:#94a3b8;">{s}</div></div>', unsafe_allow_html=True)

    st.write(" ") # Mezera
    # 3. MEGA TLAČÍTKO
    if st.button("🔥 OTEVŘÍT KVÁDR AI ASISTENTA 🔥", use_container_width=True):
        st.session_state.page = "Chat"
        st.rerun()

    # 4. ROTUJÍCÍ ZPRÁVY (VÝŠE POLOŽENÉ)
    news = get_news()
    st.session_state.news_idx = (st.session_state.news_idx + 1) % len(news)
    st.markdown(f'<div class="news-bubble">AKTUALITA: {news[st.session_state.news_idx]}</div>', unsafe_allow_html=True)
    
    time.sleep(7)
    st.rerun()

else:
    # CHAT SEKCE
    st.markdown("<div class='portal-header'><h1>🤖 KVÁDR MOZEK AI</h1></div>", unsafe_allow_html=True)
    if st.button("⬅️ ZPĚT NA PORTÁL"):
        st.session_state.page = "Domů"
        st.rerun()

    if "msgs" not in st.session_state:
        st.session_state.msgs = [{"role": "assistant", "content": "Zdravím! Jsem Kvádr mozek, tvůj osobní asistent. Jak ti můžu dnes pomoci?"}]

    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if p := st.chat_input("Napište dotaz..."):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        with st.chat_message("assistant"):
            try:
                mod = genai.GenerativeModel(st.session_state.ai_model)
                res = mod.generate_content(f"Jsi Kvádr mozek, mluv česky, stručně a přátelsky. Dotaz: {p}").text
                st.markdown(res)
                st.session_state.msgs.append({"role": "assistant", "content": res})
            except: st.error("AI je momentálně offline.")
