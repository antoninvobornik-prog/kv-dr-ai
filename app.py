import streamlit as st
import pandas as pd
import requests
import base64

# ==============================================================================
# 1. DESIGN: LOGO VEDLE TEXTU A POZADÍ (CONTAIN)
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
        /* POZADÍ - viditelné CELÉ logo */
        .stApp {{
            background-color: #0e1117;
            background-image: linear-gradient(rgba(0,0,0,0.88), rgba(0,0,0,0.88)), url("data:image/png;base64,{bin_str}");
            background-size: contain;
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-position: center;
        }}
        
        /* TEXTY - bílá barva */
        h1, h2, h3, p, span, div, .stMarkdown, label {{
            color: #ffffff !important;
        }}

        /* HLAVIČKA - logo a text VŽDY v jedné řadě (i na mobilu) */
        .header-container {{
            display: flex;
            flex-direction: row;
            align-items: center;
            gap: 12px;
            padding-bottom: 20px;
        }}
        .header-container img {{
            width: 45px !important;
            height: auto;
        }}
        .header-container .text-group {{
            display: flex;
            flex-direction: column;
        }}
        .header-container h1 {{
            margin: 0 !important;
            font-size: 1.8rem !important;
            line-height: 1 !important;
        }}
        .header-container p {{
            margin: 0 !important;
            color: #4facfe !important;
            font-weight: bold;
            letter-spacing: 2px;
            font-size: 0.8rem !important;
            text-transform: uppercase;
        }}

        /* Původní styl sidebar */
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
    st.error("Nastavte API klíče v Secrets!")
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
# 4. HLAVNÍ HLAVIČKA (LOGO VLEVO, TEXT VPRAVO)
# ==============================================================================
try:
    with open(JMENO_SOUBORU, "rb") as f:
        logo_base = base64.b64encode(f.read()).decode()
    logo_src = f'data:image/png;base64,{logo_base}'
except:
    logo_src = ""

st.markdown(f"""
    <div class="header-container">
        <img src="{logo_src}">
        <div class="text-group">
            <h1>KVÁDR</h1>
            <p>AI ASISTENT</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# ==============================================================================
# 5. CHAT A ROBUSTNÍ AI VOLÁNÍ (ABY TO UŽ NIKDY NEHODILO CHYBU)
# ==============================================================================
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
        with st.spinner("KVÁDR přemýšlí..."):
            v_info = " ".join(data['zprava'].dropna().astype(str).tolist())
            t_info = " ".join(data['tajne'].dropna().astype(str).tolist()) if 'tajne' in data.columns else ""
            payload = {"contents": [{"parts": [{"text": f"Instrukce: {t_info}\nData: {v_info}\nDotaz: {prompt}"}]}]}
            
            # SEZNAM POKUSŮ - kód zkusí tyto 3 adresy jednu po druhé
            urls = [
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}",
                f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}",
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={API_KEY}"
            ]
            
            odpoved_nalezena = False
            for url in urls:
                try:
                    response = requests.post(url, json=payload, timeout=10)
                    res = response.json()
                    if 'candidates' in res:
                        odpoved = res['candidates'][0]['content']['parts'][0]['text']
                        st.markdown(odpoved)
                        st.session_state.messages.append({"role": "assistant", "content": odpoved})
                        odpoved_nalezena = True
                        break # Povedlo se, končíme cyklus
                except:
                    continue # Zkusíme další URL v seznamu
            
            if not odpoved_nalezena:
                st.error("Systémová chyba: Žádný z AI modelů neodpovídá. Zkontrolujte prosím funkčnost vašeho Google API klíče.")
