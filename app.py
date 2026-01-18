import streamlit as st
import google.generativeai as genai
import pandas as pd
from gspread_pandas import Spread

# 1. NASTAVENÍ STRÁNKY
st.set_page_config(page_title="Můj AI Asistent", layout="wide")

# 2. NAČTENÍ KLÍČŮ
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    gsheet_url = st.secrets["GSHEET_URL"]
    genai.configure(api_key=api_key)
    # ZMĚNA: Používáme verzi 1.0-pro, která netrpí chybou 404 v1beta
    model = genai.GenerativeModel('gemini-1.0-pro')
except Exception as e:
    st.error(f"Chyba nastavení: {e}")
    st.stop()

# 3. FUNKCE PRO TABULKU
def nacti_data():
    try:
        s = Spread(gsheet_url)
        df = s.sheet_to_df(sheet='List1', index=None)
        return df
    except Exception:
        return pd.DataFrame(columns=['zprava'])

def uloz_data(nova_zprava):
    try:
        s = Spread(gsheet_url)
        df = nacti_data()
        novy_radek = pd.DataFrame([[str(nova_zprava)]], columns=['zprava'])
        df = pd.concat([df, novy_radek], ignore_index=True)
        s.df_to_sheet(df, index=False, sheet='List1', replace=True)
        return True
    except Exception as e:
        st.error(f"Chyba zápisu do tabulky: {e}")
        return False

# 4. VYKRESLENÍ
st.title("🤖 Tvůj AI Asistent")
data = nacti_data()

# LEVÝ PANEL
with st.sidebar:
    st.header("📌 Trvalé informace")
    if not data.empty:
        for zpr in data['zprava']:
            st.info(zpr)
    
    st.divider()
    heslo = st.text_input("Zadej heslo pro úpravy", type="password")
    if heslo == "mojeheslo":
        nova_inf = st.text_area("Co si mám pamatovat?")
        if st.button("Uložit do paměti"):
            if uloz_data(nova_inf):
                st.success("Uloženo! Restartuji...")
                st.rerun()

# 5. CHAT
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
            # Sestavení kontextu z tabulky
            kontext = "Tvoje trvalé znalosti: " + ", ".join(data['zprava'].tolist()) if not data.empty else ""
            response = model.generate_content(f"{kontext}\n\nUživatel: {prompt}")
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Chyba AI: {e}")
