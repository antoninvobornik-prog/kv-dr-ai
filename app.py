import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import streamlit.components.v1 as components

# --- KONFIGURACE A DESIGN ---
st.set_page_config(page_title="Kvádr Portál 6.0", layout="wide", initial_sidebar_state="collapsed")

# Definice měst pro celou aplikaci
MESTA = {
    "Nové Město": (50.34, 16.15),
    "Rychnov": (50.16, 16.27),
    "Bělá": (50.53, 14.80),
    "Praha": (50.07, 14.43),
    "Hradec Králové": (50.21, 15.83),
    "Pardubice": (50.03, 15.77)
}

st.markdown("""
<style>
    section[data-testid="stSidebar"] {display: none;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp { background: #070b14; color: white; }
    
    /* Design tlačítek */
    .stButton>button {
        background: linear-gradient(90deg, #ff4b4b, #ff7575);
        color: white; border-radius: 12px; border: none;
        padding: 15px; font-weight: bold; width: 100%;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.3);
    }

    /* Design pro chatové zprávy */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.05) !important;
        border-radius: 15px !important;
        margin-bottom: 10px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    
    /* Úprava vstupu chatu */
    .stChatInput {
        background-color: #111827 !important;
        border-radius: 15px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- LOGIKA POČASÍ ---
def get_weather_info(code):
    icons = {0:"☀️", 1:"🌤️", 2:"⛅", 3:"☁️", 45:"🌫️", 51:"🌦️", 61:"🌧️", 71:"❄️", 80:"🌧️", 95:"⚡"}
    descs = {0:"Jasno", 1:"Skoro jasno", 2:"Polojasno", 3:"Zataženo", 45:"Mlha", 51:"Mrholení", 61:"Déšť", 71:"Sněžení", 80:"Přeháňky", 95:"Bouřka"}
    return icons.get(code, "🌡️"), descs.get(code, "Neznámé")

@st.cache_data(ttl=600)
def fetch_weather_cards():
    cards_html = ""
    for m, (lat, lon) in list(MESTA.items())[:5]: # Jen prvních 5 pro karty
        try:
            r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&timezone=auto", timeout=5).json()
            curr = r['current']
            icon, _ = get_weather_info(curr['weathercode'])
            cards_html += f"""
            <div style="flex: 0 0 auto; width: 100px; background: rgba(255,255,255,0.07); border-radius: 12px; padding: 10px; text-align: center; margin-right: 10px; border: 1px solid rgba(255,255,255,0.1);">
                <div style="font-size: 9px; color: #4dabff; font-weight: bold; margin-bottom: 5px;">{m.upper()}</div>
                <div style="font-size: 24px; font-weight: bold;">{round(curr['temperature_2m'])}°</div>
                <div style="font-size: 15px; margin-top: 3px;">{icon}</div>
            </div>
            """
        except: pass
    return f'<div style="display: flex; overflow-x: auto; padding: 10px 0;">{cards_html}</div>'

# --- HLAVNÍ STRÁNKA ---
if "page" not in st.session_state: st.session_state.page = "Domů"

if st.session_state.page == "Domů":
    if st.button("💬 OTEVŘÍT AI ASISTENTA"):
        st.session_state.page = "AI Chat"
        st.rerun()

    components.html(fetch_weather_cards(), height=115)

    # --- DETAILNÍ PŘEDPOVĚĎ S VÝBĚREM MĚSTA ---
    with st.expander("📅 Podrobná předpověď a radar"):
        vybrane_mesto = st.selectbox("Vyberte město pro detaily:", list(MESTA.keys()))
        lat, lon = MESTA[vybrane_mesto]
        
        try:
            res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=auto").json()
            daily = res['daily']
            df = pd.DataFrame({
                "Datum": [datetime.strptime(d, "%Y-%m-%d").strftime("%d.%m.") for d in daily['time']],
                "Den (°C)": daily['temperature_2m_max'],
                "Noc (°C)": daily['temperature_2m_min'],
                "Stav": [get_weather_info(c)[1] for c in daily['weathercode']]
            })
            st.table(df)
        except:
            st.error("Chyba při načítání dat.")
            
        st.link_button(f"🌐 Otevřít radar pro {vybrane_mesto}", f"https://www.windy.com/{lat}/{lon}")

    st.markdown("---")
    
    # Oznámení
    try:
        sheet_url = f"https://docs.google.com/spreadsheets/d/{st.secrets['GSHEET_URL'].split('/d/')[1].split('/')[0]}/gviz/tq?tqx=out:csv&sheet=List%202"
        news_data = pd.read_csv(sheet_url)
        for val in news_data['zprava'].dropna():
            st.warning(f"🔔 {val}")
    except: pass

    # NEWS TICKER (55px odspodu)
    try:
        rss = ET.fromstring(requests.get("https://ct24.ceskatelevize.cz/rss/hlavni-zpravy", timeout=5).content)
        msg = rss.find('.//item/title').text
        st.markdown(f"""
            <div style="position: fixed; bottom: 55px; left: 10px; right: 10px; 
                        background: #002d6e; color: white; padding: 12px; 
                        border-radius: 15px; border: 1px solid #3b82f6; 
                        z-index: 999; text-align: center; font-size: 14px; font-family: sans-serif;">
                🗞️ {msg}
            </div>
        """, unsafe_allow_html=True)
    except: pass

# --- CHAT STRÁNKA (S DESIGNEM) ---
else:
    st.markdown("<h3 style='text-align: center;'>🤖 Kvádr AI Asistent</h3>", unsafe_allow_html=True)
    if st.button("🏠 ZPĚT NA PORTÁL"):
        st.session_state.page = "Domů"
        st.rerun()
    
    st.write("---")
    
    # Příklad designových zpráv
    with st.chat_message("assistant"):
        st.write("Dobrý den! Jsem váš Kvádr asistent. Jak vám mohu dnes pomoci?")
    
    if prompt := st.chat_input("Napište zprávu..."):
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("assistant"):
            st.write(f"Zpracovávám váš dotaz ohledně: {prompt}")
