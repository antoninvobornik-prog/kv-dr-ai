import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# =================================================================
# 1. KONFIGURACE A STAV APLIKACE
# =================================================================
st.set_page_config(
    page_title="Kvádr Portál 2.1", 
    layout="wide", 
    page_icon="🏙️", 
    initial_sidebar_state="collapsed"
)

# Skrytí bočního menu pro čistý vzhled
st.markdown("<style>section[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)

# Inicializace session stavů (paměť aplikace)
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

# Konfigurace AI
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    if "model_name" not in st.session_state:
        st.session_state.model_name = "gemini-1.5-flash"
except Exception as e:
    st.error(f"Chyba konfigurace AI: {e}")

# =================================================================
# 2. DATOVÉ FUNKCE (LOGIKA)
# =================================================================

def get_weather_desc(code):
    """Překlad kódů počasí do češtiny s ikonami."""
    mapping = {
        0: "Jasno ☀️", 1: "Převážně jasno 🌤️", 2: "Polojasno ⛅", 3: "Zataženo ☁️",
        45: "Mlha 🌫️", 48: "Námraza 🌫️", 51: "Mírné mrholení 🌦️", 53: "Mrholení 🌦️",
        55: "Silné mrholení 🌧️", 61: "Slabý déšť 🌧️", 63: "Déšť 🌧️", 65: "Silný déšť 🌊",
        71: "Slabé sněžení ❄️", 73: "Sněžení ❄️", 75: "Silné sněžení ☃️",
        95: "Bouřka ⚡", 96: "Bouřka s kroupami ⛈️"
    }
    return mapping.get(code, "Neznámé")

@st.cache_data(ttl=600)
def nacti_kompletni_pocasi():
    """Načte počasí pro všechny lokality najednou."""
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
            
            předpověď = []
            for i in range(7):
                datum_obj = datetime.now() + timedelta(days=i)
                předpověď.append({
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
                "tyden": předpověď
            }
        except:
            vysledek[m] = {"aktualni": "??", "popis": "Chyba dat", "tyden": []}
    return vysledek

def nacti_zpravy_agregovane():
    """Získá zprávy z ČT24 a Seznamu, ukládá do paměti pro rychlost."""
    ted = time.time()
    # Pokud máme zprávy v paměti a jsou mladší než 10 minut, nezatěžujeme síť
    if st.session_state.cache_zpravy and (ted - st.session_state.posledni_update_zprav < 600):
        return st.session_state.cache_zpravy

    zdroje = [
        ("ČT24", "https://ct24.ceskatelevize.cz/rss/hlavni-zpravy"),
        ("Seznam", "https://www.seznamzpravy.cz/rss")
    ]
    vsechny_titulky = []
    
    for label, url in zdroje:
        try:
            r = requests.get(url, timeout=4)
            root = ET.fromstring(r.content)
            for item in root.findall('.//item')[:10]:
                title = item.find('title').text
                vsechny_titulky.append(f"{label}: {title}")
        except:
            continue
            
    if vsechny_titulky:
        st.session_state.cache_zpravy = vsechny_titulky
        st.session_state.posledni_update_zprav = ted
        return vsechny_titulky
    return ["Načítám čerstvé zprávy..."]

def nacti_data_sheets(list_name):
    """Načte data z Google Sheets."""
    try:
        url = st.secrets["GSHEET_URL"]
        sheet_id = url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(list_name)}"
        return pd.read_csv(csv_url)
    except:
        return pd.DataFrame(columns=['zprava'])

# =================================================================
# 3. UI A DESIGN (CSS)
# =================================================================
st.markdown("""
<style>
    .stApp {
        background: radial-gradient(circle at center, #1a2c4e 0%, #070b14 100%);
        color: white;
    }
    .news-ticker {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background: rgba(0, 45, 110, 0.98);
        color: #ffffff;
        padding: 18px;
        text-align: center;
        border-top: 3px solid #3b82f6;
        font-weight: bold;
        z-index: 9999;
        font-size: 20px;
        box-shadow: 0px -5px 15px rgba(0,0,0,0.5);
    }
    .weather-card {
        background: rgba(255, 255, 255, 0.05);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: 0.3s;
    }
    .weather-card:hover {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid #3b82f6;
    }
    .stButton>button {
        border-radius: 10px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# =================================================================
# 4. NAVIGACE MEZI STRÁNKAMI
# =================================================================
nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
with nav_col2:
    if st.session_state.page == "Domů":
        if st.button("💬 VSTOUPIT DO AI CHATU", use_container_width=True, type="primary"):
            st.session_state.page = "AI Chat"
            st.rerun()
    else:
        if st.button("🏠 NÁVRAT NA HLAVNÍ PANEL", use_container_width=True):
            st.session_state.page = "Domů"
            st.rerun()

# =================================================================
# 5. STRÁNKA: DOMOVSKÝ PANEL
# =================================================================
if st.session_state.page == "Domů":
    st.markdown("<h1 style='text-align:center; margin-bottom:30px;'>🏙️ Kvádr Portál 2.1</h1>", unsafe_allow_html=True)
    
    # --- SEKCE POČASÍ ---
    w_data = nacti_kompletni_pocasi()
    w_cols = st.columns(4)
    for i, (mesto, d) in enumerate(w_data.items()):
        w_cols[i].markdown(f"""
        <div class='weather-card'>
            <div style='font-size: 1.1em; color: #3b82f6;'>{mesto}</div>
            <div style='font-size: 2.2em; font-weight: bold;'>{d['aktualni']}</div>
            <div style='font-size: 0.9em;'>{d['popis']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.write("##")
    with st.expander("📅 Zobrazit detailní předpověď a srážky pro všechny lokality"):
        tabs = st.tabs(list(w_data.keys()))
        for i, (mesto, d) in enumerate(w_data.items()):
            with tabs[i]:
                if d["tyden"]:
                    df_weather = pd.DataFrame(d["tyden"])
                    st.table(df_weather)
                else:
                    st.error("Nepodařilo se načíst detailní předpověď.")

    # --- SEKCE OZNÁMENÍ ---
    st.markdown("<h2 style='text-align:center;'>📢 Interní Oznámení</h2>", unsafe_allow_html=True)
    df_oznameni = nacti_data_sheets("List 2")
    if not df_oznameni.empty:
        for zprava in df_oznameni['zprava'].dropna():
            st.info(zprava)
    else:
        st.write("<p style='text-align:center; color:gray;'>Žádná nová oznámení.</p>", unsafe_allow_html=True)

    # --- NEWS TICKER (ČT24 + SEZNAM) ---
    zpravy_list = nacti_zpravy_agregovane()
    idx = st.session_state.news_index % len(zpravy_list)
    vybrana_zprava = zpravy_list[idx]
    
    st.markdown(f"""
        <div class="news-ticker">
            🗞️ {vybrana_zprava}
        </div>
    """, unsafe_allow_html=True)

    # Automatické obnovení každých 5 sekund
    time.sleep(5)
    st.session_state.news_index += 1
    st.rerun()

# =================================================================
# 6. STRÁNKA: AI CHAT S KONTEXTEM
# =================================================================
elif st.session_state.page == "AI Chat":
    st.markdown("<h1 style='text-align:center;'>💬 Kvádr AI Asistent</h1>", unsafe_allow_html=True)
    
    # Tlačítka pro správu chatu
    chat_btns = st.columns([0.8, 0.2])
    with chat_btns[1]:
        if st.button("🗑️ Vymazat chat"):
            st.session_state.chat_history = []
            st.rerun()

    # Zobrazení historie
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Vstup od uživatele
    if prompt := st.chat_input("Napište dotaz k projektu..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Kvádr přemýšlí..."):
                try:
                    # Načtení kontextu z tabulky
                    df_context = nacti_data_sheets("List 1")
                    knowledge_base = " ".join(df_context['zprava'].astype(str).tolist())
                    
                    sys_prompt = f"Jsi seriózní asistent projektu Kvádr. Zde jsou tvé interní informace: {knowledge_base}. Odpovídej věcně a česky."
                    
                    model = genai.GenerativeModel(
                        st.session_state.model_name,
                        system_instruction=sys_prompt
                    )
                    
                    # Formátování historie pro Gemini
                    gemini_history = []
                    for h in st.session_state.chat_history[:-1]:
                        role = "user" if h["role"] == "user" else "model"
                        gemini_history.append({"role": role, "parts": [h["content"]]})
                    
                    chat = model.start_chat(history=gemini_history)
                    response = chat.send_message(prompt)
                    
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                    st.rerun()
                except Exception as e:
                    st.error(f"Omlouvám se, došlo k chybě: {e}")
