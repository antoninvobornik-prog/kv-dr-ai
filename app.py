import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# =================================================================
# 1. NASTAVENÍ A FUNKCE
# =================================================================
st.set_page_config(page_title="Kvádr 2.0", layout="wide", initial_sidebar_state="collapsed")
st.markdown("<style>section[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)

if "page" not in st.session_state: st.session_state.page = "Domů"
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "news_index" not in st.session_state: st.session_state.news_index = 0

def najdi_model():
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        modely = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for p in ["models/gemini-1.5-flash", "models/gemini-1.5-flash-latest", "models/gemini-pro"]:
            if p in modely: return p
        return modely[0]
    except: return "gemini-1.5-flash"

# =================================================================
# 2. CSS STYLY (OPRAVENO PRO MOBIL A ZPRÁVY)
# =================================================================
st.markdown("""
<style>
    .stApp { background: radial-gradient(circle at center, #1a2c4e 0%, #070b14 100%); color: white; }
    
    /* Kontejner pro počasí - Flexbox pro horizontální scroll */
    .weather-container {
        display: flex;
        flex-direction: row;
        overflow-x: auto;
        gap: 12px;
        padding: 10px 5px;
        white-space: nowrap;
        -webkit-overflow-scrolling: touch; /* Plynulý scroll na iOS */
        scrollbar-width: none; /* Skrytí posuvníku Firefox */
    }
    .weather-container::-webkit-scrollbar { display: none; } /* Skrytí posuvníku Chrome/Safari */
    
    /* Karta počasí */
    .weather-card {
        flex: 0 0 auto; /* Nebude se scvrkávat */
        width: 110px;   /* Pevná šířka pro konzistenci */
        background: rgba(255, 255, 255, 0.08);
        padding: 10px 5px;
        border-radius: 12px;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.15);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    
    .weather-city { font-size: 12px; color: #3b82f6; font-weight: bold; white-space: normal; line-height: 1.1; height: 28px; display: flex; align-items: center; justify-content: center; }
    .weather-temp { font-size: 24px; font-weight: 800; margin: 2px 0; }
    .weather-desc { font-size: 10px; opacity: 0.8; white-space: normal; line-height: 1.1; }

    /* News ticker - POSUNUTO NAHORU (bottom: 70px) */
    .news-ticker {
        position: fixed; 
        bottom: 70px; /* Aby to nebylo pod tlačítky */
        left: 20px; 
        right: 20px;
        width: auto;
        background: rgba(0, 30, 80, 0.95); 
        color: white;
        padding: 12px; 
        text-align: center;
        border-radius: 50px; /* Kulaté rohy vypadají lépe */
        border: 1px solid #3b82f6; 
        font-weight: bold;
        z-index: 9999; 
        font-size: 16px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    
    /* Tlačítka */
    .stButton>button { border-radius: 10px; font-weight: bold; text-transform: uppercase; width: 100%; }
</style>
""", unsafe_allow_html=True)

# =================================================================
# 3. ZÍSKÁNÍ DAT
# =================================================================
def get_desc(c):
    m = {0:"Jasno ☀️",1:"Jasno 🌤️",2:"Polojasno ⛅",3:"Zataženo ☁️",45:"Mlha 🌫️",51:"Mrholení 🌦️",61:"Déšť 🌧️",71:"Sněžení ❄️",80:"Přeháňky 🌧️",95:"Bouřka ⚡"}
    return m.get(c, "")

@st.cache_data(ttl=600)
def get_weather():
    mesta = {"Nové Město": (50.34, 16.15), "Rychnov": (50.16, 16.27), "Bělá": (50.53, 14.80), "Praha": (50.07, 14.43), "Hradec": (50.21, 15.83)}
    res = {}
    for m, (lat, lon) in mesta.items():
        try:
            r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&daily=weathercode,temperature_2m_max,precipitation_probability_max&timezone=auto").json()
            dny = [{"Den":["Po","Út","St","Čt","Pá","So","Ne"][(datetime.now()+timedelta(days=i)).weekday()],"Max":f"{round(r['daily']['temperature_2m_max'][i])}°","Déšť":f"{r['daily']['precipitation_probability_max'][i]}%"} for i in range(7)]
            res[m] = {"akt": f"{round(r['current']['temperature_2m'])}°", "popis": get_desc(r['current']['weathercode']), "tyden": dny}
        except: res[m] = {"akt": "--", "popis": "Chyba", "tyden": []}
    return res

def get_sheet(name):
    try:
        sid = st.secrets["GSHEET_URL"].split("/d/")[1].split("/")[0]
        return pd.read_csv(f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(name)}")
    except: return pd.DataFrame(columns=['zprava'])

# =================================================================
# 4. HLAVNÍ STRÁNKA
# =================================================================
if st.session_state.page == "Domů":
    st.markdown("<h2 style='text-align:center; margin-top:0;'>🏙️ Kvádr Portál 2.0</h2>", unsafe_allow_html=True)
    
    if st.button("💬 OTEVŘÍT AI ASISTENTA 2.0", type="primary"):
        st.session_state.page = "AI Chat"; st.rerun()

    # --- OPRAVENÁ SEKCE POČASÍ (HTML GENEROVÁNÍ) ---
    w = get_weather()
    
    # Budujeme HTML řetězec opatrně
    html_kod = '<div class="weather-container">'
    for mesto, data in w.items():
        # Každá karta je jeden blok stringu
        karta = f"""
        <div class="weather-card">
            <div class="weather-city">{mesto}</div>
            <div class="weather-temp">{data['akt']}</div>
            <div class="weather-desc">{data['popis']}</div>
        </div>
        """
        html_kod += karta
    html_kod += '</div>'
    
    # Vykreslení
    st.markdown(html_kod, unsafe_allow_html=True)
    # -----------------------------------------------

    st.write("---")
    with st.expander("📅 Zobrazit detailní předpověď a srážky"):
        tabs = st.tabs(list(w.keys()))
        for i, m in enumerate(w.keys()):
            with tabs[i]: st.table(pd.DataFrame(w[m]["tyden"]))

    for z in get_sheet("List 2")['zprava'].dropna(): st.info(f"🔔 {z}")

    # RSS Zprávy - Posunuto nahoru v CSS
    try:
        rss = ET.fromstring(requests.get("https://ct24.ceskatelevize.cz/rss/hlavni-zpravy").content)
        msgs = [i.find('title').text for i in rss.findall('.//item')[:10]]
        st.markdown(f'<div class="news-ticker">🗞️ {msgs[st.session_state.news_index % len(msgs)]}</div>', unsafe_allow_html=True)
    except: pass
    
    time.sleep(8)
    st.session_state.news_index += 1
    st.rerun()

# =================================================================
# 5. AI CHAT
# =================================================================
else:
    if st.button("🏠 ZPĚT NA PORTÁL"): st.session_state.page = "Domů"; st.rerun()
    st.markdown("<h3 style='text-align:center;'>💬 Kvádr AI</h3>", unsafe_allow_html=True)
    
    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if p := st.chat_input("Zeptejte se..."):
        st.session_state.chat_history.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        try:
            ctx = " ".join(get_sheet("List 1")['zprava'].astype(str))
            model = genai.GenerativeModel(model_name=najdi_model(), system_instruction=f"Kontext: {ctx}")
            h = [{"role": "user" if x["role"]=="user" else "model", "parts": [x["content"]]} for x in st.session_state.chat_history[:-1]]
            res = model.start_chat(history=h).send_message(p)
            st.session_state.chat_history.append({"role": "assistant", "content": res.text})
            st.rerun()
        except Exception as e: st.error(str(e))
