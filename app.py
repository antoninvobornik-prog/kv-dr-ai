import streamlit as st
import pandas as pd
import requests
import json
import time
from gspread_pandas import Spread

# 1. NASTAVENÍ STRÁNKY
st.set_page_config(page_title="Můj AI Asistent", layout="wide")

st.markdown("""
    <style>
    .stInfo { font-size: 14px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# Načtení klíčů
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
except:
    st.error("Chybí klíče v Secrets!")
    st.stop()

# 2. DIAGNOSTIKA MODELU
@st.cache_resource
def najdi_funkcni_model():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    try:
        response = requests.get(url)
        data = response.json()
        if "models" in data:
            for m in data["models"]:
                if "generateContent" in m["supportedGenerationMethods"] and "gemini" in m["name"]:
                    return m["name"]
        return "models/gemini-pro"
    except:
        return "models/gemini-pro"

# 3. FUNKCE PRO TABULKU
def nacti_data():
    try:
        s = Spread(GSHEET_URL)
        df = s.sheet_to_df(sheet='List1', index=None)
        return df
    except:
        return pd.DataFrame(columns=['zprava'])

def uloz_do_tabulky(text_ke_uloz):
    try:
        s = Spread(GSHEET_URL)
        df = nacti_data()
        novy = pd.DataFrame([[str(text_ke_uloz)]], columns=['zprava'])
        df_final = pd.concat([df, novy], ignore_index=True)
        s.df_to_sheet(df_final, index=False, sheet='List1', replace=True)
        return True
    except Exception as e:
        st.error(f"Chyba tabulky: {e}")
        return False

# --- LOGIKA APLIKACE ---
data = nacti_data()
funkcni_model = najdi_funkcni_model()

# LEVÝ PANEL
with st.sidebar:
    st.title("📌 Trvalá paměť")
    st.write("Informace z Google Sheets:")
    
    if not data.empty:
        for zpr in data['zprava']:
            st.info(zpr)
    else:
        st.caption("Tabulka je prázdná nebo není nasdílená.")

    st.divider()
    
    st.subheader("➕ Přidat informaci")
    heslo = st.text_input("Zadej heslo (mojeheslo)", type="password")
    if heslo == "mojeheslo":
        # TADY BYLA CHYBA - OPRAVENO NA nova_zprava
        nova_zprava = st.text_area("Co si mám pamatovat?")
        if st.button("Uložit navždy"):
            if nova_zprava:
                if uloz_do_tabulky(nova_zprava):
                    st.success("Uloženo!")
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("Napiš text.")

# HLAVNÍ CHAT
st.title("🤖 Tvůj AI Asistent")
st.caption(f"Aktivní model: {funkcni_model}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Napiš něco..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Přemýšlím..."):
            kontext_text = " ".join(data['zprava'].astype(str).tolist()) if not data.empty else ""
            
            # VOLÁNÍ AI PŘES FUNKČNÍ CESTU
            url_ai = f"https://generativelanguage.googleapis.com/v1beta/{funkcni_model}:generateContent?key={API_KEY}"
            payload = {"contents": [{"parts": [{"text": f"Znalosti: {kontext_text}\n\nUživatel: {prompt}"}]}]}
            
            try:
                res = requests.post(url_ai, json=payload)
                odpoved = res.json()['candidates'][0]['content']['parts'][0]['text']
                st.markdown(odpoved)
                st.session_state.messages.append({"role": "assistant", "content": odpoved})
            except:
                st.error("AI selhala při generování.")
