import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import time

# =================================================================
# 1. KONFIGURACE A STYLOVÁNÍ (ROBUSTNÍ VERZE)
# =================================================================
st.set_page_config(page_title="KVÁDR PORTÁL 2.0", layout="wide", initial_sidebar_state="collapsed")

# Dynamický výběr modelu (vždy ten nejlepší dostupný)
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    if "ai_model" not in st.session_state:
        try:
            available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            st.session_state.ai_model = next((m for m in available if "1.5-flash" in m), available[0])
        except: st.session_state.ai_model = "models/gemini-1.5-flash"

# CSS pro pořádný vzhled
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@600;700&display=swap');
    section[data-testid="stSidebar"], footer, header {display: none;}
    .stApp { background: #020617; color: #f8fafc; font-family: 'Rajdhani', sans-serif; }
    
    .portal-header {
        text-align: center; padding: 25px; background: linear-gradient(90deg, #1e3a8a, #3b82f6);
        border-bottom: 4px solid #60a5fa; margin-bottom: 25px; border-radius: 0 0 30px 30px;
    }
    
    .weather-card {
        background: rgba(30, 41, 59, 0.8); border: 2px solid #3b82f6; border-radius: 15px;
        padding: 20px; text-align: center; transition: 0.3s;
    }
    .city-name { color: #60a5fa; font-weight: 700; font-size: 1.4rem; text-transform: uppercase; }
    .temp-val { font-size: 3.2rem; font-weight: 800; color: white; margin: 5px 0; }
    .status-text { color: #94a3b8; font-size: 1.1rem; font-weight: 500; }
    
    .news-bubble {
        position: fixed; bottom: 40px; left: 10%; right: 10%;
        background: #2563eb; color: white; padding: 15px 25px;
        border-radius: 50px; border: 2px solid #93c5fd; z-index: 9999;
        text-align: center; font-weight: 600; font-size: 1.1rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
</style>
""", unsafe_allow_html=True)

# --- ČESKÉ PŘEKLADY ---
DNY_CZ = {"Monday": "Pondělí", "Tuesday": "Úterý", "Wednesday": "Středa", "Thursday": "Čtvrtek", "Friday": "Pátek", "Saturday": "Sobota", "Sunday": "Neděle"}
W_DESC = {0: "Jasno ☀️", 1: "Skoro jasno 🌤️", 2: "Polojasno ⛅", 3: "Zataženo ☁️", 45: "Mlha 🌫️", 51: "Mrholení 🌧️", 61: "Déšť 🌧️", 71: "Sněžení ❄️", 80: "Přeháňky 🌧️", 95: "Bouřka ⚡"}

# =================================================================
# 2. FUNKCE PRO DATA
# =================================================================
@st.cache_data(ttl=600)
def get_weather(lat, lon):
    try:
        r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode,windspeed_10m&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=auto").json()
        return r
    except: return None

@st.cache_data(ttl=300)
def get_news():
    try:
        r = requests.get("https://ct24.ceskatelevize.cz/rss/hlavni-zpravy", timeout=5)
        root = ET.fromstring(r.content)
        return [item.find('title').text for item in root.findall('.//item')]
    except: return ["Zprávy se nepodařilo načíst."]

# =================================================================
# 3. ZOBRAZENÍ
# =================================================================
if "page" not in st.session_state: st.session_state.page = "Domů"
if "news_idx" not in st.session_state: st.session_state.news_idx = 0

if st.session_state.page == "Domů":
    st.markdown('<div class="portal-header"><h1>KVÁDR PORTÁL 2.0</h1></div>', unsafe_allow_html=True)

    # Hlavní akční tlačítko
    if st.button("💬 SPUSTIT KVÁDR AI ASISTENTA", use_container_width=True):
        st.session_state.page = "Chat"
        st.rerun()

    st.write("### 📍 AKTUÁLNÍ INFO Z REGIONŮ")
    mesta = {"Nové Město": (50.34, 16.15), "Rychnov": (50.16, 16.27), "Bělá": (50.76, 15.05), "Praha": (50.07, 14.43)}
    
    cols = st.columns(4)
    for i, (name, coords) in enumerate(mesta.items()):
        d = get_weather(coords[0], coords[1])
        if d:
            temp = int(round(d['current']['temperature_2m']))
            stav = W_DESC.get(d['current']['weathercode'], "Oblačno")
            vítr = d['current']['windspeed_10m']
            with cols[i]:
                st.markdown(f"""
                <div class="weather-card">
                    <div class="city-name">{name}</div>
                    <div class="temp-val">{temp}°C</div>
                    <div class="status-text">{stav}</div>
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 10px;">Vítr: {vítr} km/h</div>
                </div>
                """, unsafe_allow_html=True)

    st.write("---")
    with st.expander("📊 PODROBNÁ TÝDENNÍ PŘEDPOVĚĎ"):
        v = st.selectbox("Vyber město pro detail:", list(mesta.keys()))
        data = get_weather(mesta[v][0], mesta[v][1])
        if data:
            df = pd.DataFrame({
                "Den": [DNY_CZ.get(datetime.strptime(t, "%Y-%m-%d").strftime("%A"), "Neznámo") for t in data['daily']['time']],
                "Stav": [W_DESC.get(c, "Oblačno") for c in data['daily']['weathercode']],
                "Nejvyšší": [f"{int(round(x))}°C" for x in data['daily']['temperature_2m_max']],
                "Nejnižší": [f"{int(round(x))}°C" for x in data['daily']['temperature_2m_min']]
            })
            st.table(df)

    # Rotující zprávy
    news = get_news()
    st.session_state.news_idx = (st.session_state.news_idx + 1) % len(news)
    st.markdown(f'<div class="news-bubble"><b>AKTUÁLNĚ:</b> {news[st.session_state.news_idx]}</div>', unsafe_allow_html=True)
    
    time.sleep(7)
    st.rerun()

# --- CHAT SEKCE ---
else:
    st.markdown(f"<div class='portal-header'><h1>🤖 KVÁDR AI ({st.session_state.ai_model.split('/')[-1]})</h1></div>", unsafe_allow_html=True)
    if st.button("🏠 ZPĚT NA HLAVNÍ STRÁNKU"):
        st.session_state.page = "Domů"
        st.rerun()

    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if p := st.chat_input("Zeptej se na cokoliv..."):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        with st.chat_message("assistant"):
            try:
                mod = genai.GenerativeModel(st.session_state.ai_model)
                resp = mod.generate_content(f"Jsi asistent Kvádr. Odpovídej česky a k věci. Dotaz: {p}").text
                st.markdown(resp)
                st.session_state.msgs.append({"role": "assistant", "content": resp})
            except: st.error("AI má pauzu, zkus to za chvíli.")
