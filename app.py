import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import streamlit.components.v1 as components

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

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap');
    
    section[data-testid="stSidebar"] {display: none;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .stApp {
        background: radial-gradient(circle at top, #0a192f 0%, #020617 100%);
        color: #e2e8f0;
        font-family: 'Rajdhani', sans-serif;
    }

    /* Hlavní nadpis 2.0 */
    .portal-header {
        text-align: center;
        padding: 20px;
        background: linear-gradient(90deg, rgba(0,0,0,0) 0%, rgba(30,58,138,0.5) 50%, rgba(0,0,0,0) 100%);
        border-bottom: 2px solid #3b82f6;
        margin-bottom: 25px;
    }
    .portal-header h1 {
        color: #ffffff;
        text-transform: uppercase;
        letter-spacing: 4px;
        margin: 0;
        font-size: 2.2rem;
        text-shadow: 0 0 10px #3b82f6;
    }

    /* Weather Cards - MAXIMÁLNÍ KONTRAST */
    .weather-card {
        background: #1e3a8a;
        border: 2px solid #3b82f6;
        border-radius: 15px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    .weather-temp {
        font-size: 32px;
        font-weight: 800;
        color: #ffffff !important;
        margin: 5px 0;
    }
    .weather-city {
        color: #93c5fd;
        font-weight: bold;
        font-size: 13px;
        text-transform: uppercase;
    }

    /* Modrá bublina pro zprávy v jednom řádku */
    .news-bubble {
        position: fixed;
        bottom: 55px;
        left: 20px;
        right: 20px;
        background: #2563eb;
        color: white;
        padding: 12px 25px;
        border-radius: 50px;
        border: 2px solid #60a5fa;
        z-index: 1000;
        text-align: center;
        font-weight: 600;
        font-size: 16px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }

    /* Design tlačítek */
    .stButton>button {
        background: #dc2626;
        color: white;
        border-radius: 10px;
        border: none;
        padding: 15px;
        font-weight: bold;
        width: 100%;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)

# =================================================================
# 2. LOGIKA POČASÍ A ZPRÁV
# =================================================================
def get_weather(lat, lon):
    try:
        r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&timezone=auto", timeout=3).json()
        return round(r['current']['temperature_2m']), r['current']['weathercode']
    except: return "--", 0

def get_news_text():
    try:
        rss = ET.fromstring(requests.get("https://ct24.ceskatelevize.cz/rss/hlavni-zpravy", timeout=3).content)
        return rss.find('.//item/title').text
    except: return "Aktuálně nejsou k dispozici žádné nové zprávy."

# =================================================================
# 3. STRÁNKY
# =================================================================
if "page" not in st.session_state: st.session_state.page = "Domů"

# --- DOMOVSKÁ STRÁNKA ---
if st.session_state.page == "Domů":
    st.markdown('<div class="portal-header"><h1>KVÁDR PORTÁL 2.0</h1></div>', unsafe_allow_html=True)

    if st.button("💬 OTEVŘÍT AI CHAT"):
        st.session_state.page = "Chat"
        st.rerun()

    st.write("")
    
    # Karty měst
    mesta = {"Nové Město": (50.34, 16.15), "Rychnov": (50.16, 16.27), "Bělá": (50.76, 15.05), "Praha": (50.07, 14.43)}
    cols = st.columns(4)
    icons = {0:"☀️", 1:"🌤️", 2:"⛅", 3:"☁️", 45:"🌫️", 61:"🌧️", 95:"⚡"}
    
    for i, (name, coords) in enumerate(mesta.items()):
        temp, code = get_weather(coords[0], coords[1])
        with cols[i]:
            st.markdown(f"""
                <div class="weather-card">
                    <div class="weather-city">{name}</div>
                    <div class="weather-temp">{temp}°</div>
                    <div style="font-size: 20px;">{icons.get(code, "🌡️")}</div>
                </div>
            """, unsafe_allow_html=True)

    st.write("")
    with st.expander("📊 PODROBNÁ PŘEDPOVĚĎ"):
        vyber = st.selectbox("Vyberte město:", list(mesta.keys()))
        l1, l2 = mesta[vyber]
        try:
            res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={l1}&longitude={l2}&daily=temperature_2m_max,temperature_2m_min&timezone=auto").json()
            df = pd.DataFrame({"Datum": [datetime.strptime(d, "%Y-%m-%d").strftime("%d.%m.") for d in res['daily']['time']],
                               "Max (°C)": res['daily']['temperature_2m_max'], "Min (°C)": res['daily']['temperature_2m_min']})
            st.table(df)
        except: st.error("Data nedostupná.")

    # OZNÁMENÍ
    st.markdown("### 📌 OZNÁMENÍ")
    try:
        sheet_url = f"https://docs.google.com/spreadsheets/d/{st.secrets['GSHEET_URL'].split('/d/')[1].split('/')[0]}/gviz/tq?tqx=out:csv&sheet=List%202"
        df_n = pd.read_csv(sheet_url).dropna()
        for msg in df_n['zprava']: st.info(f"**{msg}**")
    except: st.write("Žádná nová oznámení.")

    # MODRÁ BUBLINA ZPRÁV
    st.markdown(f'<div class="news-bubble">ZPRÁVY: {get_news_text()}</div>', unsafe_allow_html=True)

# --- CHAT STRÁNKA ---
else:
    st.markdown("<h2 style='text-align: center; color: #3b82f6;'>🤖 KVÁDR AI</h2>", unsafe_allow_html=True)
    if st.button("🏠 ZPĚT NA PORTÁL"):
        st.session_state.page = "Domů"
        st.rerun()

    if "messages" not in st.session_state: st.session_state.messages = []
    
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Zeptejte se na cokoliv..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        with st.chat_message("assistant"):
            try:
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(f"Jsi asistent portálu Kvádr. Odpověz česky: {prompt}")
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except: st.write("AI je momentálně nedostupná.")
