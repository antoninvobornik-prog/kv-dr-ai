import streamlit as st
import pandas as pd
import requests
import base64

# ==============================================================================
# 1. NASTAVENÍ A VZHLED (DARK MODE + LOGO + POZADÍ)
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
        /* 1. TVRDÝ TMAVÝ REŽIM A POZADÍ */
        .stApp {{
            background-color: #0e1117;
            background-image: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)), {bg_image_css};
            background-size: contain; 
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-position: center center;
        }}

        /* 2. HLAVIČKA (LOGO + TEXT) V JEDNÉ LINCE */
        .header-box {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
        }}
        .header-logo {{
            width: 45px !important;
            height: auto;
        }}
        .header-text-group {{
            display: flex;
            flex-direction: column;
        }}
        .header-text-group h1 {{
            margin: 0 !important;
            padding: 0 !important;
            font-size: 1.6rem !important;
            color: #ffffff !important;
        }}
        .header-text-group p {{
            margin: 0 !important;
            color: #4facfe !important;
            font-size: 0.8rem !important;
            font-weight: bold;
            letter-spacing: 2px;
            text-transform: uppercase;
        }}

        /* 3. OPRAVA TEXTŮ (BÍLÁ BARVA) */
        h1, h2, h3, p, div, span, label, .stMarkdown {{
            color: #ffffff !important;
        }}
        
        /* 4. POSTUPNÍ PANEL (SIDEBAR) - KLASICKÝ STYL */
        [data-testid="stSidebar"] {{
            background-color: #111111;
        }}
    </style>
    """, unsafe_allow_html=True)

inject_custom_css(JMENO_SOUBORU)

# ==============================================================================
# 2. DATA A KONFIGURACE AI (VERZE v1)
# ==============================================================================
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
except:
    st.error("Chybí API klíče v Secrets!")
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
# 3. POSTRANNÍ PANEL (SIDEBAR) - JAKO PŘEDTÍM
# ==============================================================================
with st.sidebar:
    st.title("📌 Informace")
    if not data.empty and 'zprava' in data.columns:
        for zpr in data['zprava'].dropna():
            st.info(zpr)
    
    st.divider()
    if st.button("🗑️ Smazat historii"):
        st.session_state.messages = []
        st.rerun()

# ==============================================================================
# 4. HLAVNÍ PLOCHA (LOGO + CHAT)
# ==============================================================================

# Načtení loga pro hlavičku (HTML cesta)
try:
    with open(JMENO_SOUBORU, "rb") as f:
        logo_base64 = base64.b64encode(f.read()).decode()
    logo_src = f"data:image/png;base64,{logo_base64}"
except:
    logo_src = ""

# Vykreslení hlavičky
st.markdown(f"""
    <div class="header-box">
        <img src="{logo_src}" class="header-logo">
        <div class="header-text-group">
            <h1>KVÁDR</h1>
            <p>AI ASISTENT</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# Logika Chatu
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Zadejte dotaz pro KVÁDR..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("KVÁDR přemýšlí..."):
            v_info = " ".join(data['zprava'].dropna().astype(str).tolist())
            t_info = " ".join(data['tajne'].dropna().astype(str).tolist()) if 'tajne' in data.columns else ""
            
            # --- VOLÁNÍ STABILNÍHO v1 MODELU ---
            # Pokud gemini-1.5-flash v v1 stále hlásí chybu, znamená to, 
            # že váš klíč vyžaduje v1beta. Zde je ale vynuceno v1.
            model_name = "gemini-1.5-flash"
            url_ai = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent?key={API_KEY}"
            
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": f"Instrukce: {t_info}\nKontext: {v_info}\nUživatel: {prompt}"}]
                    }
                ]
            }
            
            try:
                response = requests.post(url_ai, json=payload)
                res = response.json()
                
                if 'candidates' in res and len(res['candidates']) > 0:
                    odpoved = res['candidates'][0]['content']['parts'][0]['text']
                    st.markdown(odpoved)
                    st.session_state.messages.append({"role": "assistant", "content": odpoved})
                else:
                    # Pokud v1 nezná model, zkusíme automaticky v1beta jako záchranu
                    url_fallback = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
                    res_fallback = requests.post(url_fallback, json=payload).json()
                    
                    if 'candidates' in res_fallback:
                        odpoved = res_fallback['candidates'][0]['content']['parts'][0]['text']
                        st.markdown(odpoved)
                        st.session_state.messages.append({"role": "assistant", "content": odpoved})
                    else:
                        st.error(f"Chyba AI: {res.get('error', {}).get('message', 'Model není dostupný.')}")
            except Exception as e:
                st.error(f"Chyba spojení: {e}")
