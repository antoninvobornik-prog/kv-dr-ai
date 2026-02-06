import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# =================================================================
# 1. KONFIGURACE A CHYTRÝ VÝBĚR MODELU
# =================================================================
st.set_page_config(
    page_title="Kvádr Portál 2.0", 
    layout="wide", 
    page_icon="🏙️", 
    initial_sidebar_state="collapsed"
)

# Skrytí postranního panelu
st.markdown("<style>section[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)

# Inicializace stavů aplikace
if "page" not in st.session_state: st.session_state.page = "Domů"
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "news_index" not in st.session_state: st.session_state.news_index = 0
if "active_model" not in st.session_state: st.session_state.active_model = None

def najdi_funkcni_model():
    """Najde v seznamu Googlu model, který skutečně existuje a funguje."""
    if st.session_state.active_model:
        return st.session_state.active_model
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        # Získáme seznam modelů, které podporují generování obsahu
        dostupne = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Seznam prioritních názvů (Google je občas mění)
        priority = ["models/gemini-1.5-flash", "models/gemini-1.5-flash-latest", "models/gemini-pro"]
        for p in priority:
            if p in dostupne:
                st.session_state.active_model = p
                return p
        
        return dostupne[0] if dostupne else "gemini-1.5-flash"
    except Exception as e:
        return f"Chyba: {e}"

# =================================================================
# 2. POMOCNÉ FUNKCE (POČASÍ, ZPRÁVY, SHEETS)
# =================================================================

def get_weather_desc(code):
    """Kompletní převodník kódů počasí na text a emoji."""
    mapping = {
        0: "Jasno ☀️", 1: "Převážně jasno 🌤️", 2: "Polojasno ⛅", 3: "Zataženo ☁️",
        45: "Mlha 🌫️", 48: "Námraza 🌫️", 51: "Mírné mrholení 🌦️", 53: "Mrholení 🌦️", 
        55: "Silné mrholení 🌧️", 61: "Slabý déšť 🌧️", 63: "Déšť 🌧️", 65: "Silný déšť 🌊",
        66: "Mrznoucí déšť 🧊", 71: "Sněžení ❄️", 80: "Slabé přeháňky 🌦️", 
        81: "Přeháňky 🌧️", 82: "Silné přeháňky 🌊", 95: "Bouřka ⚡"
    }
    return mapping.get(code, f"Neznámé ({code})")

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
            
            tyden = []
            for i in range(7):
                datum_obj = datetime.now() + timedelta(days=i)
                tyden.append({
                    "Den": dny_cz[datum_obj.weekday()],
                    "Stav": get_weather_desc(r['daily']['weathercode'][i]),
                    "Max": f"{round(r['daily']['temperature_2m_max'][i])}°C",
                    "Min": f"{round(r['daily']['temperature_2m_min'][i])}°C",
                    "Srážky": f"{r['daily']['precipitation_probability_max'][i]}%"
                })
            
            vysledek[m] = {
                "aktualni": f"{round(r['current']['temperature_2m'])}°C",
                "popis": get_weather_desc(r['current']['weathercode']),
                "tyden": tyden
            }
        except:
            vysledek[m] = {"aktualni": "??", "popis": "Chyba spojení", "tyden": []}
    return vysledek

@st.cache_data(ttl=600)
def nacti_zpravy_rss():
    vystup = []
    zdroje = [
        ("ČT24", "https://ct24.ceskatelevize.cz/rss/hlavni-zpravy"),
        ("Seznam Zprávy", "https://www.seznamzpravy.cz/rss")
    ]
    for label, url in zdroje:
        try:
            r = requests.get(url, timeout=5)
            root = ET.fromstring(r.content)
            for item in root.findall('.//item')[:10]:
                vystup.append(f"{label}: {item.find('title').text}")
        except: continue
    return vystup if vystup else ["Zprávy se nepodařilo načíst..."]

def nacti_data_z_tabulky(list_name):
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
# 5. DOMOVSKÁ OBRAZOVKA (PLNÁ VERZE)
# =================================================================
if st.session_state.page == "Domů":
    st.markdown("<h1 style='text-align:center;'>🏙️ Kvádr Portál 2.0</h1>", unsafe_allow_html=True)
    
    # Počasí
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
    with st.expander("📅 Podrobná týdenní předpověď (včetně Rychnova)"):
        tabs = st.tabs(list(w_data.keys()))
        for i, (mesto, d) in enumerate(w_data.items()):
            with tabs[i]:
                if d["tyden"]:
                    st.table(pd.DataFrame(d["tyden"]))
                else:
                    st.warning("Data pro tento region nejsou momentálně dostupná.")

    # Oznámení z Listu 2
    df_oznameni = nacti_data_z_tabulky("List 2")
    if not df_oznameni.empty:
        st.write("### 🔔 Aktuální oznámení")
        for zprava in df_oznameni['zprava'].dropna():
            st.info(zprava)

    # Běžící lišta zpráv
    seznam_zprav = nacti_zpravy_rss()
    idx = st.session_state.news_index % len(seznam_zprav)
    st.markdown(f'<div class="news-ticker">🗞️ {seznam_zprav[idx]}</div>', unsafe_allow_html=True)

    time.sleep(5)
    st.session_state.news_index += 1
    st.rerun()

# =================================================================
# 6. AI CHAT (DYNAMICKÝ MODEL)
# =================================================================
elif st.session_state.page == "AI Chat":
    m_name = najdi_funkcni_model()
    st.markdown("<h1 style='text-align:center;'>💬 Kvádr AI Asistent 2.0</h1>", unsafe_allow_html=True)
    st.caption(f"Status: Online | Model: {m_name}")
    
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Zeptejte se na projekt..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Kvádr analyzuje data..."):
                try:
                    df_context = nacti_data_z_tabulky("List 1")
                    kontext_text = " ".join(df_context['zprava'].astype(str).tolist())
                    
                    model = genai.GenerativeModel(
                        model_name=m_name,
                        system_instruction=f"Jsi asistent projektu Kvádr 2.0. Zde jsou tvá data: {kontext_text}. Odpovídej věcně a přátelsky."
                    )
                    
                    history_gemini = []
                    for h in st.session_state.chat_history[:-1]:
                        history_gemini.append({
                            "role": "user" if h["role"]=="user" else "model", 
                            "parts": [h["content"]]
                        })
                    
                    chat = model.start_chat(history=history_gemini)
                    response = chat.send_message(prompt)
                    
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                    st.rerun()
                except Exception as e:
                    st.error(f"Omlouvám se, došlo k chybě: {e}")
