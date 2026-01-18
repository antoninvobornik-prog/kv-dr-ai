import streamlit as st
import google.generativeai as genai
import pandas as pd
from gspread_pandas import Spread

# 1. NASTAVENÍ STRÁNKY
st.set_page_config(page_title="Můj AI Asistent", layout="wide")

# 2. NAČTENÍ KLÍČŮ ZE SECRETS
api_key = st.secrets["GOOGLE_API_KEY"]
gsheet_url = st.secrets["GSHEET_URL"]

# 3. KONFIGURACE AI
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro')

# 4. FUNKCE PRO TABULKU
def nacti_data():
    try:
        s = Spread(gsheet_url)
        df = s.sheet_to_df(sheet='List1', index=None)
        return df
    except:
        return pd.DataFrame(columns=['zprava'])

def uloz_data(nova_zprava):
    s = Spread(gsheet_url)
    df = nacti_data()
    novy_radek = pd.DataFrame([[nova_zprava]], columns=['zprava'])
    df = pd.concat([df, novy_radek], ignore_index=True)
    s.df_to_sheet(df, index=False, sheet='List1', replace=True)

# 5. DESIGN ASTRÁNKY
st.title("🤖 Kvádr AI Asistent")

with st.sidebar:
    st.header("📌 Trvalé informace")
    data = nacti_data()
    if not data.empty:
        for zpr in data['zprava']:
            st.info(zpr)
    else:
        st.write("V databázi zatím nejsou žádné zprávy.")
    
    st.divider()
    heslo = st.text_input("Zadej heslo pro úpravy", type="password")
    if heslo == "mojeheslo":
        nova_inf = st.text_area("Co si mám pamatovat navždy?")
        if st.button("Uložit navždy"):
            uloz_data(nova_inf)
            st.success("Uloženo! Obnovuji...")
            st.rerun()

# 6. CHAT
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Zeptej se mě na cokoliv..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Příprava kontextu z tabulky
    kontext = "Pamatuj si tyto důležité informace: " + ", ".join(data['zprava'].tolist())
    
    with st.chat_message("assistant"):
        try:
            full_prompt = f"{kontext}\n\nUživatel se ptá: {prompt}"
            response = model.generate_content(full_prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"AI se nepodařilo odpovědět: {e}")
