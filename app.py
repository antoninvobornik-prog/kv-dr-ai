import streamlit as st
import pandas as pd
import requests
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# 1. NASTAVENÍ
st.set_page_config(page_title="Můj AI Asistent", layout="wide")

try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
except:
    st.error("Chybí klíče v Secrets!")
    st.stop()

# 2. PŘIPOJENÍ K TABULCE (Zjednodušeno bez JSONu)
def nacti_data():
    try:
        # Připojení anonymně přes URL (tabulka musí být sdílená: "Všichni, kdo mají odkaz")
        sheet_id = GSHEET_URL.split("/d/")[1].split("/")[0]
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=List1"
        return pd.read_csv(url)
    except:
        return pd.DataFrame(columns=['zprava'])

# 3. DIAGNOSTIKA MODELU
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

# --- LOGIKA ---
data = nacti_data()
funkcni_model = najdi_funkcni_model()

# SIDEBAR
with st.sidebar:
    st.title("📌 Trvalá paměť")
    if not data.empty and 'zprava' in data.columns:
        for zpr in data['zprava'].dropna():
            st.info(zpr)
    else:
        st.caption("Tabulka je prázdná. Pro zápis je potřeba složitější nastavení, teď hlavně ať funguje čtení!")

# CHAT
st.title("🤖 Kvádr AI Asistent")
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
        kontext = " ".join(data['zprava'].astype(str).tolist()) if not data.empty else ""
        url_ai = f"https://generativelanguage.googleapis.com/v1beta/{funkcni_model}:generateContent?key={API_KEY}"
        payload = {"contents": [{"parts": [{"text": f"Znalosti: {kontext}\n\nUživatel: {prompt}"}]}]}
        
        try:
            res = requests.post(url_ai, json=payload).json()
            odpoved = res['candidates'][0]['content']['parts'][0]['text']
            st.markdown(odpoved)
            st.session_state.messages.append({"role": "assistant", "content": odpoved})
        except:
            st.error("AI selhala.")
