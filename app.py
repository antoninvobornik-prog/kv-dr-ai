import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# =================================================================
# 1. KONFIGURACE A STAV (Verze 2.0)
# =================================================================
st.set_page_config(
    page_title="Kvádr Portál 2.0", 
    layout="wide", 
    page_icon="🏙️", 
    initial_sidebar_state="collapsed"
)

# Skrytí postranního panelu
st.markdown("<style>section[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)

if "page" not in st.session_state: st.session_state.page = "Domů"
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "news_index" not in st.session_state: st.session_state.news_index = 0
if "cache_zpravy" not in st.session_state: st.session_state.cache_zpravy = []
if "posledni_update_zprav" not in st.session_state: st.session_state.posledni_update_zprav = 0

# OPRAVA: Konfigurace Google AI s přesným názvem modelu
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Používáme přesný identifikátor modelu, aby nevznikala chyba NotFound
    MODEL_ID = "models/gemini-1.5-flash"
except Exception as e:
    st.error(f"AI Konfigurace selhala: {e}")

# =================================================================
# 2. LOGICKÉ FUNKCE
# =================================================================

def get_weather_desc(code):
    """Převodník kódů počasí - opraveno, aby nehlásil Neznámé."""
    mapping = {
        0: "Jasno ☀️", 1: "Převážně jasno 🌤️", 2: "Polojasno ⛅", 3: "Zataženo ☁️",
        45: "Mlha 🌫️", 48: "Námraza 🌫️", 51: "Mírné mrholení 🌦️", 53: "Mrholení 🌦️", 
        55: "Silné mrholení 🌧️", 61: "Slabý déšť 🌧️", 63: "Déšť 🌧️", 65: "Silný déšť 🌊",
        66: "Mrznoucí déšť 🧊", 71: "Sněžení ❄️", 80: "Slabé přeháňky 🌦️", 
        81: "Přeháňky 🌧️", 82: "Silné přeháňky 🌊", 95: "Bouřka ⚡"
    }
    return mapping.get(code, f"Lokalizuji ({code})")

@st.cache_data(ttl=600)
def nacti_kompletni_pocasi():
    mesta = {
        "Nové Město n. M.": (50.344, 16.151), 
        "Rychnov n. Kn.": (50.162, 16.274),
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
                    "Stav": get_weather_desc(r['daily']['weathercode'][i]),
                    "Max": f"{round(r['daily']['temperature_2m_max'][i])}°C",
                    "Min": f"{round(r['daily']['temperature_2m_min'][i])}°C",
                    "Srážky": f"{r['daily']['precipitation_probability_max'][i]}%"
                })
            
            vysledek[m] = {
                "aktualni": f"{round(r['current']['temperature_2m'])}°C",
                "popis": get_weather_desc(r['current']['weathercode']),
                "tyden": predpoved
            }
        except:
            vysledek[m] = {"aktualni": "??", "popis": "Chyba", "tyden": []}
    return vysledek

def nacti_zpravy_agregovane():
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
            for item in root.findall('.//item')[:10]:
                title = item.find('title').text
                vystup.append(f"{label}: {title}")
        except: continue
            
    if vystup:
        st.session_state.cache_zpravy = vystup
        st.session_state.posledni_update_zprav = ted
        return vystup
    return ["Aktualizuji zpravodajství..."]

def nacti_data_sheets(list_name):
    try:
        url = st.secrets["GSHEET_URL"]
        sheet_id = url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(list_name)}"
        return pd.read_csv(csv_url)
    except:
        return pd.DataFrame(columns=['zprava'])

# =================================================================
# 3. VZHLED (CSS)
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
    }
    .weather-card {
        background: rgba(255, 255, 255, 0.07); padding: 15px;
        border-radius: 12px; text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
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
# 5. DOMOVSKÁ OBRAZOVKA (Verze 2.0)
# =================================================================
if st.session_state.page == "Domů":
    st.markdown("<h1 style='text-align:center;'>🏙️ Kvádr Portál 2.0</h1>", unsafe_allow_html=True)
    
    # Počasí pro 5 měst
    w_data = nacti_kompletni_pocasi()
    w_cols = st.columns(len(w_data))
    for i, (mesto, d) in enumerate(w_data.items()):
        w_cols[i].markdown(f"""
        <div class='weather-card'>
            <div style='color: #3b82f6; font-size: 0.8em;'>{mesto}</div>
            <div style='font-size: 1.8em; font-weight: bold;'>{d['aktualni']}</div>
            <div style='font-size: 0.85em;'>{d['popis']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.write("##")
    with st.expander("📅 Týdenní předpověď (včetně Rychnova)"):
        tabs = st.tabs(list(w_data.keys()))
        for i, (mesto, d) in enumerate(w_data.items()):
            with tabs[i]:
                if d["tyden"]: st.table(pd.DataFrame(d["tyden"]))

    # Oznámení
    df_oznameni = nacti_data_sheets("List 2")
    if not df_oznameni.empty:
        for zprava in df_oznameni['zprava'].dropna():
            st.info(zprava)

    # Spodní lišta se zprávami
    seznam_zprav = nacti_zpravy_agregovane()
    idx = st.session_state.news_index % len(seznam_zprav)
    st.markdown(f'<div class="news-ticker">🗞️ {seznam_zprav[idx]}</div>', unsafe_allow_html=True)

    time.sleep(5)
    st.session_state.news_index += 1
    st.rerun()

# =================================================================
# 6. AI CHAT (Opravené volání modelu)
# =================================================================
elif st.session_state.page == "AI Chat":
    st.markdown("<h1 style='text-align:center;'>💬 Kvádr AI Asistent 2.0</h1>", unsafe_allow_html=True)
    
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Zeptejte se na projekt..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Kvádr přemýšlí..."):
                try:
                    df_context = nacti_data_sheets("List 1")
                    kontext_text = " ".join(df_context['zprava'].astype(str).tolist())
                    
                    # OPRAVENÉ VOLÁNÍ: model_name používá MODEL_ID definovaný nahoře
                    model = genai.GenerativeModel(
                        model_name=MODEL_ID,
                        system_instruction=f"Jsi asistent projektu Kvádr 2.0. Zde jsou tvá data: {kontext_text}."
                    )
                    
                    history_gemini = []
                    for h in st.session_state.chat_history[:-1]:
                        history_gemini.append({"role": "user" if h["role"]=="user" else "model", "parts": [h["content"]]})
                    
                    chat = model.start_chat(history=history_gemini)
                    response = chat.send_message(prompt)
                    
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                    st.rerun()
                except Exception as e:
                    st.error(f"Chyba komunikace s Google AI: {e}")
                    st.info("Tip: Zkontroluj, zda máš v Secrets správně nastavený GOOGLE_API_KEY.")
