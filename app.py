import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse

# ==========================================
# 1. KONFIGURACE AI
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
# 2. DESIGN PODLE PŘEDLOHY (FOTKY) + ÚPRAVY
# ==========================================
st.markdown("""
<style>
    /* Pozadí s gradientem */
    .stApp {
        background: radial-gradient(circle at center, #1a2c4e 0%, #070b14 100%);
        color: #ffffff;
        font-family: 'Inter', sans-serif;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Centrování uvítacího obsahu */
    .welcome-container {
        text-align: center;
        padding-top: 40px;
    }
    .welcome-logo {
        background: rgba(59, 130, 246, 0.1);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 20px;
        padding: 20px;
        display: inline-block;
        margin-bottom: 20px;
    }
    .welcome-title { font-size: 32px; font-weight: bold; margin-bottom: 10px; }
    .welcome-subtitle { font-size: 18px; color: #94a3b8; margin-bottom: 30px; }
    .warning-text { font-size: 14px; color: #64748b; margin-top: 20px; }

    /* Horní blikající efekt pro aktivní tlačítko */
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.6); }
        70% { box-shadow: 0 0 0 12px rgba(59, 130, 246, 0); }
        100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
    }

    /* Karty novinek */
    .news-card {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid #1e293b;
        padding: 25px; border-radius: 15px;
        margin: 15px auto; max-width: 800px;
        font-size: 18px; line-height: 1.6;
    }

    /* Styl pro tlačítka v horní navigaci */
    .stButton > button {
        border-radius: 50px !important;
        font-weight: bold !important;
        font-size: 18px !important;
        transition: 0.3s;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. LOGIKA NAVIGACE (TLAČÍTKA NAHOŘE)
# ==========================================
cols = st.columns([1, 2, 1])
with cols[1]:
    if st.session_state.page == "Domů":
        # Tlačítko pro přechod do chatu, které bliká (definováno přes CSS animaci u aktivního prvku)
        if st.button("💬 Přejít na Kvádr AI Chat", use_container_width=True, type="primary"):
            st.session_state.page = "AI Chat"
            st.rerun()
    else:
        # Tlačítko pro návrat domů s emoji
        if st.button("🏠 Zpět na Domovskou stránku", use_container_width=True):
            st.session_state.page = "Domů"
            st.rerun()

# ==========================================
# 4. POMOCNÉ FUNKCE
# ==========================================
def nacti_data(nazev_listu):
    try:
        base_url = st.secrets["GSHEET_URL"]
        sheet_id = base_url.split("/d/")[1].split("/")[0]
        nazev_opraveny = urllib.parse.quote(nazev_listu)
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nazev_opraveny}"
        return pd.read_csv(csv_url)
    except: return pd.DataFrame(columns=['zprava'])

# ==========================================
# 5. OBSAH STRÁNEK
# ==========================================

# --- DOMOVSKÁ STRÁNKA ---
if st.session_state.page == "Domů":
    st.markdown("""
        <div class="welcome-container">
            <div class="welcome-logo"><span style="font-size: 40px;">🏠</span></div>
            <div class="welcome-title">🏠 Domovská stránka</div>
            <div class="welcome-subtitle">Aktuální oznámení a důležité novinky</div>
        </div>
    """, unsafe_allow_html=True)
    
    df_zpravy = nacti_data("List 2")
    if not df_zpravy.empty:
        for zprava in df_zpravy['zprava'].dropna():
            st.markdown(f'<div class="news-card">{zprava}</div>', unsafe_allow_html=True)
    else:
        st.info("Zatím zde nejsou žádná nová oznámení.")

# --- AI CHAT STRÁNKA ---
elif st.session_state.page == "AI Chat":
    # Uvítací obrazovka chatu
    if "chat_history" not in st.session_state or len(st.session_state.chat_history) == 0:
        st.markdown("""
            <div class="welcome-container">
                <div class="welcome-logo"><span style="font-size: 40px;">✨</span></div>
                <div class="welcome-title">Vítejte v KVÁDR AI</div>
                <div class="welcome-subtitle">Jsem váš osobní asistent. Ptejte se mě na cokoliv.</div>
                <div class="warning-text">ⓘ Kvádr AI může dělat chyby, kontrolujte důležité informace.</div>
            </div>
        """, unsafe_allow_html=True)
        st.session_state.chat_history = []

    # Zobrazení historie
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat vstup
    if prompt := st.chat_input("Napište svou zprávu..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Kvádr AI přemýšlí..."):
                try:
                    df_ai = nacti_data("List 1")
                    model = genai.GenerativeModel(st.session_state.model_name)
                    kontext = " ".join(df_ai['zprava'].astype(str).tolist())
                    
                    full_prompt = f"Jsi Kvádr AI Asistent. Tvé znalosti jsou: {kontext}. Odpověz na dotaz lidsky, přátelsky a srozumitelně: {prompt}"
                    
                    response = model.generate_content(full_prompt)
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                except:
                    st.error("Omlouvám se, momentálně mám plnou hlavu práce. Zkus to za minutku!")
