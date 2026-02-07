import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import streamlit.components.v1 as components

# --- KONFIGURACE ---
st.set_page_config(page_title="Kvádr Portál 7.0", layout="wide", initial_sidebar_state="collapsed")

# --- KOMPLETNÍ STYLOVÁNÍ (CSS) ---
st.markdown("""
<style>
    /* Základní nastavení */
    section[data-testid="stSidebar"] {display: none;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp { background-color: #0d1117; color: #e6edf3; }
    
    /* Odstranění mezer */
    .block-container { padding-top: 1rem; padding-bottom: 6rem; max-width: 1000px; }

    /* Hlavní červené tlačítko */
    .stButton>button {
        background: linear-gradient(90deg, #d73a49 0%, #cb2431 100%);
        color: white; border-radius: 10px; border: none;
        padding: 12px; font-weight: 600; width: 100%;
        text-transform: uppercase; letter-spacing: 1px;
    }

    /* Styl expanderu */
    .streamlit-expanderHeader {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 10px !important;
        color: #58a6ff !important;
    }

    /* Design chatu */
    [data-testid="stChatMessage"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 15px;
        padding: 10px;
        margin-bottom: 10px;
    }
    
    /* Spodní lišta se zprávami */
    .news-footer {
        position: fixed; bottom: 55px; left: 0; right: 0;
        background: #090c10; color: #58a6ff;
        padding: 10px; border-top: 1px solid #30363d;
        text-align: center; font-size: 13px; z-index: 999;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# --- DATA A MĚSTA ---
MESTA = {
    "Nové Město": (50.34, 16.15),
    "Rychnov": (50.16, 16.27),
    "Bělá": (50.53, 14.80),
    "Praha": (50.07, 14.43),
    "Hradec Králové": (50.21, 15.83),
    "Pardubice": (50.03, 15.77)
}

def get_weather_icon(code):
    icons = {0:"☀️", 1:"🌤️", 2:"⛅", 3:"☁️", 45:"🌫️", 51:"🌦️", 61:"🌧️", 71:"❄️", 80:"🌧️", 95:"⚡"}
    return icons.get(code, "🌡️")

# --- HLAVNÍ STRÁNKA ---
if "page" not in st.session_state: st.session_state.page = "Domů"

if st.session_state.page == "Domů":
    # Hlavní akce
    if st.button("💬 OTEVŘÍT ASISTENTA"):
        st.session_state.page = "AI Chat"
        st.rerun()

    # Weather Cards (Horizontální)
    cards_html = ""
    for m, (lat, lon) in list(MESTA.items())[:4]: # Zobrazení top 4 měst
        try:
            r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&timezone=auto").json()
            temp = round(r['current']['temperature_2m'])
            icon = get_weather_icon(r['current']['weathercode'])
            cards_html += f"""
            <div style="flex: 1; min-width: 80px; background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 10px; text-align: center; margin: 5px;">
                <div style="font-size: 10px; color: #8b949e;">{m.split()[0]}</div>
                <div style="font-size: 20px; font-weight: bold; margin: 4px 0;">{temp}°</div>
                <div>{icon}</div>
            </div>"""
        except: pass
    
    components.html(f'<div style="display: flex; justify-content: space-between; font-family: sans-serif;">{cards_html}</div>', height=100)

    # Detaily počasí
    with st.expander("📅 PODROBNÁ PŘEDPOVĚĎ"):
        vyber = st.selectbox("Vyberte město:", list(MESTA.keys()))
        lat, lon = MESTA[vyber]
        try:
            res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min&timezone=auto").json()
            df = pd.DataFrame({
                "Datum": [datetime.strptime(d, "%Y-%m-%d").strftime("%d.%m.") for d in res['daily']['time']],
                "Den": res['daily']['temperature_2m_max'],
                "Noc": res['daily']['temperature_2m_min']
            })
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.link_button(f"Satelitní radar ({vyber})", f"https://www.windy.com/{lat}/{lon}")
        except: st.error("Chyba dat.")

    st.write("")
    # Oznámení
    try:
        sheet_url = f"https://docs.google.com/spreadsheets/d/{st.secrets['GSHEET_URL'].split('/d/')[1].split('/')[0]}/gviz/tq?tqx=out:csv&sheet=List%202"
        news_data = pd.read_csv(sheet_url)
        for val in news_data['zprava'].dropna():
            st.info(f"💡 {val}")
    except: pass

    # Ticker dole
    try:
        rss = ET.fromstring(requests.get("https://ct24.ceskatelevize.cz/rss/hlavni-zpravy", timeout=5).content)
        msg = rss.find('.//item/title').text
        st.markdown(f'<div class="news-footer">🗞️ AKTUÁLNĚ: {msg}</div>', unsafe_allow_html=True)
    except: pass

# --- CHAT STRÁNKA ---
else:
    st.markdown("<h3 style='text-align: center; color: #58a6ff;'>🤖 AI Asistent</h3>", unsafe_allow_html=True)
    if st.button("🏠 ZPĚT"):
        st.session_state.page = "Domů"
        st.rerun()
    
    st.write("---")
    
    # Ukázka moderního chatu
    with st.chat_message("assistant"):
        st.write("Jsem připraven. S čím vám mohu pomoci?")
    
    if prompt := st.chat_input("Zeptejte se na Kvádr..."):
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("assistant"):
            st.write(f"Rozumím, analyzuji dotaz: {prompt}")
