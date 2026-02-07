import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# --- KONFIGURACE STRÁNKY ---
st.set_page_config(page_title="Kvádr Portál", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    section[data-testid="stSidebar"] {display: none;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp { background: #070b14; color: white; }
    .block-container { padding-top: 1rem; padding-bottom: 8rem; }
    
    /* Design tlačítka AI */
    .stButton>button {
        background: linear-gradient(90deg, #ff4b4b, #ff7575);
        color: white;
        border-radius: 12px;
        padding: 15px;
        font-weight: bold;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNKCE PRO POČASÍ ---
def get_weather_info(code):
    icons = {0:"☀️", 1:"🌤️", 2:"⛅", 3:"☁️", 45:"🌫️", 51:"🌦️", 61:"🌧️", 71:"❄️", 80:"🌧️", 95:"⚡"}
    descs = {0:"Jasno", 1:"Skoro jasno", 2:"Polojasno", 3:"Zataženo", 45:"Mlha", 51:"Mrholení", 61:"Déšť", 71:"Sněžení", 80:"Přeháňky", 95:"Bouřka"}
    return icons.get(code, "🌡️"), descs.get(code, "Neznámé")

@st.cache_data(ttl=600)
def fetch_weather_cards():
    mesta = {"Nové Město": (50.34, 16.15), "Rychnov": (50.16, 16.27), "Bělá": (50.53, 14.80), "Praha": (50.07, 14.43), "Hradec": (50.21, 15.83)}
    cards_html = ""
    for m, (lat, lon) in mesta.items():
        try:
            r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&timezone=auto", timeout=5).json()
            curr = r['current']
            icon, desc = get_weather_info(curr['weathercode'])
            cards_html += f"""
            <div style="flex: 0 0 auto; width: 100px; background: rgba(255,255,255,0.08); border-radius: 12px; padding: 10px; text-align: center; margin-right: 10px; border: 1px solid rgba(255,255,255,0.1);">
                <div style="font-size: 10px; color: #4dabff; font-weight: bold;">{m.upper()}</div>
                <div style="font-size: 22px; font-weight: bold; margin: 5px 0;">{round(curr['temperature_2m'])}°</div>
                <div style="font-size: 10px; opacity: 0.8;">{icon}</div>
            </div>
            """
        except: pass
    return f'<div style="display: flex; overflow-x: auto; padding: 10px 0;">{cards_html}</div>'

# --- HLAVNÍ STRÁNKA ---
if "page" not in st.session_state: st.session_state.page = "Domů"

if st.session_state.page == "Domů":
    # Horní tlačítko
    if st.button("💬 OTEVŘÍT AI ASISTENTA"):
        st.session_state.page = "AI Chat"
        st.rerun()

    # Horizontální karty počasí
    components.html(fetch_weather_cards(), height=110)

    # PODROBNÁ PŘEDPOVĚĎ (EXPANDER PODLE OBRÁZKU)
    with st.expander("📅 Podrobná týdenní předpověď (včetně Rychnova)"):
        st.write("Aktuální data pro Nové Město a okolí:")
        
        # Generování tabulky předpovědi
        try:
            res = requests.get("https://api.open-meteo.com/v1/forecast?latitude=50.34&longitude=16.15&daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=auto").json()
            daily = res['daily']
            df_data = {
                "Datum": [datetime.strptime(d, "%Y-%m-%d").strftime("%d.%m.") for d in daily['time']],
                "Den (°C)": daily['temperature_2m_max'],
                "Noc (°C)": daily['temperature_2m_min'],
                "Stav": [get_weather_info(c)[1] for c in daily['weathercode']]
            }
            st.table(pd.DataFrame(df_data))
        except:
            st.error("Nepodařilo se načíst detailní tabulku.")
        
        st.link_button("🌐 Otevřít meteorologický radar (Windy)", "https://www.windy.com/50.344/16.151")

    st.markdown("---")
    
    # Oznámení z tabulky
    try:
        sheet_id = st.secrets["GSHEET_URL"].split("/d/")[1].split("/")[0]
        sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=List%202"
        news_data = pd.read_csv(sheet_url)
        for val in news_data['zprava'].dropna():
            st.warning(f"🔔 {val}")
    except: pass

    # NEWS TICKER (POSUNUTO NAHORU O 10px)
    try:
        rss = ET.fromstring(requests.get("https://ct24.ceskatelevize.cz/rss/hlavni-zpravy", timeout=5).content)
        msg = rss.find('.//item/title').text
        st.markdown(f"""
            <div style="position: fixed; bottom: 55px; left: 10px; right: 10px; 
                        background: #002d6e; color: white; padding: 12px; 
                        border-radius: 15px; border: 1px solid #3b82f6; 
                        z-index: 999; text-align: center; font-size: 14px;">
                🗞️ {msg}
            </div>
        """, unsafe_allow_html=True)
    except: pass

    # Auto-refresh
    # st.empty() # Placeholder pro stabilitu
    # time.sleep(15) # Odebírám pro stabilitu při testování, můžete pak odkomentovat

# --- CHAT STRÁNKA ---
else:
    if st.button("🏠 ZPĚT"):
        st.session_state.page = "Domů"
        st.rerun()
    st.chat_input("Zeptejte se na cokoliv...")
