import streamlit as st
import pandas as pd
import requests

# ==============================================================================
# 1. DESIGN A TMAVÝ REŽIM
# ==============================================================================
st.set_page_config(page_title="Kvadr AI Asistent", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    .stInfo {
        background-color: #1f2937;
        color: #e5e7eb;
        border: 1px solid #3b82f6;
    }
    .stWarning {
        background-color: #2d2d00;
        color: #fef08a;
        border: 1px solid #ca8a04;
    }
    h1, h2, h3 {
        color: #ffffff !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Načtení klíčů
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
except:
    st.error("Chybí klíče v Secrets!")
    st.stop()

# ==============================================================================
# 2. NAČÍTÁNÍ DAT Z TABULKY
# ==============================================================================
def nacti_data():
    try:
        sheet_id = GSHEET_URL.split("/d/")[1].split("/")[0]
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=List1"
        df = pd.read_csv(url)
        return df
    except:
        return pd.DataFrame(columns=['zprava', 'tajne'])

data = nacti_data()

# ==============================================================================
# 3. LEVÝ PANEL (SIDEBAR)
# ==============================================================================
with st.sidebar:
    st.title("📌 Informace")
    
    st.subheader("O projektu:")
    if not data.empty and 'zprava' in data.columns:
        for zpr in data['zprava'].dropna():
            st.info(zpr)
    
    st.divider()
    
    heslo_input = st.text_input("Správa (heslo)", type="password")
    if heslo_input == "mojeheslo":
        st.success("Režim správce")
        if 'tajne' in data.columns:
            for t in data['tajne'].dropna():
                st.warning(t)
    else:
        st.caption("Zadejte heslo pro tajné instrukce.")

# ==============================================================================
# 4. HLAVNÍ CHAT A DESIGN NADPISŮ
# ==============================================================================
st.title("🤖 Kvadr AI Asistent")

# Tvůj specifický design
st.markdown("<p style='color: white; font-weight: bold; font-size: 1.1rem; margin-bottom: 5px;'>Tvůj inteligentní průvodce projektem Kvadr, který ti pomůže v reálném čase odpovědět na otázky ohledně Kvádru a ještě více!</p>", unsafe_allow_html=True)
st.markdown("<p style='color: gray; font-style: italic; font-size: 0.9rem; margin-top: 0px;'>POZOR MOHU DĚLAT CHYBY A NĚKTERÉ INFORMACE S KVÁDREM NEMUSÍM ZNÁT !</p>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Napiš svou otázku..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Hledám odpověď..."):
            # Příprava kontextu
            verejne = " ".join(data['zprava'].dropna().astype(str).tolist())
            tajne = " ".join(data['tajne'].dropna().astype(str).tolist()) if 'tajne' in data.columns else ""
            
            # OPRAVA: Používáme stabilnější verzi modelu v1
            url_ai = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"
            
            payload = {
                "contents": [{"parts": [{"text": f"INSTRUKCE: {tajne}\nINFO: {verejne}\nUživatel: {prompt}"}]}],
                "safetySettings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                ]
            }
            
            try:
                # Změna z v1beta na v1 v URL může vyřešit chybu 404
                response = requests.post(url_ai, json=payload)
                res = response.json()
                
                if 'candidates' in res:
                    odpoved = res['candidates'][0]['content']['parts'][0]['text']
                    st.markdown(odpoved)
                    st.session_state.messages.append({"role": "assistant", "content": odpoved})
                else:
                    st.error("AI narazila na problém. Zde je detail:")
                    st.json(res)
            except Exception as e:
                st.error(f"Chyba spojení: {e}")
