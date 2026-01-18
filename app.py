import streamlit as st
import pandas as pd
import requests
import json
from gspread_pandas import Spread

st.set_page_config(page_title="Master AI", layout="wide")

# 1. NAČTENÍ KLÍČŮ
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
except:
    st.error("Chybí klíče v Secrets!")
    st.stop()

# 2. FUNKCE PRO ZÍSKÁNÍ SEZNAMU MODELŮ (DIAGNOSTIKA)
def najdi_dostupny_model():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    try:
        response = requests.get(url)
        data = response.json()
        if "models" in data:
            # Hledáme modely, které umí generovat obsah
            for m in data["models"]:
                if "generateContent" in m["supportedGenerationMethods"]:
                    return m["name"] # Vrátí např. "models/gemini-1.5-flash-latest"
        return "models/gemini-pro" # Nouzovka
    except:
        return "models/gemini-pro"

# 3. FUNKCE PRO AI
def volej_ai(prompt, kontext, model_path):
    # Použijeme přesnou cestu, kterou nám poradil Google
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent?key={API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"parts": [{"text": f"{kontext}\n\nUživatel: {prompt}"}]}]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    res_data = response.json()
    
    if response.status_code == 200:
        return res_data['candidates'][0]['content']['parts'][0]['text']
    else:
        return f"Chyba {response.status_code}: {json.dumps(res_data)}"

# 4. ROZHRANÍ
st.title("🤖 AI Asistent - Diagnostický režim")

# Zjistíme, co tvůj klíč skutečně vidí
if "model_to_use" not in st.session_state:
    with st.spinner("Zjišťuji dostupné modely..."):
        st.session_state.model_to_use = najdi_dostupny_model()

st.caption(f"Používaný model: {st.session_state.model_to_use}")

# Načtení dat z tabulky
try:
    s = Spread(GSHEET_URL)
    data = s.sheet_to_df(sheet='List1', index=None)
except:
    data = pd.DataFrame(columns=['zprava'])

# CHAT
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
        kontext = "Znalosti: " + " ".join(data['zprava'].tolist()) if not data.empty else ""
        odpoved = volej_ai(prompt, kontext, st.session_state.model_to_use)
        st.markdown(odpoved)
        st.session_state.messages.append({"role": "assistant", "content": odpoved})
