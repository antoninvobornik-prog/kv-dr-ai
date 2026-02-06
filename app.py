import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# =================================================================
# 1. KONFIGURACE A CHYTRÝ MODEL
# =================================================================
st.set_page_config(
    page_title="Kvádr 2.0", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

if "page" not in st.session_state: st.session_state.page = "Domů"
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "news_index" not in st.session_state: st.session_state.news_index = 0

def najdi_funkcni_model():
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        modely = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for p in ["models/gemini-1.5-flash", "models/gemini-1.5-flash-latest", "models/gemini-pro"]:
            if p in modely: return p
        return modely[0]
    except: return "gemini-1.5-flash"

# =================================================================
# 2. STYLY PRO MOBILNÍ OPTIMALIZACI (ZDE JE TA ZMĚNA)
# =================================================================
st.markdown("""
<style>
    /* Hlavní pozadí */
    .stApp { background: radial-gradient(circle at center, #1a2c4e 0%, #070b14 100%); color: white; }
    
    /* Skrytí menu */
    header {visibility: hidden;}
    section[data-testid='stSidebar'] {display: none;}

    /* Kontejner pro počasí - na mobilu horizontální scroll */
    .weather-container {
        display: flex;
        overflow-x: auto;
        gap: 10px;
        padding: 10px 0;
        -webkit-overflow-scrolling: touch;
    }
    
    /* Karta počasí - kompaktnější a s lepším textem */
    .weather-card {
        min-width: 100px;
        flex: 0 0 auto;
        background: rgba(255, 255, 255, 0.1);
        padding: 12px 8px;
        border-radius: 15px;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .weather-city { font-size: 0.75rem; color: #3b82f6; font-weight: bold; margin-bottom: 2px; }
    .weather-temp { font-size: 1.6rem; font-weight: 800; line-height: 1.1; }
    .weather-desc { font-size: 0.7rem; opacity: 0.9; margin-top: 4px; }

    /* News ticker - větší a čitelnější na mobilu */
    .news-ticker {
        position: fixed; bottom: 0; left: 0; width: 100%;
        background: #002d6e; color: white;
        padding: 20px 10px; text-align: center;
        border-top: 2px solid #3b82f6; font-weight: bold;
        z-index: 9999; font-size: 18px;
        box-shadow: 0 -5px 15px rgba(0,0,0,0.5);
    }

    /* Úprava expanderu pro mobil */
    .stExpander { border: 1px solid rgba(255,255,255,0.1) !important; background: transparent !important; }
    
    /* Tlačítka */
    .stButton>button { 
        border-radius: 12px !important; 
        padding: 15px !important; 
        font-weight: bold !important;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)

# =================================================================
# 3. DATA
# =================================================================
def get_weather_desc(code):
    mapping = {0: "Jasno ☀️", 1: "Jasno 🌤️", 2: "Polojasno ⛅", 3: "Zataženo ☁️", 45: "Mlha 🌫️", 51: "Mrholení 🌦️", 61: "Déšť 🌧️", 71: "Sněžení ❄️", 80: "Přeháňky 🌧️", 95: "Bouřka ⚡"}
    return mapping.get(code, f"Kód {code}")

@st.cache_data(ttl=600)
def nacti_kompletni_pocasi():
    mesta = {"Nové Město": (50.34, 16.15), "Rychnov": (50.16, 16.27), "Bělá": (50.53, 14.80), "Praha": (50.07, 14.43), "Hradec": (50.21, 15.83)}
    res = {}
    for m, (lat, lon) in mesta.items():
        try:
            r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto").json()
            dny = []
            for i in range(7):
                d_obj = datetime.now() + timedelta(days=i)
                dny.append({"Den": ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"][d_obj.weekday()], "Max": f"{round(r['daily']['temperature_2m_max'][i])}°", "Déšť": f"{r['daily']['precipitation_probability_max'][i]}%"})
            res[m] = {"akt": f"{round(r['current']['temperature_2m'])}°", "popis": get_weather_desc(r['current']['weathercode']), "tyden": dny}
        except: res[m] = {"akt": "??", "popis": "Chyba", "tyden": []}
    return res

def nacti_gsheets(list_name):
    try:
        sid = st.secrets["GSHEET_URL"].split("/d/")[1].split("/")[0]
        url = f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(list_name)}"
        return pd.read_csv(url)
    except: return pd.DataFrame(columns=['zprava'])

# =================================================================
# 4. PORTÁL - DOMŮ
# =================================================================
if st.session_state.page == "Domů":
    st.markdown("<h2 style='text-align:center; margin-bottom:20px;'>🏙️ Kvádr Portál 2.0</h2>", unsafe_allow_html=True)
    
    # Navigace
    if st.button("💬 OTEVŘÍT AI ASISTENTA 2.0", use_container_width=True, type="primary"):
        st.session_state.page = "AI Chat"; st.rerun()

    # Počasí - Horizontální scroll pro mobil
    w_data = nacti_kompletni_pocasi()
    weather_html = '<div class="weather-container">'
    for mesto, d in w_data.items():
        weather_html += f"""
        <div class="weather-card">
            <div class="weather-city">{mesto}</div>
            <div class="weather-temp">{d['akt']}</div>
            <div class="weather-desc">{d['popis']}</div>
        </div>
        """
    weather_html += '</div>'
    st.markdown(weather_html, unsafe_allow_html=True)
    
    st.write("---")
    
    with st.expander("📅 Zobrazit detailní předpověď a srážky"):
        ts = st.tabs(list(w_data.keys()))
        for i, m in enumerate(w_data.keys()):
            with ts[i]: st.table(pd.DataFrame(w_data[m]["tyden"]))

    # Oznámení
    df_ozn = nacti_gsheets("List 2")
    for z in df_ozn['zprava'].dropna():
        st.info(f"🔔 {z}")

    # RSS Zprávy
    try:
        rss = ET.fromstring(requests.get("https://ct24.ceskatelevize.cz/rss/hlavni-zpravy").content)
        zpravy = [i.find('title').text for i in rss.findall('.//item')[:10]]
        idx = st.session_state.news_index % len(zpravy)
        st.markdown(f'<div class="news-ticker">🗞️ {zpravy[idx]}</div>', unsafe_allow_html=True)
    except: pass

    time.sleep(8)
    st.session_state.news_index += 1
    st.rerun()

# =================================================================
# 5. AI CHAT
# =================================================================
else:
    if st.button("🏠 ZPĚT NA PORTÁL", use_container_width=True):
        st.session_state.page = "Domů"; st.rerun()
        
    m_name = najdi_funkcni_model()
    st.markdown(f"<h3 style='text-align:center;'>💬 Kvádr AI</h3>", unsafe_allow_html=True)
    
    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if pr := st.chat_input("Zeptejte se..."):
        st.session_state.chat_history.append({"role": "user", "content": pr})
        with st.chat_message("user"): st.markdown(pr)
        with st.chat_message("assistant"):
            try:
                ctx = " ".join(nacti_gsheets("List 1")['zprava'].astype(str))
                model = genai.GenerativeModel(model_name=m_name, system_instruction=f"Jsi asistent Kvádru. Kontext: {ctx}")
                hist = [{"role": "user" if h["role"]=="user" else "model", "parts": [h["content"]]} for h in st.session_state.chat_history[:-1]]
                res = model.start_chat(history=hist).send_message(pr)
                st.markdown(res.text)
                st.session_state.chat_history.append({"role": "assistant", "content": res.text})
                st.rerun()
            except Exception as e: st.error(f"AI Error: {e}")
