import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse

# ==========================================
# 1. CHYTRÁ KONFIGURACE AI (Hledá funkční model)
# ==========================================
if "model_name" not in st.session_state:
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        # Najde dostupné modely
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if available_models:
            # Vybere první funkční (často gemini-1.5-flash)
            st.session_state.model_name = available_models[0]
        else:
            st.session_state.model_name = "models/gemini-1.5-flash"
    except Exception:
        st.session_state.model_name = "models/gemini-1.5-flash"

# ==========================================
# 2. DESIGN A STYLING
# ==========================================
st.set_page_config(page_title="Kvádr AI Asistent", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #070b14; color: #e0e0e0; }
    [data-testid="stSidebar"] { background-color: #0b111e !important; border-right: 1px solid #1e293b; }
    .news-card {
        background: rgba(59, 130, 246, 0.1);
        border: 1px solid rgba(59, 130, 246, 0.3);
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 15px;
    }
    .logo-text { font-weight: bold; font-size: 1.5rem; color: #3b82f6; letter-spacing: 1px; }
    .stButton > button { width: 100%; border-radius: 10px; background-color: #1e293b; color: white; border: 1px solid #334155; }
    .stButton > button:hover { border-color: #3b82f6; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. FUNKCE PRO NAČÍTÁNÍ DAT (List 1 a List 2)
# ==========================================
@st.cache_data(ttl=60)
def nacti_data(nazev_listu):
    try:
        base_url = st.secrets["GSHEET_URL"]
        sheet_id = base_url.split("/d/")[1].split("/")[0]
        nazev_opraveny = urllib.parse.quote(nazev_listu)
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nazev_opraveny}"
        return pd.read_csv(csv_url)
    except Exception:
        return pd.DataFrame(columns=['zprava'])

# ==========================================
# 4. NAVIGACE
# ==========================================
if "page" not in st.session_state:
    st.session_state.page = "Domů"

with st.sidebar:
    st.markdown('<div class="logo-text">Kvádr AI Asistent</div>', unsafe_allow_html=True)
    st.write("---")
    if st.button("🏠 DOMOVSKÁ STRÁNKA"):
        st.session_state.page = "Domů"
    if st.button("💬 AI CHAT"):
        st.session_state.page = "AI Chat"
    st.write("---")
    st.caption(f"🤖 Model: {st.session_state.model_name.split('/')[-1]}")

# ==========================================
# 5. STRÁNKA: DOMŮ (Zprávy z List 2)
# ==========================================
if st.session_state.page == "Domů":
    st.title("Oznámení a novinky")
    
    # List 2 s mezerou
    df_zpravy = nacti_data("List 2")
    
    if not df_zpravy.empty:
        for zprava in df_zpravy['zprava'].dropna():
            st.markdown(f'<div class="news-card">{zprava}</div>', unsafe_allow_html=True)
    else:
        st.info("Zatím tu nejsou žádné zprávy. Přidej je do tabulky (List 2).")

    st.write("---")
    with st.expander("🔐 Správa"):
        heslo = st.text_input("Heslo pro úpravy", type="password")
        if heslo == "Heslo123":
            st.link_button("Otevřít Google Tabulku", st.secrets["GSHEET_URL"])

# ==========================================
# 6. STRÁNKA: AI CHAT (Data z List 1)
# ==========================================
elif st.session_state.page == "AI Chat":
    st.title("💬 Kvádr AI Asistent")

    # List 1 s mezerou
    df_ai = nacti_data("List 1")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Zobrazení historie chatu
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Vstup od uživatele
    if prompt := st.chat_input("Napište svou otázku..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                model = genai.GenerativeModel(st.session_state.model_name)
                
                # Sestavení kontextu z List 1
                kontext = " ".join(df_ai['zprava'].astype(str).tolist())
                full_prompt = f"Jsi Kvádr AI Asistent. Tvé znalosti: {kontext}. Odpověz na: {prompt}"
                
                response = model.generate_content(full_prompt)
                
                if response.text:
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error("Došlo k vyčerpání limitů. Prosím, počkejte minutu.")
                st.caption(f"Chyba: {e}")
