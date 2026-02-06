import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# =================================================================
# 1. KONFIGURACE A NASTAVENÍ STAVU
# =================================================================
st.set_page_config(
    page_title="Kvádr Portál 2.1", 
    layout="wide", 
    page_icon="🏙️", 
    initial_sidebar_state="collapsed"
)

# Skrytí postranního panelu
st.markdown("<style>section[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)

# Inicializace paměti aplikace (session_state)
if "page" not in st.session_state:
    st.session_state.page = "Domů"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "news_index" not in st.session_state:
    st.session_state.news_index = 0
if "cache_zpravy" not in st.session_state:
    st.session_state.cache_zpravy = []
if "posledni_update_zprav" not in st.session_state:
    st.session_state.posledni_update_zprav = 0

# Konfigurace Google AI
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    if "model_name" not in st.session_state:
        st.session_state.model_name = "gemini-1.5-flash"
except Exception as e:
    st.error(f"Chyba AI konfigurace: {e}")

# =================================================================
# 2. LOGICKÉ FUNKCE (POČASÍ, ZPRÁVY, DATA)
# =================================================================

def get_weather_desc(code):
    """Kompletní převodník kódů Open-Meteo (řeší problém 'Neznámé')."""
    mapping = {
        0: "Jasno ☀️", 1: "Převážně jasno 🌤️", 2: "Polojasno ⛅", 3: "Zataženo ☁️",
        45: "Mlha 🌫️", 48: "Námraza 🌫️", 
        51: "Mírné mrholení 🌦️", 53: "Mrholení 🌦️", 55: "Silné mrholení 🌧️", 
        61: "Slabý déšť 🌧️", 63: "Déšť 🌧️", 65: "Silný déšť 🌊",
        66: "Mrznoucí déšť 🧊", 67: "Silný mrznoucí déšť 🧊",
        71: "Slabé sněžení ❄️", 73: "Sněžení ❄️", 75: "Silné sněžení ☃️", 
        77: "Sněhové krupky 🌨️",
        80: "Slabé přeháňky 🌦️", 81: "Přeháňky 🌧️", 82: "Silné přeháňky 🌊",
        85: "Sněhové přeháňky 🌨️", 86: "Silné sněhové přeháňky ❄️",
        95: "Bouřka ⚡", 96: "Bouřka s kroupami ⛈️", 99: "Silná bouřka ⛈️"
    }
    return mapping.get(code, f"Neznámé ({code})")

@st.cache_data(ttl=600)
def nacti_kompletni_pocasi():
    """Načte počasí pro klíčové lokality projektu."""
    mesta = {
        "Nové Město n. M.": (50.344, 16.151), 
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
            
            predpoved = []
            for i in range(7):
                datum_obj = datetime.now() + timedelta(days=i)
                predpoved.append({
                    "Den": dny_cz[datum_obj.weekday()],
                    "Datum": datum_obj.strftime("%d.%m."),
                    "Stav": get_weather_desc(r['daily']['weathercode'][i]),
                    "Max": f"{round(r['daily']['temperature_2m_max'][i])}°C",
                    "Min": f"{round(r['daily']['temperature_2m_min'][i])}°C",
                    "Déšť": f"{r['daily']['precipitation_probability_max'][i]}%"
                })
            
            vysledek[m] = {
                "aktualni": f"{round(r['current']['temperature_2m'])}°C",
                "popis": get_weather_desc(r['current']['weathercode']),
                "tyden": predpoved
            }
        except:
            vysledek[m] = {"aktualni": "??", "popis": "Chyba spojení", "tyden": []}
    return vysledek

def nacti_zpravy_agregovane():
    """Získá RSS zprávy a uloží je do mezipaměti pro plynulost lišty."""
    ted = time.time()
    if st.session_state.cache_zpravy and (ted - st.session_state.posledni_update_zprav < 600):
        return st.session_state.cache_zpravy

    zdroje = [
        ("ČT24", "https://ct24.ceskatelevize.cz/rss/hlavni-zpravy"),
        ("Seznam", "https://www.seznamzpravy.cz/rss")
    ]
    vystup = []
    for label, url in zdroje:
        try:
            r = requests.get(url, timeout=4)
            root = ET.fromstring(r.content)
            for item in root.findall('.//item')[:12]:
                title = item.find('title').text
                vystup.append(f"{label}: {title}")
        except: continue
            
    if vystup:
        st.session_state.cache_zpravy = vystup
        st.session_state.posledni_update_zprav = ted
        return vystup
    return ["Zprávy se nepodařilo aktualizovat..."]

def nacti_data_sheets(list_name):
    """Načte data z Google Sheets pro AI a Oznámení."""
    try:
        url = st.secrets["GSHEET_URL"]
        sheet_id = url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(list_name)}"
        return pd.read_csv(csv_url)
    except:
        return pd.DataFrame(columns=['zprava'])

# =================================================================
# 3. VZHLED (CSS STYLY)
# =================================================================
st.markdown("""
<style>
    .stApp { background: radial-gradient(circle at center, #1a2c4e 0%, #070b14 100%); color: white; }
    
    .news-ticker {
        position: fixed; bottom: 0; left: 0; width: 100%;
        background: rgba(0, 45, 110, 0.98); color: white;
        padding: 16px; text-align: center;
        border-top: 3px solid #3b82f6; font-weight: bold;
        z-index: 9999; font-size: 20px;
        box-shadow: 0px -5px 20px rgba(0,0,0,0.6);
    }
    
    .weather-card {
        background: rgba(255, 255, 255, 0.05); padding: 22px;
        border-radius: 15px; text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    .stButton>button { border-radius: 12px; font-weight: 800; letter-spacing: 0.5px; }
</style>
""", unsafe_allow_html=True)

# =================================================================
# 4. NAVIGACE
# =================================================================
nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
with nav_col2:
    if st.session_state.page == "Domů":
        if st.button("💬 OTEVŘÍT AI ASISTENTA 2.0", use_container_width=True, type="primary"):
            st.session_state.page = "AI Chat"; st.rerun()
    else:
        if st.button("🏠 ZPĚT NA HLAVNÍ PORTÁL", use_container_width=True):
            st.session_state.page = "Domů"; st.rerun()

# =================================================================
# 5. STRÁNKA: DOMOVSKÝ PANEL
# =================================================================
if st.session_state.page == "Domů":
    st.markdown("<h1 style='text-align:center;'>🏙️ Kvádr Portál 2.1</h1>", unsafe_allow_html=True)
    
    # --- POČASÍ ---
    w_data = nacti_kompletni_pocasi()
    w_cols = st.columns(4)
    for i, (mesto, d) in enumerate(w_data.items()):
        w_cols[i].markdown(f"""
        <div class='weather-card'>
            <div style='color: #3b82f6; font-size: 0.9em;'>{mesto}</div>
            <div style='font-size: 2.3em; font-weight: bold; margin: 5px 0;'>{d['aktualni']}</div>
            <div style='font-size: 0.95em;'>{d['popis']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.write("##")
    with st.expander("📅 Zobrazit detailní předpověď a srážky (7 dní)"):
        tabs = st.tabs(list(w_data.keys()))
        for i, (mesto, d) in enumerate(w_data.items()):
            with tabs[i]:
                if d["tyden"]: st.table(pd.DataFrame(d["tyden"]))
                else: st.error("Data nejsou momentálně k dispozici.")

    # --- OZNÁMENÍ ---
    st.markdown("<h3 style='text-align:center; margin-top:30px;'>📢 Důležitá Oznámení</h3>", unsafe_allow_html=True)
    df_oznameni = nacti_data_sheets("List 2")
    if not df_oznameni.empty:
        for zprava in df_oznameni['zprava'].dropna():
            st.info(zprava)
    else: st.write("<p style='text-align:center; color:gray;'>Žádná nová hlášení.</p>", unsafe_allow_html=True)

    # --- NEWS TICKER (SPODNÍ LIŠTA) ---
    seznam_zprav = nacti_zpravy_agregovane()
    idx = st.session_state.news_index % len(seznam_zprav)
    
    st.markdown(f'<div class="news-ticker">🗞️ {seznam_zprav[idx]}</div>', unsafe_allow_html=True)

    # Časovač pro plynulou rotaci
    time.sleep(5)
    st.session_state.news_index += 1
    st.rerun()

# =================================================================
# 6. STRÁNKA: AI CHAT (GEMINI 1.5 FLASH)
# =================================================================
elif st.session_state.page == "AI Chat":
    st.markdown("<h1 style='text-align:center;'>💬 Kvádr AI Asistent 2.0</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#3b82f6;'>Model: Gemini 1.5 Flash | Napojeno na interní data</p>", unsafe_allow_html=True)
    
    # Historie chatu
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Vstup uživatele
    if prompt := st.chat_input("Zeptejte se na cokoli k projektu..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Kvádr analyzuje data..."):
                try:
                    # Načtení kontextu z Listu 1
                    df_context = nacti_data_sheets("List 1")
                    kontext_text = " ".join(df_context['zprava'].astype(str).tolist())
                    
                    sys_instr = f"Jsi inteligentní asistent projektu Kvádr 2.0. Zde jsou tvá data: {kontext_text}. Buď věcný, lidský a profesionální."
                    
                    model = genai.GenerativeModel(st.session_state.model_name, system_instruction=sys_instr)
                    
                    # Příprava historie
                    history_gemini = []
                    for h in st.session_state.chat_history[:-1]:
                        history_gemini.append({"role": "user" if h["role"]=="user" else "model", "parts": [h["content"]]})
                    
                    chat = model.start_chat(history=history_gemini)
                    response = chat.send_message(prompt)
                    
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                    st.rerun()
                except Exception as e:
                    st.error(f"Omlouvám se, nastala technická chyba: {e}")

    if st.button("🗑️ Vymazat historii konverzace"):
        st.session_state.chat_history = []
        st.rerun()
