import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# ==========================================
# 1. KONFIGURACE A DYNAMICKÝ VÝBĚR MODELU
# ==========================================
st.set_page_config(page_title="Kvádr AI", layout="wide")

if "page" not in st.session_state: st.session_state.page = "Domů"
if "news_index" not in st.session_state: st.session_state.news_index = 0
if "chat_history" not in st.session_state: st.session_state.chat_history = []

@st.cache_resource
def inicializuj_ai():
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        # Dynamické hledání funkčního modelu
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini-1.5-flash' in m.name or 'gemini-1.5-pro' in m.name:
                    return genai.GenerativeModel(m.name)
        # Nouzový pokus, pokud listování selže
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Nelze inicializovat AI: {e}")
        return None

ai_model = inicializuj_ai()

# ==========================================
# 2. POMOCNÉ FUNKCE (Zprávy, Počasí, Tabulky)
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
    return zpravy if zpravy else ["Systém Kvádr je připraven.", "Aktualizace zpráv probíhá..."]

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
                "ikona": "☀️" if res['current']['weathercode'] == 0 else "☁️"
            }
        except: data_out[m] = {"teplota": "??", "ikona": "⚠️"}
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
        position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%);
        background: rgba(15, 25, 45, 0.95); border: 1px solid #3b82f6;
        padding: 12px 35px; border-radius: 40px; z-index: 9999;
        text-align: center; width: auto; min-width: 300px; max-width: 85%;
        box-shadow: 0 10px 30px rgba(0,0,0,0.6);
    }
    .news-text { color: #60a5fa; font-size: 14px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. NAVIGACE
# ==========================================
c_nav = st.columns([1, 2, 1])
with c_nav[1]:
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
    st.markdown("<h1 style='text-align:center; margin-bottom:0;'>PORTÁL KVÁDR</h1>", unsafe_allow_html=True)
    
    # Počasí
    w_data = nacti_kompletni_pocasi()
    cols = st.columns(len(w_data))
    for i, (mesto, d) in enumerate(w_data.items()):
        cols[i].metric(mesto, d["teplota"], d["ikona"])

    st.write("---")
    
    # Oznámení
    df_oznameni = nacti_data_sheets("List 2")
    for msg in df_oznameni['zprava'].dropna():
        st.info(f"📢 {msg}")

    # Zpravodajský ostrůvek (Novinky/CT24)
    seznam = nacti_aktuality()
    idx = st.session_state.news_index % len(seznam)
    st.markdown(f'<div class="news-island"><div class="news-text">🗞️ {seznam[idx]}</div></div>', unsafe_allow_html=True)

    # Automatické přepnutí po 8 sekundách
    time.sleep(8)
    st.session_state.news_index += 1
    st.rerun()

elif st.session_state.page == "AI Chat":
    st.title("💬 Kvádr AI")
    
    if ai_model is None:
        st.error("AI model není dostupný. Zkontrolujte API klíč v Secrets.")
    
    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if pr := st.chat_input("Zeptej se mě na projekt Kvádr..."):
        st.session_state.chat_history.append({"role": "user", "content": pr})
        with st.chat_message("user"): st.markdown(pr)
        
        with st.chat_message("assistant"):
            try:
                df_ctx = nacti_data_sheets("List 1")
                context = " ".join(df_ctx['zprava'].astype(str).tolist())
                
                # Pokud model existuje, generuj odpověď
                prompt = f"Jsi asistent projektu Kvádr. Info: {context}. Dotaz: {pr}"
                response = ai_model.generate_content(prompt)
                
                st.markdown(response.text)
                st.session_state.chat_history.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Chyba při generování: {e}")
