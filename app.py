import streamlit as st
import google.generativeai as genai
import pandas as pd
from gspread_pandas import Spread

st.set_page_config(page_title="Můj AI Asistent", layout="wide")

# 1. NASTAVENÍ KLÍČŮ (Opraveno na verzi v1)
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    gsheet_url = st.secrets["GSHEET_URL"]
    
    # Tady vynutíme stabilní verzi v1
    from google.generativeai import types
    genai.configure(api_key=api_key)
    
    # Použijeme model gemini-1.5-flash ve verzi v1
    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        generation_config={"api_version": "v1"} # Tady je ten trik!
    )
except Exception as e:
    st.error(f"Chyba nastavení: {e}")
    st.stop()

# 2. NAČTENÍ TABULKY
def nacti_data():
    try:
        s = Spread(gsheet_url)
        return s.sheet_to_df(sheet='List1', index=None)
    except:
        return pd.DataFrame(columns=['zprava'])

st.title("🤖 Tvůj AI Asistent")
data = nacti_data()

# LEVÝ PANEL (Sidebar)
with st.sidebar:
    st.header("📌 Paměť AI")
    if not data.empty:
        for zpr in data['zprava']:
            st.info(zpr)
    
    st.divider()
    heslo = st.text_input("Zadej: mojeheslo", type="password")
    if heslo == "mojeheslo":
        nova_inf = st.text_area("Co si pamatovat?")
        if st.button("Uložit"):
            s = Spread(gsheet_url)
            df = nacti_data()
            novy = pd.DataFrame([[nova_inf]], columns=['zprava'])
            df = pd.concat([df, novy], ignore_index=True)
            s.df_to_sheet(df, index=False, sheet='List1', replace=True)
            st.rerun()

# 3. CHAT
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
            # Sestavení kontextu
            kontext = "Tvoje trvalé znalosti: " + ", ".join(data['zprava'].astype(str).tolist()) if not data.empty else ""
            # Volání modelu
            response = model.generate_content(f"{kontext}\n\nUživatel: {prompt}")
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"AI se stále nedaří: {e}")
            st.info("Zkus v menu Streamlitu 'Reboot', pokud vidíš stále 404.")
