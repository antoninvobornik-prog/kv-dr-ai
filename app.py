import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# ==========================================
# 1. KONFIGURACE AI
# ==========================================
st.set_page_config(page_title="Kvádr AI", layout="wide")

if "page" not in st.session_state: st.session_state.page = "Domů"
if "show_weather_details" not in st.session_state: st.session_state.show_weather_details = False
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "news_index" not in st.session_state: st.session_state.news_index = 0

@st.cache_resource
def inicializuj_ai():
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    if 'gemini-1.5-flash' in m.name:
                        return genai.GenerativeModel(m.name)
        except:
            pass
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        return None

ai_model = inicializuj_ai()

# ==========================================
# 2. POMOCNÉ FUNKCE (RSS, Počasí, Tabulky)
# ==========================================

@st.cache_data(ttl=300)
def nacti_aktuality():
    zpravy = []
    zdroje = ["https://ct24.ceskatelevize.cz/rss/hlavni-zpravy", "https://www.novinky.cz/rss"]
    for url in zdroje:
        try:
            res = requests.get(url, timeout=5)
            root = ET.fromstring(res.content)
            for item in root.findall('.//item')[:5]:
                title = item.find('title').text
                if title: zpravy.append(title.strip())
        except: continue
    aktualni_cas = datetime.now().strftime("%H:%M")
    return zpravy if zpravy else [f"Systém Kvádr aktualizován v {aktualni_cas}"], aktualni_cas

def get_wmo_emoji(code):
    mapping = {0: "☀️ Jasno", 1: "⛅ Polojasno", 2: "⛅ Polojasno", 3: "☁️ Zataženo", 45: "🌫️ Mlha", 51: "🌧️ Mrholení", 61: "☔ Déšť", 71: "❄️ Sníh", 95: "⛈️ Bouřka"}
    return mapping.get(code, "☁️ Zataženo")

@st.cache_data(ttl=1800)
def nacti_kompletni_pocasi():
    SOURADNICE = {"Nové Město n. M.": (50.344, 16.151), "Bělá": (50.534, 14.807), "Praha": (50.075, 14.437), "Hradec Králové": (50.210, 15.832)}
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
        url = st.secrets["GSHEET_URL"]
        id_sheet = url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{id_sheet}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(nazev_listu)}"
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
    .news-island {
        position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
        background: rgba(15, 23, 42, 0.95); border: 1px solid #3b82f6;
        padding: 12px 25px; border-radius: 50px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        z-index: 1000; width: auto; max-width: 85%;
        text-align: center; backdrop-filter: blur(10px);
    }
    .news-text { color: #60a5fa; font-weight: bold; font-size: 14px; }
    .news-time { color: #3b82f6; font-size: 10px; display: block; opacity: 0.7; }
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

    seznam_zprav, cas_stazeni = nacti_aktuality()
    idx = st.session_state.news_index % len(seznam_zprav)
    st.markdown(f'''<div class="news-island"><span class="news-time">AKTUALIZOVÁNO DNES V {cas_stazeni}</span><div class="news-text">🗞️ {seznam_zprav[idx]}</div></div>''', unsafe_allow_html=True)

    time.sleep(8)
    st.session_state.news_index += 1
    st.rerun()

# ==========================================
# 6. STRÁNKA: AI CHAT (Zde je chatovací vstup)
# ==========================================
elif st.session_state.page == "AI Chat":
    st.markdown('<h2 style="text-align:center;">💬 Kvádr AI</h2>', unsafe_allow_html=True)
    
    if ai_model is None:
        st.error("AI model nebyl nalezen. Zkontroluj API klíč v Secrets.")
    else:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])

        # Chat_input je nyní bezpečně uvnitř sekce AI Chat
        if pr := st.chat_input("Zeptej se na cokoliv..."):
            st.session_state.chat_history.append({"role": "user", "content": pr})
            with st.chat_message("user"): st.markdown(pr)
            with st.chat_message("assistant"):
                try:
                    df_ai = nacti_data_sheets("List 1")
                    ctx = " ".join(df_ai['zprava'].astype(str).tolist())
                    response = ai_model.generate_content(f"Jsi asistent projektu Kvádr. Info: {ctx}\nUživatel: {pr}")
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"Chyba: {e}")
