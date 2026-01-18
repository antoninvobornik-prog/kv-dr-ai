import streamlit as st
import google.generativeai as genai
import pandas as pd
from gspread_pandas import Spread

# 1. NASTAVENÍ
st.set_page_config(page_title="Můj AI Asistent", layout="wide")

api_key = st.secrets["GOOGLE_API_KEY"]
gsheet_url = st.secrets["GSHEET_URL"]

# 2. KONFIGURACE AI (verze 0.8.3)
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. FUNKCE PRO TABULKU
def nacti_data():
    try:
        s = Spread(gsheet_url)
        return s.sheet_to_df(sheet='List1', index=None)
    except:
        return pd.DataFrame(columns=['zprava'])

# 4. CHAT A INTERFACE
st.title("🤖 Tvůj AI Asistent")
data = nacti_data()

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
            # S novou verzí knihovny tohle už projde bez 404
            response = model.generate_content(prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Chyba: {e}")
