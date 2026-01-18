import streamlit as st
import google.generativeai as genai
import pandas as pd
from gspread_pandas import Spread

# 1. NASTAVENÍ STRÁNKY
st.set_page_config(page_title="Můj AI Asistent", layout="wide")

# 2. NAČTENÍ KLÍČŮ ZE SECRETS
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    gsheet_url = st.secrets["GSHEET_URL"]
except Exception as e:
    st.error("Chybí klíče v Secrets! Zkontroluj nastavení Streamlitu.")
    st.stop()

# 3. KONFIGURACE AI
genai.configure(api_key=api_key)

# Použijeme stabilní verzi modelu
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

# 4. FUNKCE PRO TABULKU
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
        novy_radek = pd.DataFrame([[nova_zprava]], columns=['zprava'])
        df = pd.concat([df, novy_radek], ignore_index=True)
        s.df_to_sheet(df, index=False, sheet='List1', replace=True)
    except Exception as e:
        st.error(f"Nepodařilo se uložit do tabulky: {e}")

# 5. DESIGN STRÁNKY
st.title("🤖 KVÁDR AI Asistent")

data = nacti_data()

with st.sidebar:
    st.header("📌 Trvalé informace")
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
    kontext_text = ""
    if not data.empty:
        kontext_text = "Pamatuj si tyto důležité informace o majiteli: " + ", ".join(data['zprava'].astype(str).tolist())
    
    with st.chat_message("assistant"):
        try:
            full_prompt = f"{kontext_text}\n\nUživatel se ptá: {prompt}"
            # Používáme nejstabilnější metodu generování
            response = model.generate_content(full_prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"AI se nepodařilo odpovědět: {e}")
