import streamlit as st
import pandas as pd
import requests
import time
import base64

# ==============================================================================
# 1. KONFIGURACE A OPRAVA POZADÍ (ABY BYLO VIDĚT CELÉ LOGO)
# ==============================================================================
st.set_page_config(page_title="KVÁDR AI", layout="wide")

# Název souboru (přesně podle vašeho nahrání)
JMENO_SOUBORU = "pozadí.png.png"

def inject_custom_css(image_file):
    """
    Načte obrázek a nastaví CSS tak, aby se logo vždy přizpůsobilo
    obrazovce a nikdy se neořízlo (contain).
    """
    try:
        with open(image_file, "rb") as f:
            data = f.read()
        bin_str = base64.b64encode(data).decode()
        bg_image_css = f'url("data:image/png;base64,{bin_str}")'
    except FileNotFoundError:
        bg_image_css = "none"

    # --- ZMĚNA CSS PRO PERFEKTNÍ ZOBRAZENÍ LOGA ---
    st.markdown(f"""
    <style>
        /* 1. Hlavní pozadí aplikace */
        .stApp {{
            background-color: #0e1117; /* Tmavá podkladová barva pro okraje */
            
            /* Dvě vrstvy: 1. Tmavý filtr (aby byl text čitelný), 2. Samotné logo */
            background-image: 
                linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)), 
                {bg_image_css};
            
            /* KLÍČOVÁ ZMĚNA: 'contain' zajistí, že se obrázek zmenší tak, aby byl celý vidět */
            background-size: contain; 
            
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-position: center center;
        }}

        /* 2. Vynucení bílého textu pro maximální kontrast */
        h1, h2, h3, p, div, span, label, .stMarkdown, li {{
            color: #e0e0e0 !important;
        }}

        /* 3. Boční panel (Sidebar) - poloprůhledný, aby nerušil */
        [data-testid="stSidebar"] {{
            background-color: rgba(22, 27, 34, 0.95);
            border-right: 1px solid #30363d;
        }}

        /* 4. Vstupní pole a tlačítka */
        .stTextInput input, .stChatInput textarea {{
            background-color: #0d1117 !important;
            color: #ffffff !important;
            border: 1px solid #30363d !important;
        }}
        
        button {{
            background-color: #238636 !important;
            color: white !important;
            border: none !important;
            border-radius: 5px;
        }}

        /* 5. Styl pro podnadpis */
        .subtitle {{
            color: #4facfe !important;
            font-size: 1.2rem;
            font-weight: bold;
            letter-spacing: 4px;
            text-transform: uppercase;
            margin-top: -15px;
            text-shadow: 0px 0px 10px rgba(79, 172, 254, 0.6);
        }}
    </style>
    """, unsafe_allow_html=True)

# Spuštění stylů
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

# Použijeme rychlý model
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
# 4. HLAVNÍ ČÁST (LOGO V HLAVIČCE A CHAT)
# ==============================================================================

# Logo v hlavičce (malé) + Nadpis
col_logo, col_text = st.columns([0.2, 0.8])

with col_logo:
    try:
        st.image(JMENO_SOUBORU, use_container_width=True)
    except:
        st.header("🤖")

with col_text:
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
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
    # 1. Uložit uživatele
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Zpracování odpovědi
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        with st.spinner("Analyzuji data..."):
            # Příprava kontextu
            verejne = " ".join(data['zprava'].dropna().astype(str).tolist())
            tajne = " ".join(data['tajne'].dropna().astype(str).tolist()) if 'tajne' in data.columns else ""
            
            # Volání Google AI
            url_ai = f"https://generativelanguage.googleapis.com/v1beta/{MODEL_NAME}:generateContent?key={API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": f"Jsi KVÁDR AI, asistent v projektu. \nINTERNÍ DATA: {tajne}\nVEŘEJNÉ INFO: {verejne}\n\nUŽIVATEL: {prompt}"}]}]
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
                
    # 3. Uložení odpovědi
    if full_response:
        st.session_state.messages.append({"role": "assistant", "content": full_response})
