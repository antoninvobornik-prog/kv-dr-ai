import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import time

# =================================================================
# 1. HLAVNÍ KONFIGURACE A STYLOVÁNÍ (CSS MAGIE)
# =================================================================
st.set_page_config(
    page_title="KVÁDR PORTÁL 2.0",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Nastavení Google Gemini s automatickým výběrem modelu
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    if "ai_model" not in st.session_state:
        try:
            # Dynamicky najde nejlepší model (Flash/Pro) podle toho, co máš povolené
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            st.session_state.ai_model = next((m for m in models if "1.5-flash" in m), models[0])
        except:
            st.session_state.ai_model = "models/gemini-1.5-flash"

# Komplexní stylování portálu
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Roboto+Mono&display=swap');
    
    /* Globální nastavení */
    section[data-testid="stSidebar"] {display: none;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .stApp {
        background: radial-gradient(circle at top, #0f172a, #020617);
        color: #f8fafc;
        font-family: 'Rajdhani', sans-serif;
    }

    /* Hlavička portálu */
    .portal-header {
        text-align: center;
        padding: 30px;
        background: linear-gradient(90deg, #1e3a8a, #3b82f6, #1e3a8a);
        border-bottom: 4px solid #60a5fa;
        margin-bottom: 30px;
        border-radius: 0 0 30px 30px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    .portal-header h1 {
        font-size: 3.5rem;
        text-transform: uppercase;
        letter-spacing: 5px;
        margin: 0;
        color: white;
        text-shadow: 3px 3px 0px #1d4ed8;
    }

    /* Weather Cards */
    .weather-container {
        display: flex;
        gap: 20px;
        justify-content: space-around;
        margin-bottom: 30px;
    }
    .weather-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(10px);
        border: 2px solid #3b82f6;
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        flex: 1;
        transition: transform 0.3s ease;
    }
    .weather-card:hover { transform: translateY(-5px); border-color: #60a5fa; }
    .city-name { color: #93c5fd; font-weight: 700; font-size: 1.2rem; text-transform: uppercase; }
    .temp-main { font-size: 3rem; font-weight: 800; color: white; margin: 10px 0; }
    
    /* Bublina se zprávami (FIXNÍ DOLE) */
    .news-bubble {
        position: fixed;
        bottom: 40px;
        left: 50%;
        transform: translateX(-50%);
        width: 85%;
        background: #2563eb;
        color: white;
        padding: 15px 30px;
        border-radius: 100px;
        border: 3px solid #93c5fd;
        z-index: 9999;
        text-align: center;
        font-weight: 600;
        font-size: 1.2rem;
        box-shadow: 0 15px 40px rgba(0,0,0,0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        animation: slideUp 0.5s ease-out;
    }
    @keyframes slideUp { from { bottom: -100px; } to { bottom: 40px; } }

    /* AI Chat styling */
    .stChatMessage { border-radius: 20px !important; border: 1px solid #334155 !important; background: #1e293b !important; }
    .stChatInputContainer { padding-bottom: 120px !important; }
</style>
""", unsafe_allow_html=True)

# =================================================================
# 2. LOGIKA DATA A CACHE
# =================================================================

@st.cache_data(ttl=600) # POČASÍ: 10 MINUT CACHE
def fetch_weather_data(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=auto"
        return requests.get(url, timeout=5).json()
    except: return None

@st.cache_data(ttl=300) # ZPRÁVY: 5 MINUT CACHE
def fetch_news():
    try:
        r = requests.get("https://ct24.ceskatelevize.cz/rss/hlavni-zpravy", timeout=5)
        root = ET.fromstring(r.content)
        return [item.find('title').text for item in root.findall('.//item')]
    except: return ["Zpravodajství je momentálně nedostupné."]

WEATHER_DESC = {0: "Jasno ☀️", 1: "Skoro jasno 🌤️", 2: "Polojasno ⛅", 3: "Zataženo ☁️", 45: "Mlha 🌫️", 61: "Déšť 🌧️", 95: "Bouřka ⚡"}

# =================================================================
# 3. NAVIGACE A STAV
# =================================================================
if "page" not in st.session_state: st.session_state.page = "Domů"
if "news_idx" not in st.session_state: st.session_state.news_idx = 0
if "last_refresh" not in st.session_state: st.session_state.last_refresh = time.time()

# --- HLAVNÍ STRÁNKA ---
if st.session_state.page == "Domů":
    st.markdown('<div class="portal-header"><h1>KVÁDR PORTÁL 2.0</h1></div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🚀 OTEVŘÍT INTERAKTIVNÍ AI CHAT", use_container_width=True):
            st.session_state.page = "Chat"
            st.rerun()

    st.write("### 🌍 AKTUÁLNÍ PŘEHLED")
    
    mesta = {
        "Nové Město": (50.34, 16.15),
        "Rychnov": (50.16, 16.27),
        "Bělá": (50.76, 15.05),
        "Praha": (50.07, 14.43)
    }
    
    cols = st.columns(len(mesta))
    for i, (name, coords) in enumerate(mesta.items()):
        w_data = fetch_weather_data(coords[0], coords[1])
        if w_data:
            temp = int(round(w_data['current']['temperature_2m']))
            code = w_data['current']['weathercode']
            desc = WEATHER_DESC.get(code, "Oblačno")
            with cols[i]:
                st.markdown(f"""
                <div class="weather-card">
                    <div class="city-name">{name}</div>
                    <div class="temp-main">{temp}°C</div>
                    <div class="desc">{desc}</div>
                </div>
                """, unsafe_allow_html=True)

    st.write("---")
    
    # Detailní tabulka s předpovědí
    with st.expander("📅 TÝDENNÍ PŘEDPOVĚĎ A DETAILY"):
        target = st.selectbox("Vyber lokalitu:", list(mesta.keys()))
        d = fetch_weather_data(mesta[target][0], mesta[target][1])
        if d:
            df = pd.DataFrame({
                "Den": [datetime.strptime(t, "%Y-%m-%d").strftime("%A %d.%m.") for t in d['daily']['time']],
                "Max": [f"{int(round(x))}°C" for x in d['daily']['temperature_2m_max']],
                "Min": [f"{int(round(x))}°C" for x in d['daily']['temperature_2m_min']],
                "Stav": [WEATHER_DESC.get(c, "Oblačno") for c in d['daily']['weathercode']]
            })
            st.dataframe(df, use_container_width=True, hide_index=True)

    # Zprávy - Rotace každých 7 sekund
    news_list = fetch_news()
    current_news = news_list[st.session_state.news_idx]
    
    st.markdown(f"""
    <div class="news-bubble">
        <span style="color: #bfdbfe; margin-right: 15px;">● LIVE ZPRÁVY:</span> 
        {current_news}
    </div>
    """, unsafe_allow_html=True)

    # Automatická obnova
    time.sleep(7)
    st.session_state.news_idx = (st.session_state.news_idx + 1) % len(news_list)
    st.rerun()

# --- STRÁNKA CHATU ---
else:
    st.markdown(f"<div class='portal-header'><h1>🤖 AI ASISTENT ({st.session_state.ai_model.split('/')[-1]})</h1></div>", unsafe_allow_html=True)
    
    if st.button("⬅️ ZPĚT NA HLAVNÍ PANEL"):
        st.session_state.page = "Domů"
        st.rerun()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Kontejner pro zobrazení zpráv
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Napište svůj dotaz pro Kvádr AI..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                # Použití dynamicky vybraného modelu
                model = genai.GenerativeModel(st.session_state.ai_model)
                full_query = f"Jsi inteligentní mozek portálu Kvádr. Odpovídej k věci a česky. Dotaz: {prompt}"
                response = model.generate_content(full_query)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error("Omlouvám se, ale moje neurální síť je momentálně přetížena. Zkus to prosím za chvilku.")
