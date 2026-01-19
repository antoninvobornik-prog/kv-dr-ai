import streamlit as st
import pandas as pd
import requests
import time
import base64

# ==============================================================================
# 1. NASTAVENÍ STRÁNKY A POZADÍ
# ==============================================================================
st.set_page_config(page_title="Kvadr AI Asistent", layout="wide")

def set_background(image_file):
    """
    Načte obrázek a nastaví ho jako pozadí aplikace.
    """
    try:
        with open(image_file, "rb") as f:
            data = f.read()
        bin_str = base64.b64encode(data).decode()
        
        page_bg_img = f"""
        <style>
        .stApp {{
            background-image: linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.7)), url("data:image/png;base64,{bin_str}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        /* Bílá barva pro veškerý text kvůli čitelnosti */
        h1, h2, h3, p, div, span, .stMarkdown {{
            color: #ffffff !important;
            text-shadow: 1px 1px 3px rgba(0,0,0,0.8);
        }}
        [data-testid="stSidebar"] {{
            background-color: rgba(22, 27, 34, 0.95);
        }}
        </style>
        """
        st.markdown(page_bg_img, unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"Soubor '{image_file}' nebyl nalezen! Zkontroluj název v GitHubu.")

# --- TADY JE TA OPRAVA ---
# Používáme přesný název z tvého obrázku
JMENO_SOUBORU = "pozadí.png.png"
set_background(JMENO_SOUBORU)

# Načtení klíčů ze Secrets
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
except:
    st.error("Chybí klíče v Secrets (Nastavení Streamlit Cloudu)!")
    st.stop()

# ==============================================================================
# 2. FUNKCE PRO DATA A MODEL
# ==============================================================================

def nacti_data():
    try:
        sheet_id = GSHEET_URL.split("/d/")[1].split("/")[0]
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=List1"
        return pd.read_csv(url)
    except:
        return pd.DataFrame(columns=['zprava', 'tajne'])

@st.cache_resource
def ziskej_funkcni_model():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    try:
        res = requests.get(url).json()
        if "models" in res:
            modely = [m["name"] for m in res["models"] 
                      if "gemini" in m["name"] and "generateContent" in m["supportedGenerationMethods"]]
            for m in modely:
                if "1.5-flash" in m: return m
            return modely[0] if modely else "models/gemini-1.5-flash"
    except: pass
    return "models/gemini-1.5-flash"

data = nacti_data()
MODEL_NAME = ziskej_funkcni_model()

# ==============================================================================
# 3. SIDEBAR A HLAVNÍ CHAT
# ==============================================================================
with st.sidebar:
    st.title("📌 Informace")
    if not data.empty and 'zprava' in data.columns:
        for zpr in data['zprava'].dropna():
            st.info(zpr)
    
    if st.button("🗑️ Smazat historii"):
        st.session_state.messages = []
        st.rerun()

# Hlavička s logem
col1, col2 = st.columns([0.15, 0.85])
with col1:
    # Tady taky opravený název
    st.image(JMENO_SOUBORU, width=80) 
with col2:
    st.title("Kvadr AI Asistent")

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
        with st.spinner("Přemýšlím..."):
            verejne = " ".join(data['zprava'].dropna().astype(str).tolist())
            tajne = " ".join(data['tajne'].dropna().astype(str).tolist()) if 'tajne' in data.columns else ""
            
            url_ai = f"https://generativelanguage.googleapis.com/v1beta/{MODEL_NAME}:generateContent?key={API_KEY}"
            
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
                response = requests.post(url_ai, json=payload)
                res = response.json()
                if 'candidates' in res:
                    odpoved = res['candidates'][0]['content']['parts'][0]['text']
                    st.markdown(odpoved)
                    st.session_state.messages.append({"role": "assistant", "content": odpoved})
                else:
                    st.error("AI neodpovídá, zkontroluj API klíč.")
            except Exception as e:
                st.error(f"Chyba: {e}")
