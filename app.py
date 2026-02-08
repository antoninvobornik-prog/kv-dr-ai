import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# ==========================================
# 1. NASTAVENÍ A AI
# ==========================================
st.set_page_config(page_title="Kvádr AI", layout="wide")

if "page" not in st.session_state: st.session_state.page = "Domů"
if "show_weather_details" not in st.session_state: st.session_state.show_weather_details = False
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "news_index" not in st.session_state: st.session_state.news_index = 0

@st.cache_resource
def inicializuj_ai():
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        dostupne = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        vybrany = next((n for n in dostupne if '1.5-flash' in n), dostupne[0] if dostupne else None)
        return genai.GenerativeModel(model_name=vybrany) if vybrany else None
    except: return None

ai_model = inicializuj_ai()

# ==========================================
# 2. FUNKCE (ZPRÁVY BEZ TEXTU AKTUALIZOVÁNO)
# ==========================================
@st.cache_data(ttl=300)
def nacti_aktuality():
    zpravy = []
    try:
        res = requests.get("https://ct24.ceskatelevize.cz/rss/hlavni-zpravy", timeout=5)
        root = ET.fromstring(res.content)
        for item in root.findall('.//item')[:8]:
            t = item.find('title').text
            if t: zpravy.append(t.strip().replace('\n', ' '))
    except: pass
    return (zpravy if zpravy else ["Systém Kvádr je online."]), datetime.now().strftime("%H:%M")

def get_wmo_emoji(code):
    mapping = {0: "☀️", 1: "⛅", 3: "☁️", 61: "☔", 71: "❄️"}
    return mapping.get(code, "☁️")

@st.cache_data(ttl=1800)
def nacti_pocasi():
    mesta = {"Nové Město n. M.": (50.344, 16.151), "Bělá": (50.534, 14.807), "Praha": (50.075, 14.437), "Hradec Králové": (50.210, 15.832)}
    out = {}
    for m, (lat, lon) in mesta.items():
        try:
            r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&timezone=auto").json()
            out[m] = {"teplota": f"{round(r['current']['temperature_2m'])}°C", "ikona": get_wmo_emoji(r['current']['weathercode'])}
        except: out[m] = {"teplota": "--", "ikona": "⚠️"}
    return out

def nacti_sheet(list_name):
    try:
        url = st.secrets["GSHEET_URL"]
        sid = url.split("/d/")[1].split("/")[0]
        return pd.read_csv(f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(list_name)}")
    except: return pd.DataFrame(columns=['zprava'])

# ==========================================
# 3. STYLY (MAXIMÁLNÍ PROSTOR PRO TEXT)
# ==========================================
st.markdown("""
<style>
    .stApp { background: radial-gradient(circle at center, #1a2c4e 0%, #070b14 100%); color: white; }
    
    .news-island {
        position: fixed; 
        bottom: 130px; /* POSUNUTO VÝŠ NAD TLAČÍTKO */
        left: 50%; 
        transform: translateX(-50%);
        background: rgba(15, 23, 42, 0.95); 
        border: 1px solid #3b82f6;
        padding: 8px 15px; 
        border-radius: 50px; 
        width: 92%; 
        max-width: 600px;
        text-align: center; 
        z-index: 1000; 
        backdrop-filter: blur(15px);
        white-space: nowrap; 
        overflow: hidden;
    }
    .news-text { 
        color: #60a5fa; 
        font-weight: bold; 
        font-size: 13px; 
    }
    .news-time { 
        color: #3b82f6; 
        font-size: 10px; 
        margin-right: 5px;
        opacity: 0.6;
    }
    
    .w-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 15px; }
    .w-box { background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.2); padding: 8px; border-radius: 12px; text-align: center; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. OBSAH DOMOVSKÉ STRÁNKY
# ==========================================
if st.session_state.page == "Domů":
    st.markdown('<h2 style="text-align:center; margin-bottom:20px;">🏙️ KVÁDR PORTÁL</h2>', unsafe_allow_html=True)
    
    # Počasí v mřížce 2x2 pro mobil
    w_data = nacti_pocasi()
    st.markdown('<div class="w-grid">', unsafe_allow_html=True)
    for mesto, d in w_data.items():
        st.markdown(f'<div class="w-box"><div style="font-size:10px; opacity:0.7;">{mesto}</div><div style="font-size:16px; font-weight:bold;">{d["ikona"]} {d["teplota"]}</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("💬 OTEVŘÍT KVÁDR AI CHAT", use_container_width=True, type="primary"):
        st.session_state.page = "AI Chat"; st.rerun()
        
    st.button("📅 Zobrazit předpověď", use_container_width=True)

    # Oznámení
    df = nacti_sheet("List 2")
    for msg in df['zprava'].dropna(): st.info(msg)

    # ZPRÁVY (BEZ SLOVA AKTUALIZOVÁNO)
    zpravy, cas = nacti_aktuality()
    idx = st.session_state.news_index % len(zpravy)
    st.markdown(f'''
        <div class="news-island">
            <span class="news-time">[{cas}]</span>
            <span class="news-text">🗞️ {zpravy[idx]}</span>
        </div>
    ''', unsafe_allow_html=True)
    
    time.sleep(7)
    st.session_state.news_index += 1
    st.rerun()

elif st.session_state.page == "AI Chat":
    if st.button("🏠 ZPĚT"): st.session_state.page = "Domů"; st.rerun()
    st.title("💬 Kvádr AI")
    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    
    if p := st.chat_input("Zeptej se..."):
        st.session_state.chat_history.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        if ai_model:
            ctx = " ".join(nacti_sheet("List 1")['zprava'].astype(str))
            resp = ai_model.generate_content(f"Info: {ctx}\nUživatel: {p}")
            st.session_state.chat_history.append({"role": "assistant", "content": resp.text})
            st.rerun()
