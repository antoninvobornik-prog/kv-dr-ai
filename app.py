import streamlit as st
import google.generativeai as genai
import pandas as pd
from gspread_pandas import Spread

# Nastavení stránky musí být VŽDY první
st.set_page_config(page_title="Můj AI Asistent", layout="wide")

# Načtení klíčů - s kontrolou, aby aplikace nespadla
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    gsheet_url = st.secrets["GSHEET_URL"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Chyba v nastavení klíčů: {e}")
    st.stop()

# Funkce pro načtení dat (v samostatném bloku, aby nezmizel zbytek webu)
def nacti_data():
    try:
        s = Spread(gsheet_url)
        return s.sheet_to_df(sheet='List1', index=None)
    except:
        return pd.DataFrame(columns=['zprava'])

# VYKRESLENÍ STRÁNKY
st.title("🤖 Tvůj AI Asistent")
data = nacti_data()

# LEVÝ PRUH (Sidebar)
with st.sidebar:
    st.header("📌 Trvalé informace")
    if not data.empty:
        for zpr in data['zprava']:
            st.info(zpr)
    else:
        st.write("Žádná data.")

# CHAT
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
            # Oprava: Vynucení stabilní verze modelu
            response = model.generate_content(prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"AI stále hlásí chybu: {e}")
