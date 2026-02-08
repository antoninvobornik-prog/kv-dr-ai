import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# ==========================================
# 1. NASTAVENÍ
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

def nacti_sheet(list_name):
    try:
        url = st.secrets["GSHEET_URL"]
        sid = url.split("/d/")[1].split("/")[0]
        return pd.read_csv(f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(list_name)}")
    except: return pd.DataFrame(columns=['zprava'])

# ==========================================
# 3. STYLY (DVOUŘÁDKOVÝ DISPLEJ A POZICE)
# ==========================================
st.markdown("""
<style>
    .stApp { background: radial-gradient(circle at center, #1a2c4e 0%, #070b14 100%); color: white; }
    
    /* KONTEJNER PRO ZPRÁVY */
    .news-container {
        margin-top: 30px;
        padding: 15px;
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid #3b82f6;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }

    .news-text { 
        color: #60a5fa; 
        font-weight: bold; 
        font-size: 15px;
        line-height: 1.3;
        display: -webkit-box;
        -webkit-line-clamp: 2; /* MAXIMÁLNĚ 2 ŘÁDKY */
        -webkit-box-orient: vertical;
        overflow: hidden; /* OŘÍZNE ZBYTEK */
    }

    .news-time { 
        color: #3b82f6; 
        font-size: 11px; 
        display: block;
        margin-bottom: 5px;
        opacity: 0.7;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. OBSAH
# ==========================================
if st.session_state.page == "Domů":
    st.markdown('<h2 style="text-align:center;">🏙️ KVÁDR PORTÁL</h2>', unsafe_allow_html=True)
    
    # Hlavní tlačítka (budou nahoře a vždy vidět)
    if st.button("💬 OTEVŘÍT KVÁDR AI CHAT", use_container_width=True, type="primary"):
        st.session_state.page = "AI Chat"; st.rerun()
        
    if st.button("📅 Zobrazit předpověď", use_container_width=True):
        st.info("Předpověď se připravuje...")

    # Oznámení z tabulky
    df = nacti_sheet("List 2")
    for msg in df['zprava'].dropna():
        st.info(msg)

    # ZPRÁVY DOLE - DVOUŘÁDKOVÉ
    zpravy, cas = nacti_aktuality()
    idx = st.session_state.news_index % len(zpravy)
    
    st.markdown(f'''
        <div class="news-container">
            <span class="news-time">Aktualizováno: {cas}</span>
            <div class="news-text">🗞️ {zpravy[idx]}</div>
        </div>
    ''', unsafe_allow_html=True)
    
    # Automatické přepínání
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
        if ai_model:
            ctx = " ".join(nacti_sheet("List 1")['zprava'].astype(str))
            resp = ai_model.generate_content(f"Info: {ctx}\nUživatel: {p}")
            st.session_state.chat_history.append({"role": "assistant", "content": resp.text})
            st.rerun()
