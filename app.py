import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse

# ==========================================
# 1. KONFIGURACE A CHYTRÝ VÝBĚR MODELU
# ==========================================
st.set_page_config(page_title="Kvádr AI Asistent", layout="wide")

if "model_name" not in st.session_state:
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        st.session_state.model_name = available_models[0] if available_models else "models/gemini-1.5-flash"
    except:
        st.session_state.model_name = "models/gemini-1.5-flash"

if "page" not in st.session_state:
    st.session_state.page = "Domů"

# ==========================================
# 2. MODERNÍ DESIGN A ANIMACE
# ==========================================
st.markdown("""
<style>
    /* Základní font a barvy */
    html, body, [class*="st-"] {
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif !important;
    }
    .stApp { background-color: #070b14; color: #ffffff; }

    /* Blikající oválné tlačítko */
    @keyframes pulse {
        0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7); }
        70% { transform: scale(1.05); box-shadow: 0 0 0 15px rgba(59, 130, 246, 0); }
        100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
    }

    .nav-pill {
        display: block;
        background: linear-gradient(90deg, #3b82f6, #2563eb);
        color: white !important;
        padding: 15px 30px;
        border-radius: 50px;
        text-align: center;
        text-decoration: none;
        font-weight: bold;
        font-size: 20px;
        margin: 10px auto 30px auto;
        max-width: 300px;
        border: none;
        cursor: pointer;
        animation: pulse 2s infinite;
        box-shadow: 0 4px 15px rgba(37, 99, 235, 0.4);
    }
    
    .nav-pill-static {
        display: block;
        background: #1e293b;
        color: #94a3b8 !important;
        padding: 15px 30px;
        border-radius: 50px;
        text-align: center;
        text-decoration: none;
        font-weight: bold;
        font-size: 20px;
        margin: 10px auto 30px auto;
        max-width: 300px;
        border: 1px solid #334155;
    }

    /* Karty novinek */
    .news-card {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid #334155;
        border-left: 6px solid #3b82f6;
        padding: 25px;
        border-radius: 15px;
        margin-bottom: 20px;
        font-size: 19px;
        line-height: 1.6;
    }

    /* Stylování sidebar tlačítek */
    .stButton > button {
        border-radius: 12px;
        height: 50px;
        font-weight: bold;
        border: 1px solid #334155;
        background: #0f172a;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. FUNKCE PRO DATA
# ==========================================
@st.cache_data(ttl=60)
def nacti_data(nazev_listu):
    try:
        base_url = st.secrets["GSHEET_URL"]
        sheet_id = base_url.split("/d/")[1].split("/")[0]
        nazev_opraveny = urllib.parse.quote(nazev_listu)
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nazev_opraveny}"
        return pd.read_csv(csv_url)
    except:
        return pd.DataFrame(columns=['zprava'])

# ==========================================
# 4. NAVIGACE - INTERAKTIVNÍ TLAČÍTKA NAHOŘE
# ==========================================
if st.session_state.page == "Domů":
    # Klikací oválné tlačítko, které přepne na chat
    if st.button("💬 Kvádr AI (Klikni zde)", key="nav_to_chat", help="Přejít do chatu"):
        st.session_state.page = "AI Chat"
        st.rerun()
    st.markdown('<div class="nav-pill" style="pointer-events: none;">💬 Kvádr AI</div>', unsafe_allow_html=True)
else:
    # Klikací oválné tlačítko, které přepne na domů
    if st.button("🏠 Domů (Klikni zde)", key="nav_to_home", help="Zpět na novinky"):
        st.session_state.page = "Domů"
        st.rerun()
    st.markdown('<div class="nav-pill-static" style="pointer-events: none;">🏠 Domů</div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>Kvádr AI</h2>", unsafe_allow_html=True)
    st.write("---")
    if st.button("🏠 DOMOVSKÁ STRÁNKA", use_container_width=True):
        st.session_state.page = "Domů"
        st.rerun()
    if st.button("💬 AI CHAT", use_container_width=True):
        st.session_state.page = "AI Chat"
        st.rerun()
    st.write("---")
    st.caption(f"Aktivní model: {st.session_state.model_name.split('/')[-1]}")

# ==========================================
# 5. STRÁNKA: DOMŮ
# ==========================================
if st.session_state.page == "Domů":
    st.title("Oznámení a novinky")
    df_zpravy = nacti_data("List 2")
    
    if not df_zpravy.empty:
        for zprava in df_zpravy['zprava'].dropna():
            st.markdown(f'<div class="news-card">{zprava}</div>', unsafe_allow_html=True)
    else:
        st.info("Zatím žádné novinky.")

    with st.expander("🔐 Administrace"):
        heslo = st.text_input("Heslo", type="password")
        if heslo == "Heslo123":
            st.link_button("Upravit Google Tabulku", st.secrets["GSHEET_URL"])

# ==========================================
# 6. STRÁNKA: AI CHAT
# ==========================================
elif st.session_state.page == "AI Chat":
    st.title("💬 Kvádr AI Asistent")
    df_ai = nacti_data("List 1")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Zeptejte se mě na cokoliv..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            # Točící kolečko a lidský text
            with st.spinner("Kvádr AI přemýšlí..."):
                try:
                    model = genai.GenerativeModel(st.session_state.model_name)
                    kontext = " ".join(df_ai['zprava'].astype(str).tolist())
                    
                    full_prompt = f"""
                    Jsi Kvádr AI Asistent. Tvé znalosti jsou: {kontext}. 
                    Odpovídej jako člověk, buď milý, stručný a nápomocný. 
                    Mluv přirozeně, ne jako stroj.
                    Otázka: {prompt}
                    """
                    
                    response = model.generate_content(full_prompt)
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error("Teď mi to nemyslí (limit API). Zkus to za chvilku!")
