import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# =================================================================
# 1. HLAVNÍ KONFIGURACE A CHYTRÝ VÝBĚR MODELU
# =================================================================
st.set_page_config(
    page_title="Kvádr Portál 2.0", 
    layout="wide", 
    page_icon="🏙️", 
    initial_sidebar_state="collapsed"
)

# Úplné skrytí postranního panelu pro čistý design
st.markdown("<style>section[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)

# Inicializace stavů aplikace (session state)
if "page" not in st.session_state: st.session_state.page = "Domů"
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "news_index" not in st.session_state: st.session_state.news_index = 0
if "active_model" not in st.session_state: st.session_state.active_model = None

def najdi_funkcni_model():
    """Dynamicky ověří dostupné modely u Googlu, aby se předešlo chybě 404."""
    if st.session_state.active_model:
        return st.session_state.active_model
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        modely = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Preferované modely v pořadí
        priority = ["models/gemini-1.5-flash", "models/gemini-1.5-flash-latest", "models/gemini-pro"]
        for p in priority:
            if p in modely:
                st.session_state.active_model = p
                return p
        return modely[0] if modely else "gemini-1.5-flash"
    except Exception as e:
        return "gemini-1.5-flash"

# =================================================================
# 2. DATOVÉ FUNKCE (POČASÍ, ZPRÁVY, TABULKY)
# =================================================================

def get_weather_desc(code):
    """Kompletní mapování kódů WMO na české popisky s emoji."""
    mapping = {
        0: "Jasno ☀️", 1: "Skoro jasno 🌤️", 2: "Polojasno ⛅", 3: "Zataženo ☁️",
        45: "Mlha 🌫️", 48: "Námraza 🌫️", 51: "Mírné mrholení 🌦️", 53: "Mrholení 🌦️",
        55: "Silné mrholení 🌧️", 61: "Slabý déšť 🌧️", 63: "Déšť 🌧️", 65: "Silný déšť 🌊",
        71: "Sněžení ❄️", 80: "Slabé přeháňky 🌧️", 81: "Přeháňky 🌧️", 95: "Bouřka ⚡"
    }
    return mapping.get(code, f"Kód {code}")

@st.cache_data(ttl=600)
def nacti_kompletni_pocasi():
    mesta = {
        "Nové Město n. M.": (50.344, 16.151), 
        "Rychnov n. Kn.": (50.162, 16.274), 
        "Bělá pod Bezdězem": (50.534, 14.807), 
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
            vysledek[m] = {"aktualni": "??", "popis": "Není spojení", "tyden": []}
    return vysledek

@st.cache_data(ttl=600)
def nacti_zpravy_rss():
    vystup = []
    zdroje = ["https://ct24.ceskatelevize.cz/rss/hlavni-zpravy", "https://www.seznamzpravy.cz/rss"]
    for url in zdroje:
        try:
            r = requests.get(url, timeout=5)
            root = ET.fromstring(r.content)
            for item in root.findall('.//item')[:8]:
                vystup.append(item.find('title').text)
        except: continue
    return vystup if vystup else ["Zprávy se nepodařilo aktualizovat..."]

def nacti_data_z_gsheets(list_name):
    try:
        url = st.secrets["GSHEET_URL"]
        sheet_id = url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(list_name)}"
        return pd.read_csv(csv_url)
    except:
        return pd.DataFrame(columns=['zprava'])

# =================================================================
# 3. DESIGN A STYLY (CSS)
# =================================================================
st.markdown("""
<style>
    .stApp { background: radial-gradient(circle at center, #1a2c4e 0%, #070b14 100%); color: white; }
    .news-ticker {
        position: fixed; bottom: 0; left: 0; width: 100%;
        background: rgba(0, 45, 110, 0.98); color: white;
        padding: 18px; text-align: center;
        border-top: 3px solid #3b82f6; font-weight: bold;
        z-index: 9999; font-size: 21px;
    }
    .weather-card {
        background: rgba(255, 255, 255, 0.08); padding: 18px;
        border-radius: 15px; text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.15);
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
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
# 5. STRÁNKA: DOMŮ
# =================================================================
if st.session_state.page == "Domů":
    st.markdown("<h1 style='text-align:center;'>🏙️ Kvádr Portál 2.0</h1>", unsafe_allow_html=True)
    
    # Horní řada s počasím
    data_pocasi = nacti_kompletni_pocasi()
    cols = st.columns(len(data_pocasi))
    for i, (mesto, d) in enumerate(data_pocasi.items()):
        cols[i].markdown(f"""
        <div class='weather-card'>
            <div style='color: #3b82f6; font-size: 0.85em; margin-bottom: 5px;'>{mesto}</div>
            <div style='font-size: 2em; font-weight: bold;'>{d['aktualni']}</div>
            <div style='font-size: 0.9em; opacity: 0.8;'>{d['popis']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.write("##")
    
    # Detailní předpověď (Tvůj požadovaný text)
    with st.expander("📅 Zobrazit detailní předpověď a srážky pro všechny lokality"):
        tabs = st.tabs(list(data_pocasi.keys()))
        for i, (mesto, d) in enumerate(data_pocasi.items()):
            with tabs[i]:
                if d["tyden"]:
                    st.table(pd.DataFrame(d["tyden"]))
                else:
                    st.error("Nepodařilo se načíst detailní data.")

    # Oznámení z Listu 2
    df_ozn = nacti_data_z_gsheets("List 2")
    if not df_ozn.empty:
        st.write("### 🔔 Aktuální info")
        for msg in df_ozn['zprava'].dropna():
            st.info(msg)

    # Běžící zprávy s 8sekundovým intervalem
    zpravy = nacti_zpravy_rss()
    idx = st.session_state.news_index % len(zpravy)
    st.markdown(f'<div class="news-ticker">🗞️ {zpravy[idx]}</div>', unsafe_allow_html=True)

    time.sleep(8) # Tady je tvých 8 sekund
    st.session_state.news_index += 1
    st.rerun()

# =================================================================
# 6. STRÁNKA: AI CHAT
# =================================================================
else:
    model_id = najdi_funkcni_model()
    st.markdown("<h1 style='text-align:center;'>💬 Kvádr AI Asistent 2.0</h1>", unsafe_allow_html=True)
    st.caption(f"Aktivní inteligence: {model_id}")
    
    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    if prompt := st.chat_input("Zeptejte se na cokoliv ohledně projektu..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                df_kontext = nacti_data_z_gsheets("List 1")
                kontext = " ".join(df_kontext['zprava'].astype(str).tolist())
                
                ai = genai.GenerativeModel(
                    model_name=model_id,
                    system_instruction=f"Jsi mozkem projektu Kvádr 2.0. Pracuj s těmito daty: {kontext}"
                )
                
                # Převod historie pro Gemini
                history = []
                for h in st.session_state.chat_history[:-1]:
                    role = "user" if h["role"] == "user" else "model"
                    history.append({"role": role, "parts": [h["content"]]})
                
                chat = ai.start_chat(history=history)
                odpoved = chat.send_message(prompt)
                
                st.markdown(odpoved.text)
                st.session_state.chat_history.append({"role": "assistant", "content": odpoved.text})
                st.rerun()
            except Exception as e:
                st.error(f"Chyba AI modulu: {e}")
