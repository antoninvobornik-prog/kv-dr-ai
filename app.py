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

# 2. FUNKCE PRO TABULKU
def nacti_data():
    try:
        sheet_id = GSHEET_URL.split("/d/")[1].split("/")[0]
        # Načteme celou tabulku (včetně sloupce 'tajne')
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=List1"
        df = pd.read_csv(url)
        return df
    except:
        return pd.DataFrame(columns=['zprava', 'tajne'])

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

# SIDEBAR (LEVÝ PANEL)
with st.sidebar:
    st.title("📌 Informace")
    
    # VEŘEJNÉ INFORMACE (Vidí všichni)
    st.subheader("Veřejné info:")
    if not data.empty and 'zprava' in data.columns:
        for zpr in data['zprava'].dropna():
            st.info(zpr)
    
    st.divider()
    
    # SEKCE S HESLEM
    heslo = st.text_input("Zadej heslo pro správu", type="password")
    
    if heslo == "mojeheslo":
        st.success("Jsi přihlášen jako správce")
        
        # TAJNÉ INFORMACE (Vidí jen ten, kdo zná heslo)
        st.subheader("🕵️ Tajné instrukce pro AI:")
        if 'tajne' in data.columns:
            for t in data['tajne'].dropna():
                st.warning(t)
        
        st.caption("Tip: Pokud chceš upravovat, napiš to přímo do Google Tabulky do sloupce 'tajne'.")
    else:
        st.caption("Zadej heslo pro zobrazení tajných instrukcí.")

# HLAVNÍ CHAT
# Najdi tento řádek:
st.title("🤖 Kvadr AI Asistent")

# A hned pod něj přidej tento řádek:
st.caption("Tvůj inteligentní průvodce projektem Kvadr, který ti pomůže s odpověďmi v reálném čase.")

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
        # AI DOSTANE VŠE: Veřejné i Tajné informace
        verejne_info = " ".join(data['zprava'].astype(str).tolist()) if not data.empty else ""
        tajne_info = ""
        if 'tajne' in data.columns:
            tajne_info = " ".join(data['tajne'].astype(str).tolist())
        
        kontext = f"Veřejné info: {verejne_info} | Tajné instrukce: {tajne_info}"
        
        url_ai = f"https://generativelanguage.googleapis.com/v1beta/{funkcni_model}:generateContent?key={API_KEY}"
        payload = {"contents": [{"parts": [{"text": f"{kontext}\n\nUživatel: {prompt}"}]}]}
        
        try:
            res = requests.post(url_ai, json=payload).json()
            odpoved = res['candidates'][0]['content']['parts'][0]['text']
            st.markdown(odpoved)
            st.session_state.messages.append({"role": "assistant", "content": odpoved})
        except:
            st.error("AI selhala.")
