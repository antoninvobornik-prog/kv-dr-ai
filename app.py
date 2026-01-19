import streamlit as st
import pandas as pd
import requests
import time
import base64

# ==============================================================================
# 1. KONFIGURACE A OPRAVA VZHLEDU (LOGO + DARK MODE)
# ==============================================================================
st.set_page_config(page_title="KVÁDR AI", layout="wide")

JMENO_SOUBORU = "pozadí.png.png"

def inject_custom_css(image_file):
    try:
        with open(image_file, "rb") as f:
            data = f.read()
        bin_str = base64.b64encode(data).decode()
        bg_image_css = f'url("data:image/png;base64,{bin_str}")'
    except FileNotFoundError:
        bg_image_css = "none"

    st.markdown(f"""
    <style>
        /* Celkové pozadí - contain pro viditelnost celého loga */
        .stApp {{
            background-color: #0e1117;
            background-image: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)), {bg_image_css};
            background-size: contain; 
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-position: center center;
        }}

        /* Vynucení tmavého režimu pro texty */
        h1, h2, h3, p, div, span, label, .stMarkdown {{
            color: #ffffff !important;
        }}

        /* Úprava hlavičky - aby se logo a text na mobilu nepletly */
        [data-testid="stHorizontalBlock"] {{
            align-items: center;
        }}
        
        /* Omezení velikosti loga v hlavičce */
        [data-testid="stImage"] img {{
            max-width: 60px !important;
            height: auto !important;
        }}

        .subtitle {{
            color: #4facfe !important;
            font-size: 1rem;
            font-weight: bold;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-top: -15px;
        }}
        
        /* Oprava pro mobilní zobrazení textu */
        @media (max-width: 640px) {{
            h1 {{ font-size: 1.8rem !important; }}
            .subtitle {{ font-size: 0.8rem !important; }}
        }}
    </style>
    """, unsafe_allow_html=True)

inject_custom_css(JMENO_SOUBORU)

# ==============================================================================
# 2. DATA A API (OPRAVA CHYBY "AI NEODPOVĚDĚLA")
# ==============================================================================
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
except:
    st.error("⚠️ Nastavte GOOGLE_API_KEY a GSHEET_URL v Secrets!")
    st.stop()

def nacti_data():
    try:
        sheet_id = GSHEET_URL.split("/d/")[1].split("/")[0]
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=List1"
        return pd.read_csv(url)
    except:
        return pd.DataFrame(columns=['zprava', 'tajne'])

data = nacti_data()
MODEL_NAME = "gemini-1.5-flash" # Používáme stabilní název

# ==============================================================================
# 3. SIDEBAR
# ==============================================================================
with st.sidebar:
    st.title("📌 INFO")
    if not data.empty and 'zprava' in data.columns:
        for zpr in data['zprava'].dropna():
            st.info(zpr)
    if st.button("🗑️ Vymazat historii"):
        st.session_state.messages = []
        st.rerun()

# ==============================================================================
# 4. HLAVNÍ CHAT ROZHRANÍ
# ==============================================================================

# Sloupce: logo vlevo (velmi úzký sloupec), text vpravo
col_logo, col_text = st.columns([0.1, 0.9])

with col_logo:
    try:
        st.image(JMENO_SOUBORU)
    except:
        st.write("🤖")

with col_text:
    st.title("KVÁDR")
    st.markdown('<p class="subtitle">AI ASISTENT</p>', unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Napište zprávu..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("KVÁDR přemýšlí..."):
            v_info = " ".join(data['zprava'].dropna().astype(str).tolist())
            t_info = " ".join(data['tajne'].dropna().astype(str).tolist()) if 'tajne' in data.columns else ""
            
            # OPRAVENÝ PAYLOAD PRO GOOGLE API
            url_ai = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
            
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": f"Instrukce: {t_info}\nData: {v_info}\nDotaz: {prompt}"}]
                    }
                ]
            }
            
            try:
                response = requests.post(url_ai, json=payload)
                res = response.json()
                
                # Kontrola, zda API vrátilo text
                if 'candidates' in res and len(res['candidates']) > 0:
                    odpoved = res['candidates'][0]['content']['parts'][0]['text']
                    st.markdown(odpoved)
                    st.session_state.messages.append({"role": "assistant", "content": odpoved})
                else:
                    # Detailnější výpis chyby pro ladění
                    st.error(f"Systémová chyba: {res.get('error', {}).get('message', 'AI neodpověděla.')}")
            except Exception as e:
                st.error(f"Chyba spojení: {e}")
