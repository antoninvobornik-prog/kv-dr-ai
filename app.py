import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# 1. NASTAVENÍ A CHYTRÝ VÝBĚR MODELU
st.set_page_config(page_title="Kvádr Portál 2.0", layout="wide", page_icon="🏙️", initial_sidebar_state="collapsed")
st.markdown("<style>section[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)

if "page" not in st.session_state: st.session_state.page = "Domů"
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "news_index" not in st.session_state: st.session_state.news_index = 0
if "active_model" not in st.session_state: st.session_state.active_model = None

def najdi_funkcni_model():
    if st.session_state.active_model: return st.session_state.active_model
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        dostupne = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority = ["models/gemini-1.5-flash", "models/gemini-1.5-flash-latest", "models/gemini-pro"]
        for p in priority:
            if p in dostupne:
                st.session_state.active_model = p
                return p
        return dostupne[0] if dostupne else "gemini-1.5-flash"
    except: return "gemini-1.5-flash"

# 2. FUNKCE PRO DATA
def get_weather_desc(code):
    mapping = {0: "Jasno ☀️", 1: "Skoro jasno 🌤️", 2: "Polojasno ⛅", 3: "Zataženo ☁️", 45: "Mlha 🌫️", 51: "Mrholení 🌦️", 61: "Déšť 🌧️", 71: "Sněžení ❄️", 80: "Přeháňky 🌧️", 95: "Bouřka ⚡"}
    return mapping.get(code, f"Kód {code}")

@st.cache_data(ttl=600)
def nacti_kompletni_pocasi():
    mesta = {"Nové Město n. M.": (50.344, 16.151), "Rychnov n. Kn.": (50.162, 16.274), "Bělá": (50.534, 14.807), "Praha": (50.075, 14.437), "Hradec Králové": (50.210, 15.832)}
    dny_cz = ["Pondělí", "Úterý", "Středa", "Čtvrtek", "Pátek", "Sobota", "Neděle"]
    vysledek = {}
    for m, (lat, lon) in mesta.items():
        try:
            r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto").json()
            tyden = []
            for i in range(7):
                d_obj = datetime.now() + timedelta(days=i)
                tyden.append({"Den": dny_cz[d_obj.weekday()], "Datum": d_obj.strftime("%d.%m."), "Stav": get_weather_desc(r['daily']['weathercode'][i]), "Max": f"{round(r['daily']['temperature_2m_max'][i])}°C", "Min": f"{round(r['daily']['temperature_2m_min'][i])}°C", "Déšť": f"{r['daily']['precipitation_probability_max'][i]}%"})
            vysledek[m] = {"akt": f"{round(r['current']['temperature_2m'])}°C", "popis": get_weather_desc(r['current']['weathercode']), "tyden": tyden}
        except: vysledek[m] = {"akt": "??", "popis": "Chyba", "tyden": []}
    return vysledek

@st.cache_data(ttl=600)
def nacti_zpravy():
    vystup = []
    for u in ["https://ct24.ceskatelevize.cz/rss/hlavni-zpravy", "https://www.seznamzpravy.cz/rss"]:
        try:
            root = ET.fromstring(requests.get(u, timeout=5).content)
            for item in root.findall('.//item')[:8]: vystup.append(item.find('title').text)
        except: continue
    return vystup if vystup else ["Aktualizace zpráv..."]

def nacti_gsheets(list_name):
    try:
        url = st.secrets["GSHEET_URL"]
        sheet_id = url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(list_name)}"
        return pd.read_csv(csv_url)
    except: return pd.DataFrame(columns=['zprava'])

# 3. STYLY
st.markdown("""
<style>
    .stApp { background: radial-gradient(circle at center, #1a2c4e 0%, #070b14 100%); color: white; }
    .news-ticker { position: fixed; bottom: 0; left: 0; width: 100%; background: rgba(0, 45, 110, 0.98); color: white; padding: 18px; text-align: center; border-top: 3px solid #3b82f6; z-index: 9999; font-size: 20px; font-weight: bold; }
    .weather-card { background: rgba(255, 255, 255, 0.07); padding: 15px; border-radius: 12px; text-align: center; border: 1px solid rgba(255, 255, 255, 0.1); }
</style>
""", unsafe_allow_html=True)

# 4. NAVIGACE
nav_col = st.columns([1, 2, 1])[1]
if st.session_state.page == "Domů":
    if nav_col.button("💬 OTEVŘÍT AI ASISTENTA 2.0", use_container_width=True, type="primary"): st.session_state.page = "AI Chat"; st.rerun()
else:
    if nav_col.button("🏠 ZPĚT NA HLAVNÍ PORTÁL", use_container_width=True): st.session_state.page = "Domů"; st.rerun()

# 5. DOMOVSKÁ STRÁNKA
if st.session_state.page == "Domů":
    st.markdown("<h1 style='text-align:center;'>🏙️ Kvádr Portál 2.0</h1>", unsafe_allow_html=True)
    w_data = nacti_kompletni_pocasi()
    w_cols = st.columns(len(w_data))
    for i, (mesto, d) in enumerate(w_data.items()):
        w_cols[i].markdown(f"<div class='weather-card'><div style='color:#3b82f6;font-size:0.8em;'>{mesto}</div><div style='font-size:1.8em;font-weight:bold;'>{d['akt']}</div><div style='font-size:0.8em;'>{d['popis']}</div></div>", unsafe_allow_html=True)
    
    st.write("##")
    with st.expander("📅 Zobrazit detailní předpověď a srážky pro všechny lokality"):
        tabs = st.tabs(list(w_data.keys()))
        for i, (mesto, d) in enumerate(w_data.items()):
            with tabs[i]: st.table(pd.DataFrame(d["tyden"]))

    df_ozn = nacti_gsheets("List 2")
    if not df_ozn.empty:
        for z in df_ozn['zprava'].dropna(): st.info(z)

    zpravy = nacti_zpravy()
    idx = st.session_state.news_index % len(zpravy)
    st.markdown(f'<div class="news-ticker">🗞️ {zpravy[idx]}</div>', unsafe_allow_html=True)
    
    time.sleep(8) # Nastaveno na 8 sekund pro klidné čtení
    st.session_state.news_index += 1
    st.rerun()

# 6. AI CHAT
elif st.session_state.page == "AI Chat":
    m_name = najdi_funkcni_model()
    st.markdown(f"<h1 style='text-align:center;'>💬 Kvádr AI 2.0</h1>", unsafe_allow_html=True)
    st.caption(f"Aktivní model: {m_name}")
    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if pr := st.chat_input("Zeptejte se..."):
        st.session_state.chat_history.append({"role": "user", "content": pr})
        with st.chat_message("user"): st.markdown(pr)
        with st.chat_message("assistant"):
            try:
                df = nacti_gsheets("List 1")
                ctx = " ".join(df['zprava'].astype(str).tolist())
                model = genai.GenerativeModel(model_name=m_name, system_instruction=f"Jsi asistent Kvádru 2.0. Kontext: {ctx}")
                hist = [{"role": "user" if h["role"]=="user" else "model", "parts": [h["content"]]} for h in st.session_state.chat_history[:-1]]
                res = model.start_chat(history=hist).send_message(pr)
                st.markdown(res.text)
                st.session_state.chat_history.append({"role": "assistant", "content": res.text})
                st.rerun()
            except Exception as e: st.error(f"Chyba: {e}")
