import streamlit as st
import pandas as pd
import requests
import time

# 1. ZÁKLADNÍ NASTAVENÍ
st.set_page_config(page_title="Kvadr AI Asistent", layout="wide")

try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
except:
    st.error("Chybí klíče v Secrets!")
    st.stop()

# 2. FUNKCE PRO TABULKU (ČTENÍ I ZÁPIS BEZ JSONu)
def nacti_data():
    try:
        # Čtení tabulky přes CSV export
        sheet_id = GSHEET_URL.split("/d/")[1].split("/")[0]
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=List1"
        df = pd.read_csv(url)
        return df
    except:
        return pd.DataFrame(columns=['zprava'])

def uloz_do_tabulky(novy_text):
    """
    Použijeme trik s Google Apps Scriptem nebo jednodušší metodu: 
    V této verzi budeme data ukládat do dočasné paměti aplikace, 
    protože plný zápis do Sheets bez JSONu vyžaduje Service Account.
    """
    if "local_data" not in st.session_state:
        st.session_state.local_data = nacti_data()
    
    novy_radek = pd.DataFrame([[str(novy_text)]], columns=['zprava'])
    st.session_state.local_data = pd.concat([st.session_state.local_data, novy_radek], ignore_index=True)
    return True

# 3. DIAGNOSTIKA MODELU (Vynucení funkční verze)
@st.cache_resource
def najdi_funkcni_model():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    try:
        res = requests.get(url).json()
        for m in res.get("models", []):
            if "generateContent" in m["supportedGenerationMethods"] and "gemini" in m["name"]:
                return m["name"]
        return "models/gemini-1.5-flash"
    except:
        return "models/gemini-1.5-flash"

# --- HLAVNÍ LOGIKA ---
if "local_data" not in st.session_state:
    st.session_state.local_data = nacti_data()

funkcni_model = najdi_funkcni_model()

# SIDEBAR (LEVÝ PANEL)
with st.sidebar:
    st.title("📌 Trvalá paměť")
    st.write("Informace pro AI:")
    
    # Zobrazení dat
    if not st.session_state.local_data.empty:
        for zpr in st.session_state.local_data['zprava'].dropna():
            st.info(zpr)
    
    st.divider()
    st.subheader("➕ Přidat informaci")
    heslo = st.text_input("Zadej heslo (mojeheslo)", type="password")
    if heslo == "mojeheslo":
        nova_zprava = st.text_area("Co si mám pamatovat?")
        if st.button("Uložit"):
            if nova_zprava:
                uloz_do_tabulky(nova_zprava)
                st.success("Informace přidána!")
                time.sleep(1)
                st.rerun()

# HLAVNÍ CHAT
st.title("Kvádr AI Asistent")

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
        kontext = " ".join(st.session_state.local_data['zprava'].astype(str).tolist())
        url_ai = f"https://generativelanguage.googleapis.com/v1beta/{funkcni_model}:generateContent?key={API_KEY}"
        payload = {"contents": [{"parts": [{"text": f"Znalosti: {kontext}\n\nUživatel: {prompt}"}]}]}
        
        try:
            res = requests.post(url_ai, json=payload).json()
            odpoved = res['candidates'][0]['content']['parts'][0]['text']
            st.markdown(odpoved)
            st.session_state.messages.append({"role": "assistant", "content": odpoved})
        except:
            st.error("AI selhala při generování.")
