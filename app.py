import streamlit as st
import pandas as pd
import requests
import json
from gspread_pandas import Spread

# 1. ZÁKLADNÍ NASTAVENÍ
st.set_page_config(page_title="Můj AI Asistent", layout="wide")

# Načtení klíčů
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
except:
    st.error("Chybí klíče v Secrets!")
    st.stop()

# 2. FUNKCE PRO TABULKU
def nacti_data():
    try:
        s = Spread(GSHEET_URL)
        return s.sheet_to_df(sheet='List1', index=None)
    except:
        return pd.DataFrame(columns=['zprava'])

# 3. FUNKCE PRO VOLÁNÍ AI (OBCHÁZÍ CHYBU 404)
def volej_gemini(prompt, kontext):
    # Tady vynucujeme verzi v1 přímo v adrese - to už nejde přepsat
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    headers = {'Content-Type': 'json'}
    payload = {
        "contents": [{
            "parts": [{"text": f"{kontext}\n\nUživatel: {prompt}"}]
        }]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    vysledek = response.json()
    
    if response.status_code == 200:
        return vysledek['candidates'][0]['content']['parts'][0]['text']
    else:
        return f"Chyba serveru ({response.status_code}): {response.text}"

# 4. ROZHRANÍ
st.title("🤖 Tvůj AI Asistent (Stabilní verze)")
data = nacti_data()

with st.sidebar:
    st.header("📌 Paměť AI")
    if not data.empty:
        for zpr in data['zprava']:
            st.info(zpr)
    
    st.divider()
    if st.text_input("Heslo", type="password") == "mojeheslo":
        nova_inf = st.text_area("Nová informace")
        if st.button("Uložit"):
            s = Spread(GSHEET_URL)
            df = nacti_data()
            novy = pd.DataFrame([[nova_inf]], columns=['zprava'])
            df = pd.concat([df, novy], ignore_index=True)
            s.df_to_sheet(df, index=False, sheet='List1', replace=True)
            st.rerun()

# 5. CHAT
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
        with st.spinner("Odpovídám..."):
            kontext = "Tvoje znalosti: " + ", ".join(data['zprava'].tolist()) if not data.empty else ""
            odpoved = volej_gemini(prompt, kontext)
            st.markdown(odpoved)
            st.session_state.messages.append({"role": "assistant", "content": odpoved})
