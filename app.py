import streamlit as st
import pandas as pd
import requests
import time

# ==============================================================================
# 1. DESIGN A TMAVÝ REŽIM (CSS)
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

# Načtení klíčů ze Secrets
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
except:
    st.error("Chybí klíče v Secrets!")
    st.stop()

# ==============================================================================
# 2. FUNKCE PRO DATA A MODEL
# ==============================================================================

def nacti_data():
    try:
        sheet_id = GSHEET_URL.split("/d/")[1].split("/")[0]
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=List1"
        df = pd.read_csv(url)
        return df
    except:
        return pd.DataFrame(columns=['zprava', 'tajne'])

@st.cache_resource
def najdi_funkcni_model():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    try:
        res = requests.get(url).json()
        for m in res.get("models", []):
            if "generateContent" in m["name"]:
                return m["name"]
        return "models/gemini-1.5-flash"
    except:
        return "models/gemini-1.5-flash"

data = nacti_data()
funkcni_model = najdi_funkcni_model()

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
# 4. HLAVNÍ ROZHRANÍ (NADPISY A CHAT)
# ==============================================================================

st.title("🤖 Kvadr AI Asistent")

# Tvůj specifický design nadpisů
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
        with st.spinner("Odpovídám..."):
            verejne = " ".join(data['zprava'].astype(str).tolist()) if not data.empty else ""
            tajne = " ".join(data['tajne'].astype(str).tolist()) if not data.empty and 'tajne' in data.columns else ""
            
            kontext = f"INSTRUKCE (TAJNÉ): {tajne} | INFO PRO VEŘEJNOST: {verejne}"
            url_ai = f"https://generativelanguage.googleapis.com/v1beta/{funkcni_model}:generateContent?key={API_KEY}"
            
            # PAYLOAD SE ZRUŠENÝM OMEZENÍM
            payload = {
                "contents": [{"parts": [{"text": f"{kontext}\n\nUživatel: {prompt}"}]}],
                "safetySettings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                ]
            }
            
            try:
                res = requests.post(url_ai, json=payload).json()
                if 'candidates' in res:
                    odpoved = res['candidates'][0]['content']['parts'][0]['text']
                    st.markdown(odpoved)
                    st.session_state.messages.append({"role": "assistant", "content": odpoved})
                else:
                    st.warning("AI narazila na filtr i přes uvolněné nastavení.")
                    st.write("Důvod:", res.get('promptFeedback', 'Neznámý'))
            except:
                st.error("Chyba spojení s AI.")
