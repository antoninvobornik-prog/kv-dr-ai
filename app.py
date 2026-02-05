import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
from datetime import datetime, timedelta

# ==========================================
# 1. INICIALIZACE STAVU (ZÁCHRANA PŘED CHYBAMI)
# ==========================================
if "page" not in st.session_state:
    st.session_state.page = "Domů"

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "show_weather_details" not in st.session_state:
    st.session_state.show_weather_details = False

st.set_page_config(page_title="Kvádr AI", layout="wide")

# Inicializace AI modelu (automaticky najde ten funkční)
if "model_name" not in st.session_state:
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        # Najdeme modely, které skutečně fungují pod tvým klíčem
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        flash_models = [m for m in available_models if "flash" in m.lower()]
        
        if flash_models:
            st.session_state.model_name = flash_models[0]
        elif available_models:
            st.session_state.model_name = available_models[0]
        else:
            st.session_state.model_name = "gemini-1.5-flash"
    except Exception as e:
        st.session_state.model_name = "gemini-1.5-flash"

# ==========================================
# 2. POMOCNÉ FUNKCE
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

def nacti_data_sheets(nazev_listu):
    try:
        base_url = st.secrets["GSHEET_URL"]
        sheet_id = base_url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(nazev_listu)}"
        return pd.read_csv(csv_url)
    except: 
        return pd.DataFrame(columns=['zprava'])

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
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. NAVIGACE
# ==========================================
col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
with col_nav2:
    if st.session_state.page == "Domů":
        if st.button("💬 Otevřít AI Chat", use_container_width=True, type="primary"):
            st.session_state.page = "AI Chat"
            st.rerun()
    else:
        if st.button("🏠 Zpět Domů", use_container_width=True):
            st.session_state.page = "Domů"
            st.rerun()

# ==========================================
# 5. OBSAH STRÁNEK
# ==========================================

# --- DOMOVSKÁ STRÁNKA ---
if st.session_state.page == "Domů":
    # --- PŘIDANÉ NADPISY ---
    st.title("🏙️ Vítejte, Domovská stránka")
    st.subheader("Váš chytrý rozcestník a asistent")
    st.write("---") # Oddělovací čára

    weather_data = nacti_kompletni_pocasi()
    # ... (zbytek kódu pro počasí zůstává stejný) ...

    st.markdown('<h3 style="text-align:center; margin-top:30px;">📢 Aktuální oznámení</h3>', unsafe_allow_html=True)
    df_oznameni = nacti_data_sheets("List 2")
    if not df_oznameni.empty:
        for z in df_oznameni['zprava'].dropna():
            st.info(z)
    else:
        st.write("Dnes nejsou žádná nová oznámení.")

# --- AI CHAT STRÁNKA ---
elif st.session_state.page == "AI Chat":
    # --- PŘIDANÉ NADPISY ---
    st.title("💬 Chat s Kvádr AI")
    st.caption("Ptejte se na cokoliv, co vás zajímá ohledně našich dat a informací.")
    
    st.sidebar.caption(f"Model: {st.session_state.model_name}")
    # ... (zbytek kódu pro chat zůstává stejný) ...
    st.markdown('<h3 style="text-align:center;">Oznámení</h3>', unsafe_allow_html=True)
    df_oznameni = nacti_data_sheets("List 2")
    if not df_oznameni.empty:
        for z in df_oznameni['zprava'].dropna():
            st.info(z)

    
    # Zobrazení historie
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Vstup uživatele
    if prompt := st.chat_input("Napište zprávu pro Kvádr AI..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Přemýšlím..."):
                try:
                    # Načtení kontextu z tabulky
                    df_ai = nacti_data_sheets("List 1")
                    kontext_text = " ".join(df_ai['zprava'].astype(str).tolist())
                    
                    model = genai.GenerativeModel(st.session_state.model_name)
                    plny_dotaz = f"Jsi Kvádr AI. Odpovídej česky na základě tohoto kontextu: {kontext_text}\n\nUživatel: {prompt}"
                    
                    response = model.generate_content(plny_dotaz)
                    
                    if response.text:
                        st.markdown(response.text)
                        st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                        st.rerun()
                    else:
                        st.error("AI vrátila prázdnou odpověď.")
                except Exception as e:
                    st.error(f"Chyba při komunikaci s AI: {e}")
