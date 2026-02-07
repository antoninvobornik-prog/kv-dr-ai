import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# =================================================================
# 1. KONFIGURACE A STYLOVÁNÍ
# =================================================================
st.set_page_config(
    page_title="KVÁDR PORTÁL 2.1",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Nastavení Gemini API
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Převodník kódů na text a ikony
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

    /* Nadpis 2.0/2.1 */
    .portal-header {
        text-align: center;
        padding: 15px;
        background: #1e3a8a;
        border-bottom: 3px solid #3b82f6;
        margin-bottom: 20px;
        border-radius: 0 0 20px 20px;
    }
    .portal-header h1 {
        color: white;
        text-transform: uppercase;
        letter-spacing: 3px;
        margin: 0;
    }

    /* Weather Cards */
    .weather-card {
        background: #1e293b;
        border: 2px solid #3b82f6;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        transition: 0.3s;
    }
    .weather-temp {
        font-size: 36px;
        font-weight: 800;
        color: #ffffff !important;
        margin: 5px 0;
    }
    .weather-city {
        color: #60a5fa;
        font-weight: bold;
        text-transform: uppercase;
    }

    /* Modrá bublina zpráv - JEDEN ŘÁDEK */
    .news-bubble {
        position: fixed;
        bottom: 55px;
        left: 20px;
        right: 20px;
        background: #2563eb;
        color: white;
        padding: 12px 25px;
        border-radius: 50px;
        border: 2px solid #93c5fd;
        z-index: 1000;
        text-align: center;
        font-weight: 600;
        font-size: 15px;
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
        box-shadow: 0 8px 20px rgba(0,0,0,0.5);
    }

    /* Červené tlačítko */
    .stButton>button {
        background: #e11d48;
        color: white;
        border-radius: 10px;
        border: none;
        padding: 15px;
        font-weight: bold;
        width: 100%;
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

# =================================================================
# 2. POMOCNÉ FUNKCE
# =================================================================
def get_weather_data(lat, lon):
    try:
        r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=auto", timeout=3).json()
        return r
    except: return None

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
    
    # Města a souřadnice
    mesta = {
        "Nové Město": (50.34, 16.15),
        "Rychnov": (50.16, 16.27),
        "Bělá": (50.76, 15.05),
        "Praha": (50.07, 14.43)
    }
    
    cols = st.columns(4)
    for i, (name, coords) in enumerate(mesta.items()):
        data = get_weather_data(coords[0], coords[1])
        if data:
            temp = round(data['current']['temperature_2m'])
            code = data['current']['weathercode']
            stav, icon = WEATHER_MAP.get(code, ("Neznámé", "🌡️"))
            with cols[i]:
                st.markdown(f"""
                    <div class="weather-card">
                        <div class="weather-city">{name}</div>
                        <div class="weather-temp">{temp}°</div>
                        <div style="font-size: 20px;">{icon} {stav}</div>
                    </div>
                """, unsafe_allow_html=True)

    st.write("")
    
    # DETAILNÍ PŘEDPOVĚĎ
    with st.expander("📊 DETAILNÍ PŘEDPOVĚĎ A STAV POČASÍ"):
        vyber = st.selectbox("Vyberte město pro tabulku:", list(mesta.keys()))
        l1, l2 = mesta[vyber]
        data = get_weather_data(l1, l2)
        if data:
            daily = data['daily']
            df = pd.DataFrame({
                "Datum": [datetime.strptime(d, "%Y-%m-%d").strftime("%d.%m.") for d in daily['time']],
                "Stav": [WEATHER_MAP.get(c, ("Neznámé", "🌡️"))[0] for c in daily['weathercode']],
                "Max (°C)": [int(round(t)) for t in daily['temperature_2m_max']],
                "Min (°C)": [int(round(t)) for t in daily['temperature_2m_min']]
            })
            st.table(df) # st.table vypadá v tmavém režimu lépe pro statický text
        else:
            st.error("Nepodařilo se načíst data.")

    # OZNÁMENÍ
    st.markdown("### 📌 OZNÁMENÍ")
    try:
        sheet_id = st.secrets["GSHEET_URL"].split("/d/")[1].split("/")[0]
        sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=List%202"
        df_n = pd.read_csv(sheet_url).dropna()
        for msg in df_n['zprava']:
            st.info(f"**{msg}**")
    except:
        st.write("Aktuálně žádná nová oznámení.")

    # ZPRÁVY - JEDEN ŘÁDEK
    try:
        rss = ET.fromstring(requests.get("https://ct24.ceskatelevize.cz/rss/hlavni-zpravy", timeout=3).content)
        msg = rss.find('.//item/title').text
    except:
        msg = "Zpravodajství je momentálně nedostupné."
    
    st.markdown(f'<div class="news-bubble">ZPRÁVY: {msg}</div>', unsafe_allow_html=True)

# --- CHAT STRÁNKA ---
else:
    st.markdown("<h2 style='text-align: center; color: #60a5fa;'>🤖 KVÁDR AI</h2>", unsafe_allow_html=True)
    if st.button("🏠 ZPĚT NA HLAVNÍ PORTÁL"):
        st.session_state.page = "Domů"
        st.rerun()

    if "messages" not in st.session_state: st.session_state.messages = []
    
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Zeptejte se mě na cokoliv..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        with st.chat_message("assistant"):
            try:
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(f"Jsi asistent portálu Kvádr. Odpověz česky a stručně: {prompt}")
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except:
                st.write("Omlouvám se, ale AI teď odpočívá. Zkuste to za chvíli.")
