import streamlit as st
import pandas as pd
import requests
import json
import time
from gspread_pandas import Spread

# 1. NASTAVENÍ STRÁNKY
st.set_page_config(page_title="Můj AI Asistent", layout="wide")

# Styl pro sidebar
st.markdown("""
    <style>
    .stInfo { font-size: 14px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# Načtení klíčů ze Secrets
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
except:
    st.error("Chybí klíče v Secrets!")
    st.stop()

# 2. DIAGNOSTIKA MODELU (To, co nám právě zachránilo krk)
@st.cache_resource # Zjistíme to jen jednou, aby to bylo rychlé
def najdi_funkcni_model():
    # Zkusíme v1beta seznam modelů
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    try:
        response = requests.get(url)
        data = response.json()
        if "models" in data:
            for m in data["models"]:
                # Hledáme Gemini model, který umí odpovídat
                if "generateContent" in m["supportedGenerationMethods"] and "gemini" in m["name"]:
                    return m["name"]
        return "models/gemini-pro"
    except:
        return "models/gemini-pro"

# 3. FUNKCE PRO PRÁCI S TABULKOU
def nacti_data():
    try:
        s = Spread(GSHEET_URL)
        df = s.sheet_to_df(sheet='List1', index=None)
        return df
    except:
        return pd.DataFrame(columns=['zprava'])

def uloz_do_tabulky(text):
    try:
        s = Spread(GSHEET_URL)
        df = nacti_data()
        novy = pd.DataFrame([[str(text)]], columns=['zprava'])
        df_final = pd.concat([df, novy], ignore_index=True)
        s.df_to_sheet(df_final, index=False, sheet='List1', replace=True)
        return True
    except Exception as e:
        st.error(f"Chyba tabulky: {e}")
        return False

# 4. FUNKCE PRO VOLÁNÍ AI
def volej_ai(prompt, kontext, model_path):
    # Použijeme v1beta, protože ta nám teď zafungovala
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    cely_text = f"Tvoje trvalé znalosti: {kontext}\n\nUživatel: {prompt}"
    payload = {"contents": [{"parts": [{"text": cely_text}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        res_data = response.json()
        return res_data['candidates'][0]['content']['parts'][0]['text']
    except:
        return "Omlouvám se, ale AI se nepodařilo odpovědět."

# --- HLAVNÍ ČÁST APLIKACE ---

# Načtení dat a modelu
data = nacti_data()
funkcni_model = najdi_funkcni_model()

# LEVÝ PANEL (TABULKA)
with st.sidebar:
    st.title("📌 Trvalá paměť")
    st.write("Informace načtené z Google Sheets:")
    
    if not data.empty:
        for zpr in data['zprava']:
            st.info(zpr)
    else:
        st.caption("Tabulka je prázdná nebo nedostupná.")

    st.divider()
    
    # Přidávání nových informací
    st.subheader("➕ Přidat informaci")
    heslo = st.text_input("Zadej heslo (mojeheslo)", type="password")
    if heslo == "mojeheslo":
        nova_inf = st.text_area("Co si mám pamatovat?")
        if st.button("Uložit navždy"):
            if uloz_do_tabulky(nova_info):
                st.success("Uloženo do tabulky!")
                time.sleep(1)
                st.rerun()

# HLAVNÍ CHAT
st.title("🤖 Tvůj AI Asistent")
st.caption(f"Aktivní model: {funkcni_model}")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Zobrazení historie
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Vstup uživatele
if prompt := st.chat_input("Napiš něco..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Přemýšlím..."):
            kontext_text = " ".join(data['zprava'].tolist()) if not data.empty else ""
            odpoved = volej_ai(prompt, kontext_text, funkcni_model)
            st.markdown(odpoved)
            st.session_state.messages.append({"role": "assistant", "content": odpoved})
