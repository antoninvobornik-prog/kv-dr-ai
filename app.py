import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
from datetime import datetime, timedelta

# ==========================================
# 1. KONFIGURACE
# ==========================================
st.set_page_config(page_title="Kvádr AI", layout="wide")

if "model_name" not in st.session_state:
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        st.session_state.model_name = "models/gemini-1.5-flash"
    except:
        st.session_state.model_name = "models/gemini-1.5-flash"

if "page" not in st.session_state: st.session_state.page = "Domů"
if "show_weather_details" not in st.session_state: st.session_state.show_weather_details = False
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# ==========================================
# 2. LOGIKA POČASÍ
# ==========================================
SOURADNICE = {
    "Nové Město n. M.": (50.344, 16.151),
    "Bělá": (50.534, 14.807),
    "Praha": (50.075, 14.437),
    "Hradec Králové": (50.210, 15.832)
}

def get_wmo_emoji(code):
    mapping = {0: "☀️ Jasno", 1: "⛅ Polojasno", 2: "⛅ Polojasno", 3: "☁️ Zataženo", 45: "🌫️ Mlhavo", 48: "🌫️ Mlhavo", 51: "🌧️ Mrholení", 53: "🌧️ Mrholení", 55: "🌧️ Mrholení", 61: "☔ Déšť", 63: "☔ Déšť", 65: "☔ Déšť", 71: "❄️ Sníh", 73: "❄️ Sníh", 75: "❄️ Sníh", 95: "⛈️ Bouřka", 96: "⛈️ Bouřka", 99: "⛈️ Bouřka"}
    return mapping.get(code, "☁️ Zataženo")

@st.cache_data(ttl=1800)
def nacti_kompletni_pocasi():
    data_output = {}
    for mesto, (lat, lon) in SOURADNICE.items():
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=auto"
            res = requests.get(url, timeout=3).json()
            data_output[mesto] = {
                "aktualni_teplota": f"{round(res['current']['temperature_2m'])}°C",
                "aktualni_ikona": get_wmo_emoji(res['current']['weathercode']).split(" ")[0],
                "predpoved": [{"den": (datetime.now() + timedelta(days=i)).strftime("%d.%m."), "pocasi": get_wmo_emoji(res['daily']['weathercode'][i]), "teplota": f"{round(res['daily']['temperature_2m_min'][i])}° / {round(res['daily']['temperature_2m_max'][i])}°"} for i in range(7)]
            }
        except:
            data_output[mesto] = {"aktualni_teplota": "--", "aktualni_ikona": "⚠️", "predpoved": []}
    return data_output

# ==========================================
# 3. DESIGN A STYLY
# ==========================================
st.markdown("""
<style>
    .stApp { background: radial-gradient(circle at center, #1a2c4e 0%, #070b14 100%); color: #ffffff; }
    .weather-grid-top { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-bottom: 20px; }
    .weather-box-small { background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.4); padding: 12px; border-radius: 12px; text-align: center; min-width: 120px; }
    .wb-city { font-size: 11px; color: #cbd5e1; text-transform: uppercase; }
    .wb-temp { font-size: 18px; font-weight: bold; }
    .city-detail-card { background: rgba(15, 23, 42, 0.8); border-left: 4px solid #3b82f6; border-radius: 8px; padding: 15px; margin-bottom: 10px; }
    .forecast-row { display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.05); padding: 5px 0; font-size: 13px; }
    .stButton > button { border-radius: 50px !important; }
</style>
""", unsafe_allow_html=True)

def nacti_data_sheets(nazev_listu):
    try:
        base_url = st.secrets["GSHEET_URL"]
        sheet_id = base_url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(nazev_listu)}"
        return pd.read_csv(csv_url)
    except: return pd.DataFrame(columns=['zprava'])

# ==========================================
# 4. NAVIGACE
# ==========================================
col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
with col_nav2:
    if st.session_state.page == "Domů":
        if st.button("💬 Otevřít AI Chat", use_container_width=True, type="primary"):
            st.session_state.page = "AI Chat"; st.rerun()
    else:
        if st.button("🏠 Zpět Domů", use_container_width=True):
            st.session_state.page = "Domů"; st.rerun()

# --- DOMOVSKÁ STRÁNKA ---
if st.session_state.page == "Domů":
    weather_data = nacti_kompletni_pocasi()
    html_top = '<div class="weather-grid-top">'
    for m, d in weather_data.items():
        html_top += f'<div class="weather-box-small"><div class="wb-city">{m}</div><div class="wb-temp">{d["aktualni_ikona"]} {d["aktualni_teplota"]}</div></div>'
    st.markdown(html_top + '</div>', unsafe_allow_html=True)

    if st.button("📅 Detailní předpověď", use_container_width=True):
        st.session_state.show_weather_details = not st.session_state.show_weather_details
        st.rerun()

    if st.session_state.show_weather_details:
        cols = st.columns(2)
        for i, (mesto, data) in enumerate(weather_data.items()):
            with cols[i % 2]:
                rows = "".join([f'<div class="forecast-row"><span>{d["den"]}</span><span>{d["pocasi"]}</span><b>{d["teplota"]}</b></div>' for d in data['predpoved']])
                st.markdown(f'<div class="city-detail-card"><b style="color:#60a5fa">{mesto}</b>{rows}</div>', unsafe_allow_html=True)

    st.markdown('<h3 style="text-align:center;">Oznámení</h3>', unsafe_allow_html=True)
    df = nacti_data_sheets("List 2")
    for z in df['zprava'].dropna():
        st.info(z)

# --- AI CHAT ---
elif st.session_state.page == "AI Chat":
    # 1. Zobrazení historie (vždy nahoře)
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 2. Vstup od uživatele
    if prompt := st.chat_input("Napište zprávu..."):
        # Okamžité zobrazení a uložení zprávy uživatele
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 3. Generování odpovědi
        with st.chat_message("assistant"):
            with st.spinner("Kvádr AI přemýšlí..."):
                try:
                    df_ai = nacti_data_sheets("List 1")
                    ctx = " ".join(df_ai['zprava'].astype(str).tolist())
                    model = genai.GenerativeModel(st.session_state.model_name)
                    # Přidání systémové instrukce, aby robot věděl, co má dělat
                    full_prompt = f"Jsi asistent Kvádr AI. Odpovídej česky. Kontext: {ctx}\nDotaz: {prompt}"
                    res = model.generate_content(full_prompt)
                    
                    if res.text:
                        odpoved = res.text
                        st.markdown(odpoved)
                        st.session_state.chat_history.append({"role": "assistant", "content": odpoved})
                        st.rerun() # Důležité: Synchronizuje stav po odpovědi
                    else:
                        st.warning("Robot vygeneroval prázdnou odpověď (možná bezpečnostní filtr).")
                except Exception as e:
                    st.error(f"Chyba: {e}")
