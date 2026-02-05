import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
from datetime import datetime, timedelta

# ==========================================
# 1. KONFIGURACE
# ==========================================
st.set_page_config(page_title="Kvádr AI", page_icon="✨", layout="wide")

# Inicializace session state proměnných
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
# 2. LOGIKA POČASÍ (RYCHLÁ & BEZ CHYB)
# ==========================================
SOURADNICE = {
    "Nové Město n. M.": (50.344, 16.151),
    "Bělá": (50.534, 14.807),
    "Praha": (50.075, 14.437),
    "Hradec Králové": (50.210, 15.832)
}

def get_wmo_emoji(code):
    if code == 0: return "☀️ Jasno"
    if code in [1, 2, 3]: return "⛅ Polojasno"
    if code in [45, 48]: return "🌫️ Mlhavo"
    if code in [51, 53, 55]: return "🌧️ Mrholení"
    if code in [61, 63, 65]: return "☔ Déšť"
    if code in [71, 73, 75]: return "❄️ Sníh"
    if code in [95, 96, 99]: return "⛈️ Bouřka"
    return "☁️ Zataženo"

@st.cache_data(ttl=1800)
def nacti_kompletni_pocasi():
    data_output = {}
    for mesto, (lat, lon) in SOURADNICE.items():
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=auto"
            res = requests.get(url, timeout=3).json()
            
            curr_temp = round(res["current"]["temperature_2m"])
            curr_code = res["current"]["weathercode"]
            
            daily = res.get("daily", {})
            predpoved_list = []
            for i in range(7):
                datum = datetime.now() + timedelta(days=i)
                den_nazev = datum.strftime("%d.%m.")
                kod = daily["weathercode"][i]
                t_min = daily["temperature_2m_min"][i]
                t_max = daily["temperature_2m_max"][i]
                predpoved_list.append({
                    "den": den_nazev,
                    "pocasi": get_wmo_emoji(kod),
                    "teplota": f"{round(t_min)}° / {round(t_max)}°"
                })

            data_output[mesto] = {
                "aktualni_teplota": f"{curr_temp}°C",
                "aktualni_ikona": get_wmo_emoji(curr_code).split(" ")[0],
                "predpoved": predpoved_list
            }
        except:
            data_output[mesto] = {"aktualni_teplota": "--", "aktualni_ikona": "⚠️", "predpoved": []}
    return data_output

# ==========================================
# 3. DESIGN A STYLY (CSS)
# ==========================================
st.markdown("""
<style>
    .stApp {
        background: radial-gradient(circle at center, #1a2c4e 0%, #070b14 100%);
        color: #ffffff;
        font-family: 'Inter', sans-serif;
    }
    #MainMenu, footer {visibility: hidden;}

    /* Horní lišta počasí */
    .weather-grid-top { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-bottom: 20px; }
    .weather-box-small {
        background: rgba(59, 130, 246, 0.15);
        border: 1px solid rgba(59, 130, 246, 0.4);
        padding: 12px 15px; border-radius: 12px;
        text-align: center; flex: 1; min-width: 130px;
        backdrop-filter: blur(5px);
    }
    .wb-city { font-size: 13px; color: #cbd5e1; text-transform: uppercase; font-weight: 600; }
    .wb-temp { font-size: 20px; font-weight: 800; color: #ffffff; margin-top: 2px; }
    .wb-icon { font-size: 20px; margin-right: 5px; }

    /* Detailní karty počasí */
    .city-detail-card {
        background: rgba(15, 23, 42, 0.8);
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
    }
    .city-title { font-size: 18px; font-weight: bold; margin-bottom: 10px; color: #60a5fa; border-bottom: 1px solid #334155; padding-bottom: 5px; }
    .forecast-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.05);
    }
    .f-date { width: 50px; color: #94a3b8; font-size: 14px; }
    .f-icon { flex-grow: 1; text-align: left; padding-left: 15px; font-size: 14px; }
    .f-temp { font-weight: bold; color: #e2e8f0; font-size: 14px; }

    /* Styly pro chat uvítání */
    .chat-welcome-container {
        text-align: center;
        padding-top: 5vh; 
        padding-bottom: 5vh;
    }
    .chat-welcome-icon { font-size: 60px; display: block; margin-bottom: 20px; }
    .chat-welcome-title { font-size: 3em; font-weight: 800; margin: 0; background: linear-gradient(90deg, #ffffff, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .chat-welcome-subtitle { color: #94a3b8; font-size: 1.2em; margin-top: 10px; }

    /* Obecné styly tlačítek */
    .stButton > button { border-radius: 50px !important; font-weight: bold; transition: 0.2s; border: 1px solid rgba(255,255,255,0.1); }
    .stButton > button:hover { transform: scale(1.02); background: rgba(255,255,255,0.1); }
    
    /* Kontejner pro tlačítko Zpět */
    .nav-header { padding-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.05); margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. POMOCNÉ FUNKCE DATA
# ==========================================
def nacti_data_sheets(nazev_listu):
    try:
        base_url = st.secrets["GSHEET_URL"]
        sheet_id = base_url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(nazev_listu)}"
        return pd.read_csv(csv_url)
    except: return pd.DataFrame(columns=['zprava'])

# ==========================================
# 5. STRÁNKA: DOMŮ
# ==========================================
if st.session_state.page == "Domů":
    # Horní navigace na Chat
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
         if st.button("💬 Přejít na Kvádr AI Chat", use_container_width=True, type="primary"):
            st.session_state.page = "AI Chat"
            st.rerun()

    st.markdown('<div style="text-align:center; padding-top:20px; margin-bottom:10px;"><div style="background:rgba(59,130,246,0.1); padding:15px; border-radius:20px; display:inline-block; font-size:40px;">🏠</div></div>', unsafe_allow_html=True)
    
    # Počasí
    weather_data = nacti_kompletni_pocasi()
    html_top = '<div class="weather-grid-top">'
    for mesto, data in weather_data.items():
        html_top += f'<div class="weather-box-small"><div class="wb-city">{mesto}</div><div class="wb-temp"><span class="wb-icon">{data["aktualni_ikona"]}</span>{data["aktualni_teplota"]}</div></div>'
    html_top += '</div>'
    st.markdown(html_top, unsafe_allow_html=True)

    # Tlačítko Podrobnosti
    col_btn1, col_btn2, col_btn3 = st.columns([1,2,1])
    with col_btn2:
        btn_label = "❌ Zavřít podrobnosti" if st.session_state.show_weather_details else "📅 Podrobná předpověď (7 dní)"
        if st.button(btn_label, use_container_width=True):
            st.session_state.show_weather_details = not st.session_state.show_weather_details
            st.rerun()

    if st.session_state.show_weather_details:
        st.write("---")
        cols = st.columns(2)
        idx = 0
        for mesto, data in weather_data.items():
            with cols[idx % 2]:
                html_rows = "".join([f'<div class="forecast-row"><span class="f-date">{d["den"]}</span><span class="f-icon">{d["pocasi"]}</span><span class="f-temp">{d["teplota"]}</span></div>' for d in data['predpoved']])
                st.markdown(f'<div class="city-detail-card"><div class="city-title">{mesto}</div>{html_rows}</div>', unsafe_allow_html=True)
            idx += 1

    # Oznámení
    st.markdown('<h3 style="text-align:center; margin-top:20px; font-size:20px;">Oznámení</h3>', unsafe_allow_html=True)
    df = nacti_data_sheets("List 2")
    for zprava in df['zprava'].dropna():
        st.markdown(f'<div style="background:rgba(15,23,42,0.6); border:1px solid #1e293b; padding:20px; border-radius:15px; margin:10px auto; max-width:800px; font-size:16px;">{zprava}</div>', unsafe_allow_html=True)

# ==========================================
# 6. STRÁNKA: AI CHAT
# ==========================================
elif st.session_state.page == "AI Chat":
    # FIX: Horní lišta s tlačítkem Zpět
    st.markdown('<div class="nav-header">', unsafe_allow_html=True)
    c_nav1, c_nav2, c_nav3 = st.columns([1, 1.5, 1])
    with c_nav2:
        if st.button("🏠 Zpět na Domovskou stránku", use_container_width=True):
            st.session_state.page = "Domů"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Logika zobrazení obsahu (Uvítání vs Chat)
    if not st.session_state.chat_history:
        # Úvodní obrazovka (Image 3 styl)
        st.markdown("""
            <div class="chat-welcome-container">
                <span class="chat-welcome-icon">✨</span>
                <h1 class="chat-welcome-title">Vítejte v KVÁDR AI</h1>
                <p class="chat-welcome-subtitle">Zeptejte se mě na cokoliv.</p>
            </div>
        """, unsafe_allow_html=True)
    else:
        # Historie chatu (Image 2 styl)
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Chat input
    if pr := st.chat_input("Napište zprávu..."):
        st.session_state.chat_history.append({"role": "user", "content": pr})
        with st.chat_message("user"):
            st.markdown(pr)
        
        with st.chat_message("assistant"):
            with st.spinner("Kvádr AI přemýšlí..."):
                try:
                    df_ai = nacti_data_sheets("List 1")
                    ctx = " ".join(df_ai['zprava'].astype(str).tolist())
                    model = genai.GenerativeModel(st.session_state.model_name)
                    res = model.generate_content(f"Kontext: {ctx}\nDotaz: {pr}")
                    st.markdown(res.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": res.text})
                except Exception as e:
                    st.error(f"Chyba spojení s AI: {e}")
        st.rerun()
