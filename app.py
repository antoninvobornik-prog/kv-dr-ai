import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# ==========================================
# 1. NASTAVENÍ A KONFIGURACE
# ==========================================
st.set_page_config(page_title="Kvádr AI", layout="wide", page_icon="🏙️", initial_sidebar_state="collapsed")

st.markdown("<style>section[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)

if "page" not in st.session_state:
    st.session_state.page = "Domů"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "news_index" not in st.session_state:
    st.session_state.news_index = 0

try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    if "model_name" not in st.session_state:
        st.session_state.model_name = "gemini-1.5-flash"
except:
    st.error("Chybí API klíč v Secrets!")

# ==========================================
# 2. POMOCNÉ FUNKCE
# ==========================================

@st.cache_data(ttl=300)
def nacti_zpravy():
    try:
        res = requests.get("https://www.seznamzpravy.cz/rss", timeout=5)
        root = ET.fromstring(res.content)
        return [item.find('title').text for item in root.findall('.//item')[:15]]
    except:
        return ["Sledujte projekt Kvádr pro nejnovější info."]

def nacti_kompletni_pocasi():
    """Stáhne aktuální počasí i předpověď na 7 dní."""
    mesta = {"Nové Město n. M.": (50.344, 16.151), "Bělá": (50.534, 14.807), "Praha": (50.075, 14.437), "Hradec Králové": (50.210, 15.832)}
    vysledek = {}
    for m, (lat, lon) in mesta.items():
        try:
            # Přidán parametr daily pro 7denní předpověď
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=auto"
            r = requests.get(url).json()
            
            # Aktuální data
            vysledek[m] = {
                "aktualni": f"{round(r['current']['temperature_2m'])}°C",
                "ikona": "☀️" if r['current']['weathercode'] < 3 else "☁️",
                "tyden": []
            }
            if r['current']['weathercode'] > 60: vysledek[m]["ikona"] = "🌧️"
            
            # Sestavení tabulky na 7 dní
            for i in range(7):
                datum = (datetime.now() + timedelta(days=i)).strftime("%a %d.%m.")
                vysledek[m]["tyden"].append({
                    "Den": datum,
                    "Max": f"{round(r['daily']['temperature_2m_max'][i])}°C",
                    "Min": f"{round(r['daily']['temperature_2m_min'][i])}°C"
                })
        except: vysledek[m] = {"aktualni": "??", "ikona": "⚠️", "tyden": []}
    return vysledek

def nacti_data_sheets(list_name):
    try:
        url = st.secrets["GSHEET_URL"]
        sheet_id = url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(list_name)}"
        return pd.read_csv(csv_url)
    except: return pd.DataFrame(columns=['zprava'])

# ==========================================
# 3. VZHLED (CSS)
# ==========================================
st.markdown("""
<style>
    .stApp { background: radial-gradient(circle at center, #1a2c4e 0%, #070b14 100%); color: white; }
    .news-ticker {
        position: fixed; bottom: 0; left: 0; width: 100%;
        background: rgba(0, 45, 110, 0.95); color: #ffffff;
        padding: 15px; text-align: center; border-top: 3px solid #3b82f6;
        font-weight: bold; z-index: 999; font-size: 18px;
    }
    .weather-card { background: rgba(255,255,255,0.1); padding: 15px; border-radius: 12px; text-align: center; margin-bottom: 10px; }
    h1, h2 { text-align: center; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. NAVIGACE
# ==========================================
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    if st.session_state.page == "Domů":
        if st.button("💬 OTEVŘÍT AI CHAT", use_container_width=True, type="primary"):
            st.session_state.page = "AI Chat"; st.rerun()
    else:
        if st.button("🏠 ZPĚT NA DOMOVSKOU STRÁNKU", use_container_width=True):
            st.session_state.page = "Domů"; st.rerun()

# ==========================================
# 5. STRÁNKA: DOMŮ
# ==========================================
if st.session_state.page == "Domů":
    st.markdown("<h1>🏙️ Kvádr Portál</h1>", unsafe_allow_html=True)
    
    # Počasí - Karty
    w_data = nacti_kompletni_pocasi()
    cols = st.columns(4)
    for i, (mesto, d) in enumerate(w_data.items()):
        cols[i].markdown(f"<div class='weather-card'><b>{mesto}</b><br><span style='font-size:24px;'>{d['ikona']} {d['aktualni']}</span></div>", unsafe_allow_html=True)
    
    # NOVÁ SEKCE: Podrobná předpověď
    with st.expander("📅 Zobrazit podrobnou předpověď na 7 dní"):
        tab_mesta = st.tabs(list(w_data.keys()))
        for i, (mesto, d) in enumerate(w_data.items()):
            with tab_mesta[i]:
                df_w = pd.DataFrame(d["tyden"])
                st.table(df_w) # Zobrazí čistou tabulku bez ovládacích prvků

    # Oznámení
    st.markdown("<br><h2>📢 Oznámení projektu</h2>", unsafe_allow_html=True)
    df_o = nacti_data_sheets("List 2")
    if not df_o.empty:
        for msg in df_o['zprava'].dropna(): st.info(msg)
    else: st.write("Žádná aktuální oznámení.")

    # News Ticker
    zpravy = nacti_zpravy()
    aktualni_zprava = zpravy[st.session_state.news_index % len(zpravy)]
    st.markdown(f'<div class="news-ticker">🗞️ AKTUÁLNĚ: {aktualni_zprava}</div>', unsafe_allow_html=True)

    time.sleep(10)
    st.session_state.news_index += 1
    st.rerun()

# ==========================================
# 6. STRÁNKA: AI CHAT
# ==========================================
elif st.session_state.page == "AI Chat":
    col_h1, col_h2 = st.columns([0.9, 0.1])
    with col_h1: st.markdown("<h1>💬 Chat s Kvádr AI</h1>", unsafe_allow_html=True)
    with col_h2:
        st.write("##")
        if st.button("🗑️"): st.session_state.chat_history = []; st.rerun()

    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Napište zprávu..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Kvádr AI přemýšlí..."):
                try:
                    df_ai = nacti_data_sheets("List 1")
                    info = " ".join(df_ai['zprava'].astype(str).tolist())
                    sys_instr = f"Jsi Kvádr AI, asistent organizace Kvádr. Info: {info}. Odpovídej česky a pamatuj si historii."
                    model = genai.GenerativeModel(st.session_state.model_name, system_instruction=sys_instr)
                    gemini_hist = [{"role": "user" if h["role"] == "user" else "model", "parts": [h["content"]]} for h in st.session_state.chat_history[:-1]]
                    chat = model.start_chat(history=gemini_hist)
                    response = chat.send_message(prompt)
                    if response.text:
                        st.markdown(response.text)
                        st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                        st.rerun()
                except Exception as e: st.error(f"Chyba: {e}")
