import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# ==========================================
# 1. KONFIGURACE A OPRAVA AI
# ==========================================
st.set_page_config(page_title="Kvádr AI", layout="wide")

# Inicializace stavů
if "page" not in st.session_state: st.session_state.page = "Domů"
if "news_index" not in st.session_state: st.session_state.news_index = 0
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# Pokus o konfiguraci AI
try:
    # Ujisti se, že v Secrets máš přesně název GOOGLE_API_KEY
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Použijeme model bez prefixu 'models/'
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Chyba nastavení API: {e}")

# ==========================================
# 2. POMOCNÉ FUNKCE
# ==========================================

@st.cache_data(ttl=600)
def nacti_aktuality():
    zpravy = []
    zdroje = ["https://ct24.ceskatelevize.cz/rss/hlavni-zpravy", "https://www.novinky.cz/rss"]
    for url in zdroje:
        try:
            res = requests.get(url, timeout=5)
            root = ET.fromstring(res.content)
            for item in root.findall('.//item')[:5]:
                title = item.find('title').text
                if title: zpravy.append(title.strip())
        except: continue
    return zpravy if zpravy else ["Kvádr AI je připraven.", "Aktuální zprávy se načítají..."]

@st.cache_data(ttl=1800)
def nacti_kompletni_pocasi():
    souradnice = {"Nové Město n. M.": (50.344, 16.151), "Bělá": (50.534, 14.807), "Praha": (50.075, 14.437), "Hradec Králové": (50.210, 15.832)}
    data_out = {}
    for m, (lat, lon) in souradnice.items():
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=auto"
            res = requests.get(url, timeout=5).json()
            data_out[m] = {
                "teplota": f"{round(res['current']['temperature_2m'])}°C",
                "ikona": "☀️" if res['current']['weathercode'] == 0 else "☁️",
                "predpoved": [{"den": (datetime.now()+timedelta(days=i)).strftime("%d.%m."), "t": f"{round(res['daily']['temperature_2m_min'][i])}°/{round(res['daily']['temperature_2m_max'][i])}°"} for i in range(5)]
            }
        except: data_out[m] = {"teplota": "??", "ikona": "⚠️", "predpoved": []}
    return data_out

def nacti_data_sheets(nazev_listu):
    try:
        url = st.secrets["GSHEET_URL"]
        id = url.split("/d/")[1].split("/")[0]
        csv = f"https://docs.google.com/spreadsheets/d/{id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(nazev_listu)}"
        return pd.read_csv(csv)
    except: return pd.DataFrame(columns=['zprava'])

# ==========================================
# 3. STYLY
# ==========================================
st.markdown("""
<style>
    .stApp { background: #070b14; color: white; }
    .news-island {
        position: fixed; bottom: 25px; left: 50%; transform: translateX(-50%);
        background: rgba(20, 30, 50, 0.95); border: 1px solid #3b82f6;
        padding: 10px 30px; border-radius: 30px; z-index: 9999;
        text-align: center; width: 80%; box-shadow: 0 0 20px rgba(59,130,246,0.3);
    }
    .news-text { color: #60a5fa; font-size: 14px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. NAVIGACE
# ==========================================
col_nav = st.columns([1, 2, 1])
with col_nav[1]:
    if st.session_state.page == "Domů":
        if st.button("💬 OTEVŘÍT KVÁDR AI", use_container_width=True, type="primary"):
            st.session_state.page = "AI Chat"; st.rerun()
    else:
        if st.button("🏠 ZPĚT NA PORTÁL", use_container_width=True):
            st.session_state.page = "Domů"; st.rerun()

# ==========================================
# 5. LOGIKA STRÁNEK
# ==========================================
if st.session_state.page == "Domů":
    st.markdown("<h1 style='text-align:center;'>PORTÁL KVÁDR</h1>", unsafe_allow_html=True)
    
    # Počasí lišta
    w_data = nacti_kompletni_pocasi()
    cols = st.columns(len(w_data))
    for i, (mesto, d) in enumerate(w_data.items()):
        cols[i].metric(mesto, d["teplota"], d["ikona"])

    # Zprávy z tabulky
    st.write("---")
    df_oznameni = nacti_data_sheets("List 2")
    for msg in df_oznameni['zprava'].dropna():
        st.info(msg)

    # Zpravodajský ostrůvek (Novinky/CT24)
    seznam = nacti_aktuality()
    idx = st.session_state.news_index % len(seznam)
    st.markdown(f'<div class="news-island"><div class="news-text">🔥 AKTUÁLNĚ: {seznam[idx]}</div></div>', unsafe_allow_html=True)

    # Auto-refresh po 8 sekundách
    time.sleep(8)
    st.session_state.news_index += 1
    st.rerun()

elif st.session_state.page == "AI Chat":
    st.title("💬 Kvádr AI")
    
    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if pr := st.chat_input("Zeptej se na cokoliv..."):
        st.session_state.chat_history.append({"role": "user", "content": pr})
        with st.chat_message("user"): st.markdown(pr)
        
        with st.chat_message("assistant"):
            try:
                # Načtení kontextu z tabulky
                df_ctx = nacti_data_sheets("List 1")
                context = " ".join(df_ctx['zprava'].astype(str).tolist())
                
                # Volání AI
                full_prompt = f"Jsi asistent projektu Kvádr. Kontext: {context}. Dotaz: {pr}"
                response = ai_model.generate_content(full_prompt)
                
                st.markdown(response.text)
                st.session_state.chat_history.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"AI se nepodařilo odpovědět. Důvod: {e}")
