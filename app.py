# ==========================================
# KOMPLEXNÍ AI ASISTENT S PAMĚTÍ V TABULCE
# Verze: 2.1 - Oprava parametru Markdown
# ==========================================

import streamlit as st
import google.generativeai as genai
import pandas as pd
import time
from gspread_pandas import Spread
from google.api_core import exceptions

# 1. ZÁKLADNÍ KONFIGURACE STREAMLITU
st.set_page_config(
    page_title="Můj Profesionální AI Asistent",
    page_icon="🤖",
    layout="wide"
)

# --- STYLOVÁNÍ (OPRAVENO) ---
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. NAČTENÍ KONFIGURACE ZE SECRETS
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
except Exception:
    st.error("❌ Chybí údaje v Secrets!")
    st.stop()

# 3. INICIALIZACE GOOGLE AI (GEMINI)
try:
    genai.configure(api_key=API_KEY, transport='rest')
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"❌ Chyba AI: {e}")
    st.stop()

# 4. FUNKCE PRO PRÁCI S GOOGLE TABULKOU
def nacti_data_z_tabulky():
    try:
        s = Spread(GSHEET_URL)
        df = s.sheet_to_df(sheet='List1', index=None)
        return df
    except Exception:
        return pd.DataFrame(columns=['zprava'])

def uloz_novou_informaci(text):
    try:
        with st.spinner("Ukládám..."):
            s = Spread(GSHEET_URL)
            df_stary = nacti_data_z_tabulky()
            novy_radek = pd.DataFrame([[str(text)]], columns=['zprava'])
            df_novy = pd.concat([df_stary, novy_radek], ignore_index=True)
            s.df_to_sheet(df_novy, index=False, sheet='List1', replace=True)
            return True
    except Exception as e:
        st.error(f"Chyba zápisu: {e}")
        return False

# 5. SIDEBAR
with st.sidebar:
    st.title("⚙️ Správa paměti")
    data = nacti_data_z_tabulky()
    
    st.subheader("📌 Co už vím:")
    if not data.empty:
        for i, radek in data.iterrows():
            st.info(radek['zprava'])
    
    st.divider()
    heslo = st.text_input("🔑 Heslo", type="password")
    if heslo == "mojeheslo":
        nova_zprava = st.text_area("Nová informace:")
        if st.button("💾 Uložit"):
            if uloz_novou_informaci(nova_zprava):
                st.success("Uloženo!")
                time.sleep(1)
                st.rerun()

# 6. CHAT
st.header("🤖 Tvůj Osobní AI Asistent")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Napiš něco..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            znalosti = data['zprava'].tolist() if not data.empty else []
            kontext = "Tvoje trvalé znalosti: " + " | ".join(znalosti)
            
            with st.spinner("Přemýšlím..."):
                response = model.generate_content(f"{kontext}\n\nUživatel: {prompt}")
                res_text = response.text
            
            st.markdown(res_text)
            st.session_state.messages.append({"role": "assistant", "content": res_text})
            
        except Exception as e:
            st.error(f"Chyba: {e}")
