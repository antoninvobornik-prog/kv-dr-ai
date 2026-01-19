import streamlit as st
import pandas as pd
import requests
import time
import base64

# ==============================================================================
# 1. KONFIGURACE A VYNUCENÍ TMAVÉHO REŽIMU
# ==============================================================================
st.set_page_config(page_title="KVÁDR AI", layout="wide")

# Název souboru (přesně podle vašeho nahrání)
JMENO_SOUBORU = "pozadí.png.png"

def inject_custom_css(image_file):
    """
    Funkce načte obrázek pro pozadí a vloží CSS pro tvrdý Dark Mode.
    """
    try:
        with open(image_file, "rb") as f:
            data = f.read()
        bin_str = base64.b64encode(data).decode()
        bg_image_css = f'url("data:image/png;base64,{bin_str}")'
    except FileNotFoundError:
        bg_image_css = "none"

    # CSS STYLY PRO TMAVÝ REŽIM A METALICKÝ VZHLED
    st.markdown(f"""
    <style>
        /* 1. Hlavní pozadí aplikace - tmavé s nádechem obrázku */
        .stApp {{
            background-color: #0e1117;
            background-image: linear-gradient(rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0.8)), {bg_image_css};
            background-size: cover;
            background-attachment: fixed;
            background-position: center;
        }}

        /* 2. Vynucení bílého textu všude */
        h1, h2, h3, p, div, span, label, .stMarkdown {{
            color: #e0e0e0 !important;
        }}

        /* 3. Boční panel (Sidebar) - tmavší šedá */
        [data-testid="stSidebar"] {{
            background-color: #161b22;
            border-right: 1px solid #30363d;
        }}

        /* 4. Vstupní pole (Chat input, text input) */
        .stTextInput input, .stChatInput textarea {{
            background-color: #21262d !important;
            color: #ffffff !important;
            border: 1px solid #30363d !important;
        }}
        
        /* 5. Tlačítka */
        button {{
            background-color: #238636 !important;
            color: white !important;
            border: none !important;
        }}

        /* 6. Styl pro podnadpis AI ASISTENT */
        .subtitle {{
            color: #58a6ff !important; /* Světle modrá jako záře v logu */
            font-size: 1.2rem;
            font-weight: bold;
            letter-spacing: 4px;
            text-transform: uppercase;
            margin-top: -15px;
            text-shadow: 0px 0px 10px rgba(88, 166, 255, 0.5);
        }}
    </style>
    """, unsafe_allow_html=True)

# Aktivace stylů
inject_custom_css(JMENO_SOUBORU)

# ==============================================================================
# 2. NAČTENÍ KLÍČŮ A DAT
# ==============================================================================
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
except:
    st.error("⚠️ CHYBA: Nejsou nastaveny API klíče v Secrets!")
    st.stop()

def nacti_data():
    try:
        sheet_id = GSHEET_URL.split("/d/")[1].split("/")[0]
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=List1"
        return pd.read_csv(url)
    except:
        return pd.DataFrame(columns=['zprava', 'tajne'])

# Konstantní model (Gemini Flash je rychlý a levný)
MODEL_NAME = "models/gemini-1.5-flash"
data = nacti_data()

# ==============================================================================
# 3. SIDEBAR (INFO PANEL)
# ==============================================================================
with st.sidebar:
    st.header("⚙️ OVLÁDÁNÍ")
    
    st.subheader("📢 Veřejné info")
    if not data.empty and 'zprava' in data.columns:
        for zpr in data['zprava'].dropna():
            st.info(zpr)
    
    st.divider()
    if st.button("🗑️ Vymazat paměť chatu"):
        st.session_state.messages = []
        st.rerun()

# ==============================================================================
# 4. HLAVNÍ ČÁST (LOGO A CHAT)
# ==============================================================================

# Zde je úprava pro zobrazení CELÉHO loga
# Poměr sloupců 0.25 (logo) : 0.75 (text) dává logu dost místa
col_logo, col_text = st.columns([0.25, 0.75])

with col_logo:
    try:
        # width=160 zajistí, že logo bude dostatečně velké a čitelné
        st.image(JMENO_SOUBORU, width=160)
    except:
        st.header("🤖")

with col_text:
    # Zarovnání textu vertikálně k logu
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    st.title("KVÁDR")
    st.markdown('<p class="subtitle">AI ASISTENT</p>', unsafe_allow_html=True)

# --- CHAT LOGIKA ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Vykreslení historie
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Vstup uživatele
if prompt := st.chat_input("Zadejte instrukci pro KVÁDR systém..."):
    # 1. Uložit a zobrazit dotaz uživatele
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Zpracování odpovědi
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        with st.spinner("Analyzuji data..."):
            # Příprava kontextu z tabulky
            verejne = " ".join(data['zprava'].dropna().astype(str).tolist())
            tajne = " ".join(data['tajne'].dropna().astype(str).tolist()) if 'tajne' in data.columns else ""
            
            # Odeslání na Google Gemini API
            url_ai = f"https://generativelanguage.googleapis.com/v1beta/{MODEL_NAME}:generateContent?key={API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": f"Jsi KVÁDR AI, inteligentní asistent. \nINTERNÍ DATA: {tajne}\nVEŘEJNÉ INFO: {verejne}\n\nUŽIVATEL: {prompt}"}]}]
            }
            
            try:
                response = requests.post(url_ai, json=payload)
                res = response.json()
                
                if 'candidates' in res:
                    full_response = res['candidates'][0]['content']['parts'][0]['text']
                    message_placeholder.markdown(full_response)
                else:
                    message_placeholder.error("Systémová chyba: AI neodpověděla.")
            except Exception as e:
                message_placeholder.error(f"Chyba spojení: {str(e)}")
                
    # 3. Uložení odpovědi do historie
    if full_response:
        st.session_state.messages.append({"role": "assistant", "content": full_response})
