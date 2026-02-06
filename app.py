import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# =================================================================
# 1. KONFIGURACE A STAV
# =================================================================
st.set_page_config(
    page_title="Kvádr Portál 2.1", 
    layout="wide", 
    page_icon="🏙️", 
    initial_sidebar_state="collapsed"
)

st.markdown("<style>section[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)

if "page" not in st.session_state: st.session_state.page = "Domů"
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "news_index" not in st.session_state: st.session_state.news_index = 0
if "cache_zpravy" not in st.session_state: st.session_state.cache_zpravy = []
if "posledni_update_zprav" not in st.session_state: st.session_state.posledni_update_zprav = 0

try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    if "model_name" not in st.session_state: st.session_state.model_name = "gemini-1.5-flash"
except Exception as e:
    st.error(f"AI Error: {e}")

# =================================================================
# 2. FUNKCE
# =================================================================

def get_weather_desc(code):
    mapping = {
        0: "Jasno ☀️", 1: "Převážně jasno 🌤️", 2: "Polojasno ⛅", 3: "Zataženo ☁️",
        45: "Mlha 🌫️", 48: "Námraza 🌫️", 51: "Mírné mrholení 🌦️", 53: "Mrholení 🌦️", 
        55: "Silné mrholení 🌧️", 61: "Slabý déšť 🌧️", 63: "Déšť 🌧️", 65: "Silný déšť 🌊",
        66: "Mrznoucí déšť 🧊", 80: "Slabé přeháňky 🌦️", 81: "Přeháňky 🌧️", 82: "Silné přeháňky 🌊",
        95: "Bouřka ⚡", 96: "Bouřka s kroupami ⛈️"
    }
    return mapping.get(code, f"Neznámé ({code})")

@st.cache_data(ttl=600)
def nacti_kompletni_pocasi():
    mesta = {
        "Nové Město n. M.": (50.344, 16.151), 
        "Rychnov n. Kn.": (50.162, 16.274),
        "Bělá": (50.534, 14.807), 
        "Praha": (50.075, 14.437), 
        "Hradec Králové": (50.210, 15.832)
    }
    dny_cz = ["Pondělí", "Úterý", "Středa", "Čtvrtek", "Pátek", "Sobota", "Neděle"]
    vysledek = {}
    for m, (lat, lon) in mesta.items():
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto"
            r = requests.get(url, timeout=5).json()
            pred = []
            for i in range(7):
                d_obj = datetime.now() + timedelta(days=i)
                pred.append({"Den": dny_cz[d_obj.weekday()], "Stav": get_weather_desc(r['daily']['weathercode'][i]), "Max": f"{round(r['daily']['temperature_2m_max'][i])}°C", "Déšť": f"{r['daily']['precipitation_probability_max'][i]}%"})
            vysledek[m] = {"aktualni": f"{round(r['current']['temperature_2m'])}°C", "popis": get_weather_desc(r['current']['weathercode']), "tyden": pred}
        except: vysledek[m] = {"aktualni": "??", "popis": "Chyba", "tyden": []}
    return vysledek

def nacti_zpravy():
    ted = time.time()
    if st.session_state.cache_zpravy and (ted - st.session_state.posledni_update_zprav < 600):
        return st.session_state.cache_zpravy
    zdroje = [("ČT24", "https://ct24.ceskatelevize.cz/rss/hlavni-zpravy"), ("Seznam", "https://www.seznamzpravy.cz/rss")]
    vystup = []
    for label, url in zdroje:
        try:
            r = requests.get(url, timeout=4)
            root = ET.fromstring(r.content)
            for item in root.findall('.//item')[:10]: vystup.append(f"{label}: {item.find('title').text}")
        except: continue
    if vystup:
        st.session_state.cache_zpravy, st.session_state.posledni_update_zprav = vystup, ted
        return vystup
    return ["Načítám zprávy..."]

def nacti_sheets(list_name):
    try:
        url = st.secrets["GSHEET_URL"]
        sheet_id = url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(list_name)}"
        return pd.read_csv(csv_url)
    except: return pd.DataFrame(columns=['zprava'])

# =================================================================
# 3. DESIGN
# =================================================================
st.markdown("""
<style>
    .stApp { background: radial-gradient(circle at center, #1a2c4e 0%, #070b14 100%); color: white; }
    .news-ticker { position: fixed; bottom: 0; left: 0; width: 100%; background: rgba(0, 45, 110, 0.98); color: white; padding: 15px; text-align: center; border-top: 3px solid #3b82f6; z-index: 9999; font-size: 19px; font-weight: bold; }
    .weather-card { background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 12px; text-align: center; border: 1px solid rgba(255,255,255,0.1); }
</style>
""", unsafe_allow_html=True)

# =================================================================
# 4. OBSAH
# =================================================================
nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
with nav_col2:
    if st.session_state.page == "Domů":
        if st.button("💬 OTEVŘÍT AI ASISTENTA 2.0", use_container_width=True, type="primary"): st.session_state.page = "AI Chat"; st.rerun()
    else:
        if st.button("🏠 ZPĚT NA HLAVNÍ PORTÁL", use_container_width=True): st.session_state.page = "Domů"; st.rerun()

if st.session_state.page == "Domů":
    st.markdown("<h1 style='text-align:center;'>🏙️ Kvádr Portál 2.1</h1>", unsafe_allow_html=True)
    
    w_data = nacti_kompletni_pocasi()
    cols = st.columns(len(w_data))
    for i, (mesto, d) in enumerate(w_data.items()):
        cols[i].markdown(f"<div class='weather-card'><div style='color:#3b82f6;font-size:0.8em;'>{mesto}</div><div style='font-size:1.8em;font-weight:bold;'>{d['aktualni']}</div><div style='font-size:0.8em;'>{d['popis']}</div></div>", unsafe_allow_html=True)
    
    st.write("##")
    with st.expander("📅 Detailní týdenní předpověď"):
        tabs = st.tabs(list(w_data.keys()))
        for i, (mesto, d) in enumerate(w_data.items()):
            with tabs[i]: 
                if d["tyden"]: st.table(pd.DataFrame(d["tyden"]))
    
    df_ozn = nacti_sheets("List 2")
    if not df_ozn.empty:
        for z in df_ozn['zprava'].dropna(): st.info(z)

    zpravy = nacti_zpravy()
    idx = st.session_state.news_index % len(zpravy)
    st.markdown(f'<div class="news-ticker">🗞️ {zpravy[idx]}</div>', unsafe_allow_html=True)
    time.sleep(5)
    st.session_state.news_index += 1
    st.rerun()

elif st.session_state.page == "AI Chat":
    st.markdown("<h1 style='text-align:center;'>💬 Kvádr AI 2.0</h1>", unsafe_allow_html=True)
    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Zeptejte se..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Přemýšlím..."):
                df_c = nacti_sheets("List 1")
                kontext = " ".join(df_c['zprava'].astype(str).tolist())
                model = genai.GenerativeModel(st.session_state.model_name, system_instruction=f"Jsi asistent Kvádru. Kontext: {kontext}")
                hist = [{"role": "user" if h["role"]=="user" else "model", "parts": [h["content"]]} for h in st.session_state.chat_history[:-1]]
                res = model.start_chat(history=hist).send_message(prompt)
                st.markdown(res.text)
                st.session_state.chat_history.append({"role": "assistant", "content": res.text})
                st.rerun()
