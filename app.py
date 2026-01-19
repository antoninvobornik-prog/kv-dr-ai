import streamlit as st
import pandas as pd
import requests
import time
import base64

# ==============================================================================
# 1. KONFIGURACE, DARK MODE A RESPONZIVNÍ LOGO
# ==============================================================================
st.set_page_config(page_title="KVÁDR AI", layout="wide")

# Přesný název tvého souboru
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
        /* Pozadí celé aplikace - viditelné celé logo */
        .stApp {{
            background-color: #0e1117;
            background-image: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)), {bg_image_css};
            background-size: contain; 
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-position: center center;
        }}

        /* Vynucení tmavého režimu pro všechny texty */
        h1, h2, h3, p, div, span, label, .stMarkdown {{
            color: #ffffff !important;
        }}

        /* FIX LOGA V HLAVIČCE: Aby na mobilu nebylo obří a text byl HNED VEDLE */
        [data-testid="stHorizontalBlock"] {{
            align-items: center !important;
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
        }}
        
        [data-testid="stColumn"] {{
            min-width: 0px !important;
            flex: unset !important;
        }}

        /* Logo nastaveno na velmi malé, aby zbylo místo pro text i na mobilu */
        [data-testid="stImage"] img {{
            max-width: 45px !important;
            height: auto !important;
        }}

        /* Styling nápisů */
        h1 {{
            margin: 0 !important;
            padding: 0 0 0 10px !important;
            font-size: 1.6rem !important;
            white-space: nowrap;
        }}

        .subtitle {{
            color: #4facfe !important;
            font-size: 0.85rem;
            font-weight: bold;
            letter-spacing: 2px;
            text-transform: uppercase;
            padding-left: 12px;
            margin-top: -5px;
            white-space: nowrap;
        }}

        /* Styl chatu */
        .stChatMessage {{
            background-color: rgba(255, 255, 255, 0.05) !important;
            border-radius: 10px !important;
        }}
    </style>
    """, unsafe_allow_html=True)

inject_custom_css(JMENO_SOUBORU)

# ==============================================================================
# 2. DATA A STABILNÍ API (VERZE v1)
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

# ==============================================================================
# 3. HLAVNÍ ROZHRANÍ (NADPISY A CHAT)
# ==============================================================================

# Logo a název natěsno vedle sebe
c1, c2 = st.columns([0.1, 0.9])
with c1:
    try:
        st.image(JMENO_SOUBORU)
    except:
        st.write("🤖")
with c2:
    st.title("KVÁDR")
    st.markdown('<p class="subtitle">AI ASISTENT</p>', unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Zobrazení historie
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Vstup pro uživatele
if prompt := st.chat_input("Napište zprávu systému KVÁDR..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("KVÁDR analyzuje..."):
            v_info = " ".join(data['zprava'].dropna().astype(str).tolist())
            t_info = " ".join(data['tajne'].dropna().astype(str).tolist()) if 'tajne' in data.columns else ""
            
            # --- STABILNÍ URL VERZE v1 ---
            url_ai = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"
            
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": f"Instrukce: {t_info}\nData z projektu: {v_info}\nOtázka: {prompt}"}]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "topP": 0.95,
                    "maxOutputTokens": 1024
                }
            }
            
            try:
                response = requests.post(url_ai, json=payload)
                res = response.json()
                
                if 'candidates' in res and len(res['candidates']) > 0:
                    odpoved = res['candidates'][0]['content']['parts'][0]['text']
                    st.markdown(odpoved)
                    st.session_state.messages.append({"role": "assistant", "content": odpoved})
                else:
                    error_info = res.get('error', {}).get('message', 'Neznámá chyba stability API.')
                    st.error(f"AI Chyba (v1): {error_info}")
            except Exception as e:
                st.error(f"Chyba spojení se serverem: {e}")
