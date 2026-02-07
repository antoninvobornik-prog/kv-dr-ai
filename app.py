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
    
    .stButton>button {
        background: linear-gradient(45deg, #ef4444, #dc2626) !important;
        color: white !important;
        font-size: 28px !important;
        font-weight: 800 !important;
        height: 90px !important;
        border-radius: 20px !important;
        border: 4px solid white !important;
        box-shadow: 0 0 30px rgba(239, 68, 68, 0.7) !important;
        text-transform: uppercase;
        animation: pulse 2s infinite;
    }
    @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.02); } 100% { transform: scale(1); } }

    .weather-card { background: #1e293b; border: 1px solid #3b82f6; border-radius: 12px; padding: 10px; text-align: center; }
    .city-name { color: #60a5fa; font-size: 1.1rem; font-weight: bold; }
    .temp-val { font-size: 2rem; font-weight: 800; color: white; }

    .news-bubble {
        position: fixed; bottom: 80px; left: 5%; right: 5%;
        background: #2563eb; color: white; padding: 15px;
        border-radius: 40px; text-align: center; z-index: 9999;
        font-size: 1.2rem; font-weight: 700; border: 2px solid white;
    }
</style>
""", unsafe_allow_html=True)

DNY_CZ = {"Monday":"Pondělí","Tuesday":"Úterý","Wednesday":"Středa","Thursday":"Čtvrtek","Friday":"Pátek","Saturday":"Sobota","Sunday":"Neděle"}
W_DESC = {0:"Jasno ☀️", 1:"Skoro jasno 🌤️", 2:"Polojasno ⛅", 3:"Zataženo ☁️", 45:"Mlha 🌫️", 61:"Déšť 🌧️", 95:"Bouřka ⚡"}

@st.cache_data(ttl=600)
def get_weather_full(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=auto"
        return requests.get(url).json()
    except: return None

# --- HLAVNÍ STRÁNKA ---
if "page" not in st.session_state: st.session_state.page = "Domů"

if st.session_state.page == "Domů":
    st.markdown('<div class="portal-header"><h1>KVÁDR PORTÁL 2.0</h1></div>', unsafe_allow_html=True)

    # 1. LIST 2 OZNÁMENÍ
    try:
        sheet_id = st.secrets["GSHEET_URL"].split("/d/")[1].split("/")[0]
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=List%202"
        oznameni = pd.read_csv(url).dropna(subset=['zprava'])
        for msg in oznameni['zprava']:
            st.info(f"📢 {msg}")
    except: pass

    # 2. MEGA TLAČÍTKO
    if st.button("🔥 OTEVŘÍT KVÁDR AI ASISTENTA 🔥", use_container_width=True):
        st.session_state.page = "Chat"
        st.rerun()

    # 3. POČASÍ + PŘEDPOVĚĎ
    st.write("### 🌍 AKTUÁLNÍ POČASÍ A PŘEDPOVĚĎ")
    mesta = {"Nové Město": (50.34, 16.15), "Rychnov": (50.16, 16.27), "Bělá": (50.76, 15.05), "Praha": (50.07, 14.43)}
    
    cols = st.columns(4)
    weather_data = {}
    for i, (name, coords) in enumerate(mesta.items()):
        d = get_weather_full(coords[0], coords[1])
        weather_data[name] = d
        if d:
            t = int(round(d['current']['temperature_2m']))
            s = W_DESC.get(d['current']['weathercode'], "Oblačno")
            with cols[i]:
                # TADY BYLA TA CHYBA - OPRAVENO:
                st.markdown(f'<div class="weather-card"><div class="city-name">{name}</div><div class="temp-val">{t}°C</div><div style="color:#94a3b8;">{s}</div></div>', unsafe_allow_html=True)

    with st.expander("📅 ZOBRAZIT TÝDENNÍ PŘEDPOVĚĎ (DETAIL)"):
        volba = st.selectbox("Vyber město:", list(mesta.keys()))
        detaily = weather_data.get(volba)
        if detaily:
            df = pd.DataFrame({
                "Den": [DNY_CZ.get(datetime.strptime(t, "%Y-%m-%d").strftime("%A"), t) for t in detaily['daily']['time']],
                "Stav": [W_DESC.get(c, "Oblačno") for c in detaily['daily']['weathercode']],
                "Max": [f"{int(round(x))}°C" for x in detaily['daily']['temperature_2m_max']],
                "Min": [f"{int(round(x))}°C" for x in detaily['daily']['temperature_2m_min']]
            })
            st.table(df)

    # 4. ZPRÁVY
    try:
        r = requests.get("https://ct24.ceskatelevize.cz/rss/hlavni-zpravy")
        news = [item.find('title').text for item in ET.fromstring(r.content).findall('.//item')]
        if "news_idx" not in st.session_state: st.session_state.news_idx = 0
        st.session_state.news_idx = (st.session_state.news_idx + 1) % len(news)
        st.markdown(f'<div class="news-bubble">AKTUALITA: {news[st.session_state.news_idx]}</div>', unsafe_allow_html=True)
    except: pass
    
    time.sleep(10)
    st.rerun()

else:
    # --- CHAT ---
    st.markdown("<div class='portal-header'><h1>🤖 KVÁDR MOZEK AI</h1></div>", unsafe_allow_html=True)
    if st.button("⬅️ ZPĚT"):
        st.session_state.page = "Domů"
        st.rerun()

    if "msgs" not in st.session_state:
        st.session_state.msgs = [{"role": "assistant", "content": "Zdravím! Jsem Kvádr mozek, tvůj osobní asistent. Jak ti můžu pomoci?"}]

    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if p := st.chat_input("Zeptej se..."):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        with st.chat_message("assistant"):
            try:
                mod = genai.GenerativeModel(st.session_state.ai_model)
                res = mod.generate_content(f"Jsi Kvádr mozek, mluv česky. Dotaz: {p}").text
                st.markdown(res)
                st.session_state.msgs.append({"role": "assistant", "content": res})
            except: st.error("Chyba AI.")
