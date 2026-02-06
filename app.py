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

# Skrytí bočního panelu
st.markdown("<style>section[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)

# Inicializace stavů
if "page" not in st.session_state:
    st.session_state.page = "Domů"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "news_index" not in st.session_state:
    st.session_state.news_index = 0

# Nastavení AI (Gemini)
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    if "model_name" not in st.session_state:
        st.session_state.model_name = "gemini-1.5-flash"
except:
    st.error("Chybí API klíč v Secrets!")

# ==========================================
# 2. POMOCNÉ FUNKCE
# ==========================================

@st.cache_data(ttl=600)
def nacti_zpravy():
    """Stáhne aktuální zprávy z iRozhlasu."""
    try:
        res = requests.get("https://www.irozhlas.cz/rss/irozhlas", timeout=5)
        root = ET.fromstring(res.content)
        return [item.find('title').text for item in root.findall('.//item')[:15]]
    except:
        return ["Sledujte projekt Kvádr pro nejnovější info.", "Zprávy se načítají..."]

def nacti_kompletni_pocasi():
    """Stáhne počasí pro vybraná města."""
    mesta = {"Nové Město n. M.": (50.344, 16.151), "Bělá": (50.534, 14.807), "Praha": (50.075, 14.437), "Hradec Králové": (50.210, 15.832)}
    vysledek = {}
    for m, (lat, lon) in mesta.items():
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&timezone=auto"
            r = requests.get(url).json()
            vysledek[m] = {
                "teplota": f"{round(r['current']['temperature_2m'])}°C",
                "ikona": "☀️" if r['current']['weathercode'] < 3 else "☁️"
            }
        except: vysledek[m] = {"teplota": "??", "ikona": "⚠️"}
    return vysledek

def nacti_data_sheets(list_name):
    """Načte data z Google Sheets."""
    try:
        url = st.secrets["GSHEET_URL"]
        sheet_id = url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(list_name)}"
        return pd.read_csv(csv_url)
    except: return pd.DataFrame(columns=['zprava'])

# ==========================================
# 3. STYLOVÁNÍ (CSS)
# ==========================================
st.markdown("""
<style>
    .stApp { background: radial-gradient(circle at center, #1a2c4e 0%, #070b14 100%); color: white; }
    .news-ticker {
        position: fixed; bottom: 0; left: 0; width: 100%;
        background: rgba(0, 40, 100, 0.9); color: #60a5fa;
        padding: 12px; text-align: center; border-top: 2px solid #3b82f6;
        font-weight: bold; z-index: 999; font-size: 16px;
    }
    .weather-card { background: rgba(255,255,255,0.1); padding: 15px; border-radius: 12px; text-align: center; }
    h1, h2 { text-align: center; font-family: sans-serif; }
    .stChatFloatingInputContainer { background-color: rgba(0,0,0,0) !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. NAVIGACE
# ==========================================
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    if st.session_state.page == "Domů":
        if st.button("💬 OTEVŘÍT AI CHAT", use_container_width=True, type="primary"):
            st.session_state.page = "AI Chat"
            st.rerun()
    else:
        if st.button("🏠 ZPĚT NA DOMOVSKOU STRÁNKU", use_container_width=True):
            st.session_state.page = "Domů"
            st.rerun()

# ==========================================
# 5. STRÁNKA: DOMŮ
# ==========================================
if st.session_state.page == "Domů":
    st.markdown("<h1>🏙️ Kvádr Portál</h1>", unsafe_allow_html=True)
    
    # Sekce Počasí
    w_data = nacti_kompletni_pocasi()
    cols = st.columns(4)
    for i, (mesto, d) in enumerate(w_data.items()):
        cols[i].markdown(f"<div class='weather-card'><b>{mesto}</b><br><span style='font-size:22px;'>{d['ikona']} {d['teplota']}</span></div>", unsafe_allow_html=True)

    # Sekce Oznámení (Pouze zde!)
    st.markdown("<br><h2>📢 Oznámení</h2>", unsafe_allow_html=True)
    df_o = nacti_data_sheets("List 2")
    if not df_o.empty:
        for msg in df_o['zprava'].dropna():
            st.info(msg)
    else:
        st.write("Žádná aktuální oznámení.")

    # Zpravodajský panel (běžící zprávy)
    zpravy = nacti_zpravy()
    aktualni_zprava = zpravy[st.session_state.news_index % len(zpravy)]
    st.markdown(f'<div class="news-ticker">🗞️ NOVINKY: {aktualni_zprava}</div>', unsafe_allow_html=True)

    # Automatické překlopení zprávy po 10 sekundách
    time.sleep(10)
    st.session_state.news_index += 1
    st.rerun()

# ==========================================
# 6. STRÁNKA: AI CHAT
# ==========================================
elif st.session_state.page == "AI Chat":
    col_h1, col_h2 = st.columns([0.9, 0.1])
    with col_h1:
        st.markdown("<h1>💬 Chat s Kvádr AI</h1>", unsafe_allow_html=True)
    with col_h2:
        st.write("##")
        if st.button("🗑️", help="Vymazat historii"):
            st.session_state.chat_history = []
            st.rerun()

    # Zobrazení historie
    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # Chat vstup
    if prompt := st.chat_input("Napište zprávu..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Kvádr AI přemýšlí..."):
                try:
                    # Načtení kontextu
                    df_ai = nacti_data_sheets("List 1")
                    info = " ".join(df_ai['zprava'].astype(str).tolist())
                    
                    sys_instr = f"Jsi Kvádr AI, asistent organizace Kvádr. Info: {info}. Odpovídej česky a stručně. Pamatuj si historii."
                    
                    model = genai.GenerativeModel(st.session_state.model_name, system_instruction=sys_instr)
                    
                    # Formátování historie pro Gemini
                    gemini_hist = []
                    for h in st.session_state.chat_history[:-1]:
                        r = "user" if h["role"] == "user" else "model"
                        gemini_hist.append({"role": r, "parts": [h["content"]]})
                    
                    chat = model.start_chat(history=gemini_hist)
                    response = chat.send_message(prompt)
                    
                    if response.text:
                        st.markdown(response.text)
                        st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                        st.rerun()
                except Exception as e:
                    st.error(f"Chyba: {e}")
