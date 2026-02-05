import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
from datetime import datetime, timedelta

# ==========================================
# 1. ZÁKLADNÍ NASTAVENÍ
# ==========================================
st.set_page_config(page_title="Kvádr AI", page_icon="✨", layout="wide")

# Inicializace stavů (aby si aplikace pamatovala, kde jste a co se psalo)
if "page" not in st.session_state: st.session_state.page = "Domů"
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "show_weather_details" not in st.session_state: st.session_state.show_weather_details = False

# Nastavení AI klíče
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-flash")
except:
    st.error("⚠️ Chybí API klíč pro AI. Zkontrolujte 'secrets'.")

# ==========================================
# 2. DESIGN (CSS) - ČISTÝ A MODERNÍ
# ==========================================
st.markdown("""
<style>
    .stApp {
        background: radial-gradient(circle at center, #1a2c4e 0%, #070b14 100%);
        color: #ffffff;
    }
    
    /* Horní lišta počasí */
    .weather-grid-top { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-bottom: 20px; }
    .weather-box-small {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 10px; border-radius: 15px;
        text-align: center; min-width: 120px;
    }
    
    /* Vítejte obrazovka v chatu */
    .welcome-screen {
        text-align: center;
        margin-top: 50px;
        margin-bottom: 50px;
    }
    .welcome-title { font-size: 3.5rem; font-weight: 900; background: linear-gradient(to right, #fff, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }

    /* Fix pro tlačítko Zpět */
    .back-nav {
        background: rgba(15, 23, 42, 0.5);
        padding: 15px;
        border-radius: 20px;
        margin-bottom: 30px;
        border: 1px solid rgba(255,255,255,0.05);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. FUNKCE (POČASÍ A TABULKY)
# ==========================================
def nacti_data_sheets(nazev_listu):
    try:
        base_url = st.secrets["GSHEET_URL"]
        sheet_id = base_url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(nazev_listu)}"
        return pd.read_csv(csv_url)
    except:
        return pd.DataFrame(columns=['zprava'])

@st.cache_data(ttl=1800)
def nacti_pocasi():
    mesta = {"Nové Město n. M.": (50.34, 16.15), "Bělá": (50.53, 14.80), "Praha": (50.07, 14.43), "Hradec Králové": (50.21, 15.83)}
    vysledky = {}
    for m, (lat, lon) in mesta.items():
        try:
            r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m&daily=temperature_2m_max,temperature_2m_min&timezone=auto", timeout=2).json()
            vysledky[m] = {"teplota": f"{round(r['current']['temperature_2m'])}°C", "max": round(r['daily']['temperature_2m_max'][0]), "min": round(r['daily']['temperature_2m_min'][0])}
        except: vysledky[m] = {"teplota": "??", "max": "--", "min": "--"}
    return vysledky

# ==========================================
# 4. STRÁNKA DOMŮ
# ==========================================
if st.session_state.page == "Domů":
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("💬 OTEVŘÍT AI CHAT", use_container_width=True, type="primary"):
            st.session_state.page = "AI Chat"
            st.rerun()

    # Počasí lišta
    w_data = nacti_pocasi()
    html_w = '<div class="weather-grid-top">'
    for m, d in w_data.items():
        html_w += f'<div class="weather-box-small"><div style="font-size:12px; color:#94a3b8;">{m}</div><div style="font-size:20px; font-weight:bold;">{d["teplota"]}</div></div>'
    html_w += '</div>'
    st.markdown(html_w, unsafe_allow_html=True)

    # Oznámení
    st.markdown("<h4 style='text-align:center;'>Oznámení</h4>", unsafe_allow_html=True)
    df_oznameni = nacti_data_sheets("List 2")
    for text in df_oznameni['zprava'].dropna():
        st.info(text)

# ==========================================
# 5. STRÁNKA AI CHAT
# ==========================================
elif st.session_state.page == "AI Chat":
    # Horní navigace (Tlačítko Zpět)
    with st.container():
        st.markdown('<div class="back-nav">', unsafe_allow_html=True)
        col_back1, col_back2, col_back3 = st.columns([1, 1.5, 1])
        with col_back2:
            if st.button("🏠 Zpět na domovskou obrazovku", use_container_width=True):
                st.session_state.page = "Domů"
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Zobrazení historie nebo úvodní obrazovky
    if not st.session_state.chat_history:
        st.markdown("""
            <div class="welcome-screen">
                <div style="font-size: 80px;">✨</div>
                <h1 class="welcome-title">Vítejte v KVÁDR AI</h1>
                <p style="color: #94a3b8; font-size: 1.2rem;">Váš chytrý asistent je připraven.</p>
            </div>
        """, unsafe_allow_html=True)
    else:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Vstup pro zprávu
    if prompt := st.chat_input("Jak vám mohu dnes pomoci?"):
        # 1. Zobrazit zprávu uživatele
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. Generovat odpověď AI
        with st.chat_message("assistant"):
            with st.spinner("Přemýšlím..."):
                try:
                    # Načtení kontextu z tabulky
                    df_ctx = nacti_data_sheets("List 1")
                    kontext = " ".join(df_ctx['zprava'].astype(str).tolist())
                    
                    full_prompt = f"Instrukce: Odpovídej stručně a lidsky. Zde je tvůj kontext: {kontext}\n\nUživatel se ptá: {prompt}"
                    response = model.generate_content(full_prompt)
                    st.markdown(response.text)
                    
                    # Uložit do historie a restartovat pro čisté zobrazení
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"Omlouvám se, došlo k chybě: {e}")
        
        st.rerun() # Refresh pro správné zařazení zpráv
