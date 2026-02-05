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

# ==========================================
# 2. CHYTRÉ POČASÍ (Open-Meteo API)
# ==========================================
def get_wmo_emoji(code):
    """Převede číselný kód počasí na hezkou ikonu"""
    if code == 0: return "☀️ Jasno"
    if code in [1, 2, 3]: return "⛅ Polojasno"
    if code in [45, 48]: return "🌫️ Mlhavo"
    if code in [51, 53, 55]: return "🌧️ Mrholení"
    if code in [61, 63, 65]: return "☔ Déšť"
    if code in [71, 73, 75]: return "❄️ Sníh"
    if code in [95, 96, 99]: return "⛈️ Bouřka"
    return "☁️ Zataženo"

def nacti_aktualni(mesto):
    """Rychlé aktuální počasí pro horní lištu"""
    try:
        url = f"https://wttr.in/{mesto}?format=%C+%t&m&lang=cs"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.text.replace("+", "")
        return "N/A"
    except: return "Chyba"

def nacti_predpoved_7dni(lat, lon):
    """Stáhne přesná data na 7 dní z Open-Meteo"""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=auto"
        res = requests.get(url, timeout=5).json()
        
        daily = res.get("daily", {})
        dni = []
        for i in range(7):
            datum = datetime.now() + timedelta(days=i)
            den_nazev = datum.strftime("%d.%m.")
            kod = daily["weathercode"][i]
            temp_max = daily["temperature_2m_max"][i]
            temp_min = daily["temperature_2m_min"][i]
            dni.append({
                "den": den_nazev,
                "pocasi": get_wmo_emoji(kod),
                "teplota": f"{round(temp_min)}°C / {round(temp_max)}°C"
            })
        return dni
    except:
        return []

# Souřadnice měst pro maximální přesnost (Praha, HK, NMNM, Bělá)
SOURADNICE = {
    "Nové Město n. M.": (50.344, 16.151),
    "Bělá": (50.534, 14.807), # Bělá pod Bezdězem (pokud myslíte jinou, stačí změnit čísla)
    "Praha": (50.075, 14.437),
    "Hradec Králové": (50.210, 15.832)
}

# ==========================================
# 3. DESIGN A STYLY
# ==========================================
st.markdown("""
<style>
    .stApp {
        background: radial-gradient(circle at center, #1a2c4e 0%, #070b14 100%);
        color: #ffffff;
        font-family: 'Inter', sans-serif;
    }
    #MainMenu, footer {visibility: hidden;}

    /* Horní rychlé počasí */
    .weather-grid-top {
        display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-bottom: 20px;
    }
    .weather-box-small {
        background: rgba(59, 130, 246, 0.1);
        border: 1px solid rgba(59, 130, 246, 0.3);
        padding: 10px 15px; border-radius: 12px;
        text-align: center; flex: 1; min-width: 120px;
    }
    .wb-city { font-size: 12px; color: #94a3b8; text-transform: uppercase; font-weight: bold; }
    .wb-temp { font-size: 16px; font-weight: bold; color: #ffffff; margin-top: 5px; }

    /* Detailní karta města */
    .city-detail-card {
        background: rgba(15, 23, 42, 0.8);
        border-left: 5px solid #3b82f6;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .city-title { font-size: 22px; font-weight: bold; margin-bottom: 15px; color: #60a5fa; border-bottom: 1px solid #334155; padding-bottom: 10px; }
    
    /* Řádky předpovědi */
    .forecast-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05);
    }
    .f-date { width: 60px; color: #94a3b8; font-size: 14px; }
    .f-icon { flex-grow: 1; text-align: left; padding-left: 15px; font-size: 15px; }
    .f-temp { font-weight: bold; color: #ffffff; font-size: 15px; }

    .stButton > button { border-radius: 50px !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. NAVIGACE
# ==========================================
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    if st.session_state.page == "Domů":
        if st.button("💬 Přejít na Kvádr AI Chat", use_container_width=True, type="primary"):
            st.session_state.page = "AI Chat"; st.rerun()
    else:
        if st.button("🏠 Zpět na Domovskou stránku", use_container_width=True):
            st.session_state.page = "Domů"; st.rerun()

# ==========================================
# 5. DATA A LOGIKA
# ==========================================
def nacti_data(nazev_listu):
    try:
        base_url = st.secrets["GSHEET_URL"]
        sheet_id = base_url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(nazev_listu)}"
        return pd.read_csv(csv_url)
    except: return pd.DataFrame(columns=['zprava'])

# --- DOMOVSKÁ STRÁNKA ---
if st.session_state.page == "Domů":
    st.markdown('<div style="text-align:center; padding-top:20px; margin-bottom:10px;"><div style="background:rgba(59,130,246,0.1); padding:15px; border-radius:20px; display:inline-block; font-size:40px;">🏠</div></div>', unsafe_allow_html=True)
    st.markdown('<h2 style="text-align:center; margin:0;">Domovská stránka</h2>', unsafe_allow_html=True)
    
    # 1. Horní rychlý přehled (4 města)
    w_nmnm = nacti_aktualni("Nove+Mesto+nad+Metuji")
    w_bela = nacti_aktualni("Bela,CZ")
    w_praha = nacti_aktualni("Prague")
    w_hk = nacti_aktualni("Hradec+Kralove")

    st.markdown(f"""
    <div class="weather-grid-top">
        <div class="weather-box-small"><div class="wb-city">Nové Město</div><div class="wb-temp">{w_nmnm}</div></div>
        <div class="weather-box-small"><div class="wb-city">Bělá</div><div class="wb-temp">{w_bela}</div></div>
        <div class="weather-box-small"><div class="wb-city">Praha</div><div class="wb-temp">{w_praha}</div></div>
        <div class="weather-box-small"><div class="wb-city">Hradec Králové</div><div class="wb-temp">{w_hk}</div></div>
    </div>
    """, unsafe_allow_html=True)

    # Tlačítko pro zobrazení/skrytí detailů
    col_btn1, col_btn2, col_btn3 = st.columns([1,2,1])
    with col_btn2:
        btn_label = "❌ Zavřít podrobnosti" if st.session_state.show_weather_details else "📅 Podrobná předpověď (7 dní)"
        if st.button(btn_label, use_container_width=True):
            st.session_state.show_weather_details = not st.session_state.show_weather_details
            st.rerun()

    # 2. Sekce podrobností (pokud je aktivní)
    if st.session_state.show_weather_details:
        st.write("---")
        cols = st.columns(2) # Rozdělení do dvou sloupců pro kompaktnost na PC
        
        mesta_items = list(SOURADNICE.items())
        
        # Procházíme města a tvoříme karty
        for i, (nazev, (lat, lon)) in enumerate(mesta_items):
            with cols[i % 2]: # Střídání sloupců
                predpoved = nacti_predpoved_7dni(lat, lon)
                
                html_rows = ""
                for den in predpoved:
                    html_rows += f"""
                    <div class="forecast-row">
                        <span class="f-date">{den['den']}</span>
                        <span class="f-icon">{den['pocasi']}</span>
                        <span class="f-temp">{den['teplota']}</span>
                    </div>
                    """
                
                st.markdown(f"""
                <div class="city-detail-card">
                    <div class="city-title">{nazev}</div>
                    {html_rows}
                </div>
                """, unsafe_allow_html=True)
        st.write("---")

    # 3. Novinky
    st.markdown('<h3 style="text-align:center; margin-top:30px;">Oznámení</h3>', unsafe_allow_html=True)
    df = nacti_data("List 2")
    for zprava in df['zprava'].dropna():
        st.markdown(f'<div style="background:rgba(15,23,42,0.6); border:1px solid #1e293b; padding:20px; border-radius:15px; margin:10px auto; max-width:800px;">{zprava}</div>', unsafe_allow_html=True)

# --- CHAT STRÁNKA ---
elif st.session_state.page == "AI Chat":
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    
    if not st.session_state.chat_history:
        st.markdown('<div style="text-align:center; padding-top:50px;"><span style="font-size:50px; display:block; margin-bottom:20px;">✨</span><h1 style="margin:0;">Vítejte v KVÁDR AI</h1><p style="color:#94a3b8;">Jsem připraven pomoci.</p></div>', unsafe_allow_html=True)

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if pr := st.chat_input("Napište zprávu..."):
        st.session_state.chat_history.append({"role": "user", "content": pr})
        with st.chat_message("user"): st.markdown(pr)
        with st.chat_message("assistant"):
            with st.spinner("Kvádr AI přemýšlí..."):
                try:
                    df_ai = nacti_data("List 1")
                    ctx = " ".join(df_ai['zprava'].astype(str).tolist())
                    model = genai.GenerativeModel(st.session_state.model_name)
                    res = model.generate_content(f"Kontext: {ctx}\nDotaz: {pr}")
                    st.markdown(res.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": res.text})
                except: st.error("Chyba AI.")
