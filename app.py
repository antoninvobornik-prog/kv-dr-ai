import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests

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

if "page" not in st.session_state:
    st.session_state.page = "Domů"

# ==========================================
# 2. OPRAVENÁ FUNKCE POČASÍ (S HEADERS)
# ==========================================
def nacti_pocasi(mesto):
    try:
        url = f"https://wttr.in/{mesto}?format=%C+%t&m&lang=cs"
        # Přidání hlavičky, aby nás server neblokoval jako bota
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.text.replace("+", "")
        return "Nedostupné"
    except:
        return "Chyba"

# ==========================================
# 3. STYLY (Čistý temný režim)
# ==========================================
st.markdown("""
<style>
    .stApp {
        background: radial-gradient(circle at center, #1a2c4e 0%, #070b14 100%);
        color: #ffffff;
    }
    #MainMenu, footer {visibility: hidden;}
    
    .welcome-container { text-align: center; padding-top: 20px; }
    .welcome-logo { background: rgba(59, 130, 246, 0.1); border-radius: 20px; padding: 20px; display: inline-block; }
    
    .weather-grid { display: flex; justify-content: center; gap: 10px; margin-bottom: 30px; }
    .weather-box {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 10px; border-radius: 12px;
        text-align: center; min-width: 140px;
    }
    .weather-city { font-size: 11px; color: #94a3b8; text-transform: uppercase; }
    .weather-data { font-size: 16px; font-weight: bold; color: #3b82f6; }

    .news-card {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid #1e293b;
        padding: 20px; border-radius: 15px;
        margin: 10px auto; max-width: 800px;
        font-size: 16px;
    }
    .stButton > button { border-radius: 50px !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. NAVIGACE (Horní tlačítko)
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

if st.session_state.page == "Domů":
    st.markdown('<div class="welcome-container"><div class="welcome-logo"><span style="font-size: 40px;">🏠</span></div><h2 style="margin-bottom:0;">Domovská stránka</h2><p style="color:#94a3b8;">Aktuální přehled a počasí</p></div>', unsafe_allow_html=True)
    
    # Počasí
    w_nmnm = nacti_pocasi("Nove+Mesto+nad+Metuji")
    w_bela = nacti_pocasi("Bela")
    st.markdown(f'<div class="weather-grid"><div class="weather-box"><div class="weather-city">Nové Město n. M.</div><div class="weather-data">🌡️ {w_nmnm}</div></div><div class="weather-box"><div class="weather-city">Bělá</div><div class="weather-data">🌡️ {w_bela}</div></div></div>', unsafe_allow_html=True)

    # Zprávy z tabulky
    df = nacti_data("List 2")
    for zprava in df['zprava'].dropna():
        st.markdown(f'<div class="news-card">{zprava}</div>', unsafe_allow_html=True)

elif st.session_state.page == "AI Chat":
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if pr := st.chat_input("Napište svou zprávu..."):
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
