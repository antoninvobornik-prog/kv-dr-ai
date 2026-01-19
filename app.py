import streamlit as st
import pandas as pd
import requests
import time
import base64

# ==============================================================================
# 1. KONFIGURACE A VYNUCENÍ VIDITELNOSTI SIDEBARU
# ==============================================================================
# initial_sidebar_state="expanded" zajistí, že panel bude při startu vidět
st.set_page_config(
    page_title="KVÁDR AI", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

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
        /* Pozadí chatu - celé logo bez ořezu */
        .stApp {{
            background-color: #0e1117;
            background-image: linear-gradient(rgba(0, 0, 0, 0.88), rgba(0, 0, 0, 0.88)), {bg_image_css};
            background-size: contain; 
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-position: center center;
        }}

        /* Vynucení Dark Mode textů */
        h1, h2, h3, p, div, span, label, .stMarkdown, li {{
            color: #ffffff !important;
        }}

        /* FIX SIDEBARU: Aby byl vždy čitelný a viditelný */
        [data-testid="stSidebar"] {{
            background-color: #111111 !important;
            border-right: 1px solid #333 !important;
            min-width: 250px !important;
        }}

        /* FIX LOGA A TEXTU V JEDNÉ ŘADĚ (MOBIL I PC) */
        .header-container {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 20px;
        }}
        
        .header-logo {{
            width: 50px !important;
            height: auto;
        }}

        .header-text {{
            display: flex;
            flex-direction: column;
        }}

        .header-text h1 {{
            margin: 0 !important;
            padding: 0 !important;
            font-size: 1.8rem !important;
            line-height: 1 !important;
        }}

        .subtitle {{
            color: #4facfe !important;
            font-size: 0.8rem !important;
            font-weight: bold;
            letter-spacing: 3px;
            text-transform: uppercase;
            margin: 0 !important;
        }}

        /* Skrytí Streamlit menu pro čistší vzhled */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

inject_custom_css(JMENO_SOUBORU)

# ==============================================================================
# 2. DATA A OPRAVA AI (VERZE v1)
# ==============================================================================
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
except:
    st.error("⚠️ CHYBA: Nastavte API klíče v Secrets!")
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
# 3. SIDEBAR (POSTRANNÍ PANEL)
# ==============================================================================
with st.sidebar:
    st.image(JMENO_SOUBORU, width=100)
    st.title("SYSTÉM KVÁDR")
    st.write("---")
    
    st.subheader("📢 Aktuální info")
    if not data.empty and 'zprava' in data.columns:
        for zpr in data['zprava'].dropna():
            st.info(zpr)
    
    st.write("---")
    if st.button("🗑️ Resetovat chat"):
        st.session_state.messages = []
        st.rerun()

# ==============================================================================
# 4. HLAVNÍ ROZHRANÍ (LOGO + NÁZEV V JEDNÉ ŘADĚ)
# ==============================================================================

# Použití HTML pro naprostou kontrolu nad řazením loga a textu
try:
    with open(JMENO_SOUBORU, "rb") as f:
        logo_data = f.read()
    logo_base64 = base64.b64encode(logo_data).decode()
    logo_html = f'data:image/png;base64,{logo_base64}'
except:
    logo_html = ""

st.markdown(f"""
    <div class="header-container">
        <img src="{logo_html}" class="header-logo">
        <div class="header-text">
            <h1>KVÁDR</h1>
            <p class="subtitle">AI ASISTENT</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Zadejte dotaz..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("KVÁDR odpovídá..."):
            v_info = " ".join(data['zprava'].dropna().astype(str).tolist())
            t_info = " ".join(data['tajne'].dropna().astype(str).tolist()) if 'tajne' in data.columns else ""
            
            # OPRAVA: Zkoušíme stabilní cestu pro v1
            # Pokud gemini-1.5-flash selže, kód automaticky zkusí gemini-pro
            model_to_use = "gemini-1.5-flash"
            url_ai = f"https://generativelanguage.googleapis.com/v1/models/{model_to_use}:generateContent?key={API_KEY}"
            
            payload = {
                "contents": [{"parts": [{"text": f"Instrukce: {t_info}\nData: {v_info}\nUživatel: {prompt}"}]}]
            }
            
            try:
                response = requests.post(url_ai, json=payload)
                res = response.json()
                
                if 'candidates' in res:
                    odpoved = res['candidates'][0]['content']['parts'][0]['text']
                    st.markdown(odpoved)
                    st.session_state.messages.append({"role": "assistant", "content": odpoved})
                else:
                    # Pokud flash neexistuje v v1, zkusíme gemini-pro (starší stabilní verze)
                    url_ai_fallback = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={API_KEY}"
                    response = requests.post(url_ai_fallback, json=payload)
                    res = response.json()
                    if 'candidates' in res:
                        odpoved = res['candidates'][0]['content']['parts'][0]['text']
                        st.markdown(odpoved)
                        st.session_state.messages.append({"role": "assistant", "content": odpoved})
                    else:
                        st.error(f"Chyba: {res.get('error', {}).get('message', 'Model není dostupný.')}")
            except Exception as e:
                st.error(f"Chyba spojení: {e}")
