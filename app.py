import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse

# ==========================================
# 1. DESIGN A KONFIGURACE
# ==========================================
st.set_page_config(page_title="KVÁDR AI", layout="wide")

def local_css():
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
        .logo-text { font-weight: bold; font-size: 1.5rem; color: white; letter-spacing: 2px; }
        .stButton > button { width: 100%; border-radius: 10px; background-color: #1e293b; color: white; }
    </style>
    """, unsafe_allow_html=True)

local_css()

# ==========================================
# 2. FUNKCE PRO NAČÍTÁNÍ DAT (S CACHE)
# ==========================================
# Tato funkce si zapamatuje data na 60 sekund. 
# Když obnovíš stránku (F5), nepoběží znovu pro data do Googlu, ale vezme je z paměti.
@st.cache_data(ttl=60)
def nacti_data(nazev_listu):
    try:
        base_url = st.secrets["GSHEET_URL"]
        sheet_id = base_url.split("/d/")[1].split("/")[0]
        nazev_opraveny = urllib.parse.quote(nazev_listu)
        # URL bez časového razítka, aby cache správně fungovala
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nazev_opraveny}"
        return pd.read_csv(csv_url)
    except Exception as e:
        return pd.DataFrame(columns=['zprava'])

# ==========================================
# 3. SIDEBAR - NAVIGACE
# ==========================================
if "page" not in st.session_state:
    st.session_state.page = "Domů"

with st.sidebar:
    st.markdown('<div class="logo-text">✦ KVÁDR AI</div>', unsafe_allow_html=True)
    st.write("---")
    if st.button("🏠 DOMŮ"):
        st.session_state.page = "Domů"
    if st.button("💬 AI CHAT"):
        st.session_state.page = "Kvádr AI Chat"
    st.write("---")
    st.info("Mezipaměť aktivní (50s).")

# ==========================================
# 4. STRÁNKA: DOMŮ
# ==========================================
if st.session_state.page == "Domů":
    st.title("Oznámení a novinky")
    
    df_zpravy = nacti_data("List 2")
    
    if not df_zpravy.empty:
        for zprava in df_zpravy['zprava'].dropna():
            st.markdown(f'<div class="news-card">{zprava}</div>', unsafe_allow_html=True)
    else:
        st.info("Zatím tu nejsou žádné zprávy. Upravte List 2 v tabulce.")

    st.write("---")
    with st.expander("🔐 Administrace"):
        heslo = st.text_input("Zadejte heslo", type="password")
        if heslo == "Heslo123":
            st.success("Přihlášen! Změny v tabulce se projeví do 1 minuty.")
            st.link_button("Upravit Google Tabulku", st.secrets["GSHEET_URL"])

# ==========================================
# 5. STRÁNKA: AI CHAT
# ==========================================
elif st.session_state.page == "Kvádr AI Chat":
    st.title("💬 Asistent KVÁDR")

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
            try:
                genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                kontext = " ".join(df_ai['zprava'].astype(str).tolist())
                full_prompt = f"Jsi asistent KVÁDR AI. Zde jsou tvé znalosti: {kontext}. Odpověz na: {prompt}"
                
                response = model.generate_content(full_prompt)
                st.markdown(response.text)
                st.session_state.chat_history.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error("Limit vyčerpán nebo chyba API. Počkejte chvíli (1 min.) a zkuste to znovu.")
                st.caption(f"Detail chyby: {e}")
