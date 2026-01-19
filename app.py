import streamlit as st
import pandas as pd
import requests
import base64

# ==============================================================================
# 1. NASTAVENÍ A PERFEKTNÍ VZHLED (CELÉ LOGO + FIX MOBILU)
# ==============================================================================
st.set_page_config(page_title="KVÁDR AI", layout="wide")

JMENO_SOUBORU = "pozadí.png.png"

def inject_styles(image_file):
    try:
        with open(image_file, "rb") as f:
            data = f.read()
        bin_str = base64.b64encode(data).decode()
        
        st.markdown(f"""
        <style>
        /* POZADÍ: 'contain' zajistí, že logo bude vidět CELÉ na jakémkoliv displeji */
        .stApp {{
            background-color: #0e1117;
            background-image: linear-gradient(rgba(0,0,0,0.88), rgba(0,0,0,0.88)), url("data:image/png;base64,{bin_str}");
            background-size: contain; 
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-position: center;
        }}
        
        /* TEXTY: Vždy bílá a čitelná */
        h1, h2, h3, p, span, div, .stMarkdown, label {{
            color: #ffffff !important;
        }}

        /* FIX HLAVIČKY: Logo a text v jedné lince (Flexbox) */
        .header-box {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 25px;
        }}
        .header-box img {{
            width: 50px !important;
            height: auto;
        }}
        .header-box div {{
            display: flex;
            flex-direction: column;
        }}
        .header-box h1 {{
            margin: 0 !important;
            font-size: 1.8rem !important;
            line-height: 1 !important;
        }}
        .header-box p {{
            margin: 0 !important;
            color: #4facfe !important;
            font-weight: bold;
            letter-spacing: 3px;
            font-size: 0.85rem !important;
            text-transform: uppercase;
        }}

        /* Sidebar - klasický tmavý vzhled */
        [data-testid="stSidebar"] {{
            background-color: #111111;
        }}
        </style>
        """, unsafe_allow_html=True)
    except:
        pass

inject_styles(JMENO_SOUBORU)

# ==============================================================================
# 2. DATA (TVÁ FUNKČNÍ LOGIKA)
# ==============================================================================
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
except:
    st.error("⚠️ Nastavte Secrets!")
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
# 3. POSTRANNÍ PANEL (SIDEBAR) - KLASICKÝ
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
# 4. HLAVIČKA (LOGO + NÁZEV V JEDNÉ LINCE)
# ==============================================================================
try:
    with open(JMENO_SOUBORU, "rb") as f:
        logo_data = base64.b64encode(f.read()).decode()
    logo_src = f'data:image/png;base64,{logo_data}'
except:
    logo_src = ""

st.markdown(f"""
    <div class="header-box">
        <img src="{logo_src}">
        <div>
            <h1>KVÁDR</h1>
            <p>AI ASISTENT</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# ==============================================================================
# 5. CHAT A STABILNÍ AI VOLÁNÍ
# ==============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Zadejte zprávu..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # POUŽÍVÁME STABILNÍ v1beta S FALLBACKEM
        url_ai = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
        
        v_info = " ".join(data['zprava'].dropna().astype(str).tolist())
        t_info = " ".join(data['tajne'].dropna().astype(str).tolist()) if 'tajne' in data.columns else ""
        
        payload = {
            "contents": [{"parts": [{"text": f"Instrukce: {t_info}\nInfo: {v_info}\nUživatel: {prompt}"}]}]
        }
        
        try:
            response = requests.post(url_ai, json=payload)
            res = response.json()
            
            # Pokud Flash selže (not found), zkusíme okamžitě gemini-pro (fallback)
            if 'error' in res and 'not found' in res['error']['message'].lower():
                url_fallback = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={API_KEY}"
                response = requests.post(url_fallback, json=payload)
                res = response.json()

            if 'candidates' in res:
                odpoved = res['candidates'][0]['content']['parts'][0]['text']
                st.markdown(odpoved)
                st.session_state.messages.append({"role": "assistant", "content": odpoved})
            else:
                st.error(f"Chyba AI: {res.get('error', {}).get('message', 'Nepodařilo se získat odpověď.')}")
        except Exception as e:
            st.error(f"Chyba spojení: {e}")
