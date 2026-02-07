import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# ==========================================
# 1. KONFIGURACE
# ==========================================
st.set_page_config(page_title="Kvádr AI", layout="wide")

if "page" not in st.session_state: st.session_state.page = "Domů"
if "show_weather_details" not in st.session_state: st.session_state.show_weather_details = False
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "news_index" not in st.session_state: st.session_state.news_index = 0

try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    MODEL_ID = "gemini-1.5-flash" 
except:
    st.error("Chybí GOOGLE_API_KEY v Secrets!")

# ==========================================
# 2. POMOCNÉ FUNKCE
# ==========================================

@st.cache_data(ttl=600)
def nacti_aktuality():
    """Stáhne zprávy z ČT24 a Novinek."""
    zpravy = []
    zdroje = ["https://ct24.ceskatelevize.cz/rss/hlavni-zpravy", "https://www.novinky.cz/rss"]
    for url in zdroje:
        try:
            res = requests.get(url, timeout=5)
            root = ET.fromstring(res.content)
            for item in root.findall('.//item')[:5]:
                title = item.find('title').text
                zpravy.append(title)
        except: continue
    return zpravy if zpravy else ["Kvádr AI: Připraven k práci.", "Sledujte aktuální dění."]

SOURADNICE = {"Nové Město n. M.": (50.344, 16.151), "Bělá": (50.534, 14.807), "Praha": (50.075, 14.437), "Hradec Králové": (50.210, 15.832)}

def get_wmo_emoji(code):
    mapping = {0: "☀️ Jasno", 1: "⛅ Polojasno", 2: "⛅ Polojasno", 3: "☁️ Zataženo", 45: "🌫️ Mlha", 51: "🌧️ Mrholení", 61: "☔ Déšť", 71: "❄️ Sníh", 95: "⛈️ Bouřka"}
    return mapping.get(code, "☁️ Zataženo")

@st.cache_data(ttl=1800)
def nacti_kompletni_pocasi():
    data_output = {}
    for mesto, (lat, lon) in SOURADNICE.items():
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=auto"
            res = requests.get(url, timeout=5).json()
            data_output[mesto] = {
                "aktualni_teplota": f"{round(res['current']['temperature_2m'])}°C",
                "aktualni_ikona": get_wmo_emoji(res['current']['weathercode']).split(" ")[0],
                "predpoved": [{"den": (datetime.now() + timedelta(days=i)).strftime("%d.%m."), "pocasi": get_wmo_emoji(res['daily']['weathercode'][i]), "teplota": f"{round(res['daily']['temperature_2m_min'][i])}°/{round(res['daily']['temperature_2m_max'][i])}°"} for i in range(7)]
            }
        except: data_output[mesto] = {"aktualni_teplota": "--", "aktualni_ikona": "⚠️", "predpoved": []}
    return data_output

def nacti_data_sheets(nazev_listu):
    try:
        base_url = st.secrets["GSHEET_URL"]
        sheet_id = base_url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(nazev_listu)}"
        return pd.read_csv(csv_url)
    except: return pd.DataFrame(columns=['zprava'])

# ==========================================
# 3. STYLY
# ==========================================
st.markdown("""
<style>
    .stApp { background: radial-gradient(circle at center, #1a2c4e 0%, #070b14 100%); color: white; }
    .weather-grid-top { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin-bottom: 15px; }
    .weather-box-small { background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3); padding: 10px; border-radius: 10px; text-align: center; min-width: 120px; }
    
    /* Zpravodajský ostrůvek */
    .news-island {
        position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
        background: rgba(15, 23, 42, 0.9); border: 1px solid #3b82f6;
        padding: 12px 25px; border-radius: 50px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        z-index: 1000; width: auto; max-width: 85%;
        text-align: center; backdrop-filter: blur(10px);
    }
    .news-text { color: #60a5fa; font-weight: bold; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. NAVIGACE
# ==========================================
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    if st.session_state.page == "Domů":
        if st.button("💬 OTEVŘÍT KVÁDR AI CHAT", use_container_width=True, type="primary"):
            st.session_state.page = "AI Chat"; st.rerun()
    else:
        if st.button("🏠 ZPĚT NA PORTÁL", use_container_width=True):
            st.session_state.page = "Domů"; st.rerun()

# ==========================================
# 5. STRÁNKA: DOMŮ
# ==========================================
if st.session_state.page == "Domů":
    st.markdown('<h1 style="text-align:center;">🏙️ KVÁDR PORTÁL</h1>', unsafe_allow_html=True)
    
    weather_data = nacti_kompletni_pocasi()
    h_html = '<div class="weather-grid-top">'
    for m, d in weather_data.items():
        h_html += f'<div class="weather-box-small"><div style="font-size:11px; opacity:0.7;">{m}</div><div style="font-size:18px; font-weight:bold;">{d["aktualni_ikona"]} {d["aktualni_teplota"]}</div></div>'
    h_html += '</div>'
    st.markdown(h_html, unsafe_allow_html=True)

    if st.button("📅 " + ("Zavřít detail" if st.session_state.show_weather_details else "Zobrazit předpověď"), use_container_width=True):
        st.session_state.show_weather_details = not st.session_state.show_weather_details
        st.rerun()

    if st.session_state.show_weather_details:
        cols = st.columns(2)
        for i, (mesto, data) in enumerate(weather_data.items()):
            with cols[i % 2]:
                rows = "".join([f'<div style="display:flex; justify-content:space-between; font-size:13px; border-bottom:1px solid rgba(255,255,255,0.1); padding:4px 0;"><span>{f["den"]}</span><span>{f["pocasi"]}</span><b>{f["teplota"]}</b></div>' for f in data['predpoved']])
                st.markdown(f'<div style="background:rgba(15,23,42,0.7); padding:10px; border-radius:10px; margin-bottom:10px;"><b style="color:#60a5fa;">{mesto}</b>{rows}</div>', unsafe_allow_html=True)

    st.markdown('<h3 style="text-align:center; margin-top:20px;">📢 Oznámení</h3>', unsafe_allow_html=True)
    df = nacti_data_sheets("List 2")
    for msg in df['zprava'].dropna(): st.info(msg)

    # LOGIKA PRO ZPRAVODAJSKÝ OSTRŮVEK
    seznam_zprav = nacti_aktuality()
    idx = st.session_state.news_index % len(seznam_zprav)
    aktualni_titulek = seznam_zprav[idx]

    st.markdown(f"""
        <div class="news-island">
            <div class="news-text">🗞️ {aktualni_titulek}</div>
        </div>
    """, unsafe_allow_html=True)

    # Časovač pro změnu
    time.sleep(8)
    st.session_state.news_index += 1
    st.rerun()

# ==========================================
# 6. STRÁNKA: AI CHAT
# ==========================================
elif st.session_state.page == "AI Chat":
    st.markdown('<h2 style="text-align:center;">💬 Kvádr AI</h2>', unsafe_allow_html=True)
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if pr := st.chat_input("Zeptej se na projekt Kvádr..."):
        st.session_state.chat_history.append({"role": "user", "content": pr})
        with st.chat_message("user"): st.markdown(pr)
        with st.chat_message("assistant"):
            try:
                df_ai = nacti_data_sheets("List 1")
                ctx = " ".join(df_ai['zprava'].astype(str).tolist())
                model = genai.GenerativeModel(MODEL_ID)
                response = model.generate_content(f"Jsi asistent projektu Kvádr. Info: {ctx}\nUživatel: {pr}")
                st.markdown(response.text)
                st.session_state.chat_history.append({"role": "assistant", "content": response.text})
            except: st.error("Chyba AI.")
