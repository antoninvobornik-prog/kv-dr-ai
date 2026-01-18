import streamlit as st
import google.generativeai as genai
import pandas as pd
from gspread_pandas import Spread

st.set_page_config(page_title="Můj AI Asistent", layout="wide")

# NAČTENÍ KLÍČŮ
api_key = st.secrets["GOOGLE_API_KEY"]
gsheet_url = st.secrets["GSHEET_URL"]

# TADY JE TA ZMĚNA - VYNUCENÍ STABILNÍ VERZE
genai.configure(api_key=api_key, transport='rest')

def nacti_data():
    try:
        s = Spread(gsheet_url)
        return s.sheet_to_df(sheet='List1', index=None)
    except:
        return pd.DataFrame(columns=['zprava'])

st.title("🤖 Tvůj AI Asistent")
data = nacti_data()

# LEVÝ PANEL
with st.sidebar:
    st.header("📌 Trvalé informace")
    if not data.empty:
        for zpr in data['zprava']:
            st.info(zpr)
    
    st.divider()
    heslo = st.text_input("Heslo", type="password")
    if heslo == "mojeheslo":
        nova_inf = st.text_area("Nová informace")
        if st.button("Uložit"):
            s = Spread(gsheet_url)
            df = nacti_data()
            novy = pd.DataFrame([[nova_inf]], columns=['zprava'])
            df = pd.concat([df, novy], ignore_index=True)
            s.df_to_sheet(df, index=False, sheet='List1', replace=True)
            st.rerun()

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
        try:
            # POUŽIJEME GEMINI-1.5-FLASH, ALE PŘES REST
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Chyba: {e}")
