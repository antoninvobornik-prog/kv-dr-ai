import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# ==========================================
# 1. KONFIGURACE A STAV
# ==========================================
st.set_page_config(page_title="Kvádr AI", layout="wide")

if "page" not in st.session_state: st.session_state.page = "Domů"
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "news_index" not in st.session_state: st.session_state.news_index = 0

@st.cache_resource
def najdi_model():
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        dostupne = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return next((n for n in dostupne if '1.5-flash' in n), dostupne[0])
    except: return None

MODEL_ID = najdi_model()

# ==========================================
# 2. POMOCNÉ FUNKCE
# ==========================================
def nacti_data_sheets(nazev_listu):
    try:
        base_url = st.secrets["GSHEET_URL"]
        sid = base_url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(nazev_listu)}"
        return pd.read_csv(csv_url)
    except: return pd.DataFrame(columns=['rok', 'udalost', 'zprava'])

def get_wmo_description(code):
    mapping = {0: "Jasno", 1: "Převážně jasno", 2: "Polojasno", 3: "Zataženo", 45: "Mlha", 61: "Slabý déšť", 71: "Sněžení", 95: "Bouřka"}
    return mapping.get(code, "Oblačno")

@st.cache_data(ttl=1800)
def nacti_kompletni_pocasi():
    mesta = {"Nové Město n. M.": (50.344, 16.151), "Bělá": (50.534, 14.807), "Praha": (50.075, 14.437), "Hradec Králové": (50.210, 15.832)}
    output = {}
    for m, (lat, lon) in mesta.items():
        try:
            res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=auto", timeout=5).json()
            output[m] = {
                "teplota": f"{round(res['current']['temperature_2m'])}°C",
                "stav": get_wmo_description(res['current']['weathercode']),
                "ikona": "☀️" if res['current']['weathercode'] < 3 else "☁️",
                "predpoved": [{"den": (datetime.now() + timedelta(days=i)).strftime("%d.%m."), "stav": get_wmo_description(res['daily']['weathercode'][i]), "teplota": f"{round(res['daily']['temperature_2m_min'][i])}°/{round(res['daily']['temperature_2m_max'][i])}°"} for i in range(5)]
            }
        except: output[m] = {"teplota": "--", "stav": "Nenalezeno", "ikona": "⚠️", "predpoved": []}
    return output

# ... (Styly CSS zůstávají stejné)
st.markdown("""
<style>
    .stApp { background: radial-gradient(circle at center, #1a2c4e 0%, #070b14 100%); color: white; }
    .news-island { position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%); background: rgba(15, 23, 42, 0.9); border: 1px solid #3b82f6; padding: 10px 20px; border-radius: 20px; z-index: 1000; width: 90%; max-width: 500px; text-align: center; backdrop-filter: blur(10px); }
    .news-text { color: #60a5fa; font-weight: bold; font-size: 13px; }
    .timeline-card { background: rgba(255,255,255,0.05); border-left: 4px solid #3b82f6; padding: 15px; margin: 12px 0; border-radius: 0 12px 12px 0; }
    .year-label { color: #3b82f6; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. NAVIGACE
# ==========================================
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    if st.session_state.page == "Domů":
        if st.button("🗺️ PROZKOUMAT KVÁDR SVĚT", use_container_width=True):
            st.session_state.page = "Info"; st.rerun()
        if st.button("💬 OTEVŘÍT KVÁDR AI CHAT", use_container_width=True, type="primary"):
            st.session_state.page = "AI Chat"; st.rerun()
    else:
        if st.button("🏠 ZPĚT NA ÚVOD", use_container_width=True):
            st.session_state.page = "Domů"; st.rerun()

# ==========================================
# 5. STRÁNKA: DOMŮ
# ==========================================
if st.session_state.page == "Domů":
    st.markdown('<h1 style="text-align:center;">🏙️ KVÁDR PORTÁL</h1>', unsafe_allow_html=True)
    df_oznameni = nacti_data_sheets("List 2")
    if 'zprava' in df_oznameni.columns:
        for msg in df_oznameni['zprava'].dropna(): st.info(msg)
    
    # Zpravodajská lišta
    try:
        zpravy = []
        res = requests.get("https://ct24.ceskatelevize.cz/rss/hlavni-zpravy", timeout=5)
        root = ET.fromstring(res.content)
        for item in root.findall('.//item')[:5]: zpravy.append(item.find('title').text)
        idx = st.session_state.news_index % len(zpravy)
        st.markdown(f'<div class="news-island"><div class="news-text">🗞️ {zpravy[idx]}</div></div>', unsafe_allow_html=True)
    except: pass
    
    time.sleep(8); st.session_state.news_index += 1; st.rerun()

# ==========================================
# 6. STRÁNKA: INFO (PŘEJMENOVÁNO)
# ==========================================
elif st.session_state.page == "Info":
    st.markdown('<h2 style="text-align:center;">🗺️ Kvádr Info & Počasí</h2>', unsafe_allow_html=True)
    tab_pocasi, tab_historie = st.tabs(["🌦️ Předpověď počasí", "📜 Historie a Sezóny"])
    
    with tab_pocasi:
        w_data = nacti_kompletni_pocasi()
        cols = st.columns(2)
        for i, (mesto, d) in enumerate(w_data.items()):
            with cols[i % 2]:
                st.markdown(f"### {d['ikona']} {mesto}: {d['teplota']}")
                st.write(f"*Aktuální stav: {d['stav']}*")
                for f in d['predpoved']:
                    st.write(f"**{f['den']}**: {f['stav']} | {f['teplota']}")
                st.divider()

    with tab_historie:
        df_hist = nacti_data_sheets("List 3")
        if not df_hist.empty:
            # Čištění zobrazení: odstranění nan a .0
            df_hist = df_hist.fillna("")
            for _, row in df_hist.iterrows():
                rok = str(row['rok']).replace(".0", "")
                if rok == "nan": rok = ""
                st.markdown(f'<div class="timeline-card"><div class="year-label">{rok}</div>{row["udalost"]}</div>', unsafe_allow_html=True)

# ==========================================
# 7. STRÁNKA: AI CHAT
# ==========================================
elif st.session_state.page == "AI Chat":
    st.markdown('<h2 style="text-align:center;">💬 Kvádr AI</h2>', unsafe_allow_html=True)
    # (Chat kód zůstává beze změny...)
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
    if pr := st.chat_input("Zeptej se..."):
        st.session_state.chat_history.append({"role": "user", "content": pr})
        with st.chat_message("user"): st.markdown(pr)
        with st.chat_message("assistant"):
            df_ai = nacti_data_sheets("List 1")
            ctx = " ".join(df_ai['zprava'].astype(str).tolist())
            model = genai.GenerativeModel(MODEL_ID)
            res = model.generate_content(f"Jsi asistent Kvádru. Kontext: {ctx}\nUživatel: {pr}")
            st.markdown(res.text)
            st.session_state.chat_history.append({"role": "assistant", "content": res.text})
