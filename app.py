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
except Exception:
    st.error("Chyba v Secrets! Zkontroluj GOOGLE_API_KEY a GSHEET_URL.")
    st.stop()

# 3. KONFIGURACE AI - VYNUCENÍ VERZE v1
# Tady jsme přidali transport='rest', což často řeší chyby s verzemi
genai.configure(api_key=api_key, transport='rest')

# Definujeme model bez prefixu models/, knihovna si ho doplní sama správně
model = genai.GenerativeModel('gemini-1.5-flash')

# 4. FUNKCE PRO TABULKU
def nacti_data():
    try:
        s = Spread(gsheet_url)
        df = s.sheet_to_df(sheet='List1', index=None)
        return df
    except:
        return pd.DataFrame(columns=['zprava'])

def uloz_data(nova_zprava):
    try:
        s = Spread(gsheet_url)
        df = nacti_data()
        novy_radek = pd.DataFrame([[nova_zprava]], columns=['zprava'])
        df = pd.concat([df, novy_radek], ignore_index=True)
        s.df_to_sheet(df, index=False, sheet='List1', replace=True)
    except Exception as e:
        st.error(f"Chyba zápisu: {e}")

# 5. DESIGN STRÁNKY
st.title("🤖 Tvůj AI Asistent")

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
            st.success("Uloženo!")
            st.rerun()

# 6. CHAT
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Napiš něco..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    kontext = "Kontext z tabulky: " + ", ".join(data['zprava'].astype(str).tolist())
    
    with st.chat_message("assistant"):
        try:
            # Přímé volání, které by už nemělo padat do v1beta
            response = model.generate_content(f"{kontext}\n\nDotaz: {prompt}")
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"AI se nepodařilo odpovědět: {e}")
