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
# 2. FUNKCE
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

@st.cache_data(ttl=1800)
def nacti_pocasi():
    mesta = {"Nové Město": (50.344, 16.151), "Bělá": (50.534, 14.807), "Praha": (50.075, 14.437), "Hradec": (50.210, 15.832)}
    out = {}
    for m, (lat, lon) in mesta.items():
        try:
            r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m&timezone=auto").json()
            out[m] = f"{round(r['current']['temperature_2m'])}°"
        except: out[m] = "--"
    return out

def nacti_sheet(list_name):
    try:
        url = st.secrets["GSHEET_URL"]
        sid = url.split("/d/")[1].split("/")[0]
        return pd.read_csv(f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(list_name)}")
    except: return pd.DataFrame(columns=['zprava'])

# ==========================================
# 3. STYLY (BUBLINY, PLOVOUCÍ DVOUŘÁDKOVÁ LIŠTA)
# ==========================================
st.markdown("""
<style>
    .stApp { background: radial-gradient(circle at center, #1a2c4e 0%, #070b14 100%); color: white; }
    
    /* BUBLINY POČASÍ */
    .w-grid { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin-bottom: 20px; }
    .w-box { background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); padding: 8px 12px; border-radius: 15px; text-align: center; min-width: 80px; }

    /* PLOVOUCÍ LIŠTA DOLE - DVOUŘÁDKOVÁ */
    .floating-news {
        position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%);
        background: rgba(15, 23, 42, 0.95); border: 1px solid #3b82f6;
        padding: 10px 15px; border-radius: 20px; width: 90%; max-width: 500px;
        z-index: 1000; backdrop-filter: blur(10px); text-align: center;
        box-shadow: 0 5px 20px rgba(0,0,0,0.6);
    }
    .news-text { 
        color: #60a5fa; font-weight: bold; font-size: 14px; line-height: 1.2;
        display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
    }
    .news-time { color: #3b82f6; font-size: 10px; opacity: 0.7; margin-bottom: 2px; display: block; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. OBSAH
# ==========================================
if st.session_state.page == "Domů":
    st.markdown('<h1 style="text-align:center; font-size: 24px;">🏙️ KVÁDR PORTÁL</h1>', unsafe_allow_html=True)
    
    # 1. BUBLINY S TEPLOTOU (ZPĚT)
    w_data = nacti_pocasi()
    w_html = '<div class="w-grid">'
    for m, t in w_data.items():
        w_html += f'<div class="w-box"><div style="font-size:10px; opacity:0.6;">{m}</div><div style="font-size:16px; font-weight:bold;">{t}</div></div>'
    w_html += '</div>'
    st.markdown(w_html, unsafe_allow_html=True)

    if st.button("💬 OTEVŘÍT KVÁDR AI CHAT", use_container_width=True, type="primary"):
        st.session_state.page = "AI Chat"; st.rerun()
        
    # Oznámení
    df = nacti_sheet("List 2")
    for msg in df['zprava'].dropna(): st.info(msg)

    # 2. PLOVOUCÍ ZPRÁVY DOLE (DVOUŘÁDKOVÉ)
    zpravy, cas = nacti_aktuality()
    idx = st.session_state.news_index % len(zpravy)
    st.markdown(f'''
        <div class="floating-news">
            <span class="news-time">{cas}</span>
            <div class="news-text">🗞️ {zpravy[idx]}</div>
        </div>
    ''', unsafe_allow_html=True)
    
    time.sleep(8)
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
        
        # 3. KOLEČKO NAČÍTÁNÍ (spinner)
        with st.chat_message("assistant"):
            with st.spinner("Kvádr přemýšlí..."):
                if ai_model:
                    try:
                        ctx = " ".join(nacti_sheet("List 1")['zprava'].astype(str))
                        resp = ai_model.generate_content(f"Info: {ctx}\nUživatel: {p}")
                        st.markdown(resp.text)
                        st.session_state.chat_history.append({"role": "assistant", "content": resp.text})
                    except Exception as e:
                        st.error("Chyba AI spojení.")
