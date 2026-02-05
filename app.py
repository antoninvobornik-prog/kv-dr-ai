import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests

# ==========================================
# 1. KONFIGURACE A NASTAVENÍ
# ==========================================
st.set_page_config(page_title="Kvádr AI Asistent", layout="wide")

if "model_name" not in st.session_state:
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        st.session_state.model_name = "models/gemini-1.5-flash"
    except:
        st.session_state.model_name = "models/gemini-1.5-flash"

if "page" not in st.session_state:
    st.session_state.page = "Domů"

# ==========================================
# 2. FUNKCE PRO POČASÍ (API NMNM & BĚLÁ)
# ==========================================
def nacti_pocasi(mesto):
    try:
        # Použití wttr.in pro jednoduché a rychlé načítání bez klíče
        url = f"https://wttr.in/{mesto}?format=%C+%t"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.text
        return "Nedostupné"
    except:
        return "Chyba spojení"

# ==========================================
# 3. MODERNÍ DESIGN (GRADIENT + KARTY)
# ==========================================
st.markdown("""
<style>
    .stApp {
        background: radial-gradient(circle at center, #1a2c4e 0%, #070b14 100%);
        color: #ffffff;
    }
    .welcome-container { text-align: center; padding-top: 20px; }
    .welcome-logo { background: rgba(59, 130, 246, 0.1); border-radius: 20px; padding: 20px; display: inline-block; }
    
    /* Karty počasí */
    .weather-grid {
        display: flex;
        justify-content: center;
        gap: 15px;
        margin-bottom: 30px;
    }
    .weather-box {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 15px;
        text-align: center;
        min-width: 160px;
    }
    .weather-city { font-size: 14px; color: #94a3b8; margin-bottom: 5px; }
    .weather-data { font-size: 18px; font-weight: bold; color: #3b82f6; }

    .news-card {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid #1e293b;
        padding: 20px; border-radius: 15px;
        margin: 10px auto; max-width: 800px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. NAVIGACE
# ==========================================
cols = st.columns([1, 2, 1])
with cols[1]:
    if st.session_state.page == "Domů":
        if st.button("💬 Přejít na Kvádr AI Chat", use_container_width=True, type="primary"):
            st.session_state.page = "AI Chat"
            st.rerun()
    else:
        if st.button("🏠 Zpět na Domovskou stránku", use_container_width=True):
            st.session_state.page = "Domů"
            st.rerun()

# ==========================================
# 5. OBSAH
# ==========================================
def nacti_data(nazev_listu):
    try:
        base_url = st.secrets["GSHEET_URL"]
        sheet_id = base_url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(nazev_listu)}"
        return pd.read_csv(csv_url)
    except: return pd.DataFrame(columns=['zprava'])

# --- DOMŮ ---
if st.session_state.page == "Domů":
    st.markdown('<div class="welcome-container"><div class="welcome-logo"><span style="font-size: 40px;">🏠</span></div></div>', unsafe_allow_html=True)
    
    # SEKCE POČASÍ (NMNM a Bělá)
    nmnm_w = nacti_pocasi("Nove+Mesto+nad+Metuji")
    bela_w = nacti_pocasi("Bela")
    
    st.markdown(f"""
    <div class="weather-grid">
        <div class="weather-box">
            <div class="weather-city">Nové Město n. M.</div>
            <div class="weather-data">🌡️ {nmnm_w}</div>
        </div>
        <div class="weather-box">
            <div class="weather-city">Bělá</div>
            <div class="weather-data">🌡️ {bela_w}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<h2 style="text-align:center;">Oznámení a novinky</h2>', unsafe_allow_html=True)
    df_zpravy = nacti_data("List 2")
    for zprava in df_zpravy['zprava'].dropna():
        st.markdown(f'<div class="news-card">{zprava}</div>', unsafe_allow_html=True)

# --- CHAT ---
elif st.session_state.page == "AI Chat":
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]): st.markdown(message["content"])

    if prompt := st.chat_input("Napište svou zprávu..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Kvádr AI přemýšlí..."):
                try:
                    df_ai = nacti_data("List 1")
                    model = genai.GenerativeModel(st.session_state.model_name)
                    kontext = " ".join(df_ai['zprava'].astype(str).tolist())
                    response = model.generate_content(f"Kontext: {kontext}\nDotaz: {prompt}")
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                except: st.error("Chyba spojení.")
