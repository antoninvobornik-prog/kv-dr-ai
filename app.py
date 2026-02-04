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

# ==========================================
# 2. STYLING (Čitelnost, Animace, Vzhled)
# ==========================================
st.markdown("""
<style>
    /* Základní čisté písmo a velká velikost pro čitelnost */
    html, body, [class*="st-"] {
        font-family: 'Arial', sans-serif !important;
        font-size: 20px !important;
    }

    .stApp { background-color: #070b14; color: #ffffff; }

    /* Blikající animace pro ikonu chatu */
    @keyframes slowBlink {
        0% { opacity: 1; }
        50% { opacity: 0.2; }
        100% { opacity: 1; }
    }
    .blink-chat { animation: slowBlink 2s infinite; color: #3b82f6; font-weight: bold; }

    /* Styl pro horní navigační lištu na mobilu */
    .top-nav {
        background-color: #162033;
        padding: 15px;
        border-radius: 12px;
        border: 2px solid #3b82f6;
        text-align: center;
        margin-bottom: 25px;
    }
    .nav-label { font-size: 24px !important; font-weight: bold; }

    /* Styl karet s novinkami */
    .news-card {
        background: #1e293b;
        border-radius: 15px;
        padding: 25px;
        margin-bottom: 20px;
        border-left: 8px solid #3b82f6;
        line-height: 1.6;
    }

    /* Úprava tlačítek v menu */
    .stButton > button {
        height: 60px;
        font-size: 20px !important;
        background-color: #3b82f6;
        color: white;
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. FUNKCE PRO NAČÍTÁNÍ DAT
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
# 4. NAVIGACE A LOGIKA STRÁNEK
# ==========================================
if "page" not in st.session_state:
    st.session_state.page = "Domů"

with st.sidebar:
    st.markdown("## HLAVNÍ MENU")
    if st.button("🏠 DOMOVSKÁ STRÁNKA"):
        st.session_state.page = "Domů"
    if st.button("💬 AI CHAT"):
        st.session_state.page = "AI Chat"
    st.write("---")
    st.caption(f"Verze pro snadné ovládání")

# Zobrazení navigačního pomocníka nahoře (viditelný hlavně na mobilu)
if st.session_state.page == "Domů":
    st.markdown('<div class="top-nav"><span class="blink-chat">💬 Kvádr AI</span> (Menu vlevo)</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="top-nav">🏠 Domů (Menu vlevo)</div>', unsafe_allow_html=True)

# ==========================================
# 5. STRÁNKA: DOMŮ
# ==========================================
if st.session_state.page == "Domů":
    st.title("Novinky a oznámení")
    df_zpravy = nacti_data("List 2")
    
    if not df_zpravy.empty:
        for zprava in df_zpravy['zprava'].dropna():
            st.markdown(f'<div class="news-card">{zprava}</div>', unsafe_allow_html=True)
    else:
        st.info("Zatím zde nejsou žádné zprávy.")

    with st.expander("🔐 Správa"):
        heslo = st.text_input("Zadejte heslo", type="password")
        if heslo == "Heslo123":
            st.link_button("Otevřít tabulku pro úpravy", st.secrets["GSHEET_URL"])

# ==========================================
# 6. STRÁNKA: AI CHAT
# ==========================================
elif st.session_state.page == "AI Chat":
    st.title("💬 Kvádr AI Asistent")
    
    df_ai = nacti_data("List 1")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Zobrazení chatu
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Vstup
    if prompt := st.chat_input("Zde napište svou otázku..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            # Točící se kolečko a text při načítání
            with st.spinner("Kvádr AI přemýšlí..."):
                try:
                    model = genai.GenerativeModel(st.session_state.model_name)
                    kontext = " ".join(df_ai['zprava'].astype(str).tolist())
                    
                    # Instrukce pro lidštější chování
                    system_prompt = f"""
                    Jsi Kvádr AI Asistent, přátelský a lidský společník. 
                    Tvé znalosti jsou: {kontext}. 
                    Odpovídej vlídně, srozumitelně a nepoužívej složité technické výrazy. 
                    Pokud něco nevíš, přiznej to lidsky. 
                    Odpověz na: {prompt}
                    """
                    
                    response = model.generate_content(system_prompt)
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error("Omlouvám se, ale jsem teď trochu unavený (limit API). Zkus to prosím za minutku.")
