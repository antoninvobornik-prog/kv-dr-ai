import streamlit as st
import pandas as pd
import requests
import time

# ==============================================================================
# 1. DESIGN A VZHLED (TMAVÝ REŽIM)
# ==============================================================================
st.set_page_config(page_title="Kvadr AI Asistent", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
    .stInfo { background-color: #1f2937; color: #e5e7eb; border: 1px solid #3b82f6; }
    .stWarning { background-color: #2d2d00; color: #fef08a; border: 1px solid #ca8a04; }
    h1, h2, h3 { color: #ffffff !important; }
    </style>
    """, unsafe_allow_html=True)

# Načtení klíčů ze Secrets
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
except:
    st.error("Chybí klíče v Secrets (Nastavení Streamlit Cloudu)!")
    st.stop()

# ==============================================================================
# 2. FUNKCE PRO DATA A CHYTRÁ DETEKCE MODELU
# ==============================================================================

def nacti_data():
    """Načte data z Google Tabulky a vyčistí prázdné řádky."""
    try:
        sheet_id = GSHEET_URL.split("/d/")[1].split("/")[0]
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=List1"
        return pd.read_csv(url)
    except:
        return pd.DataFrame(columns=['zprava', 'tajne'])

@st.cache_resource
def ziskej_funkcni_model():
    """Najde model Gemini, který skutečně funguje pro tvůj klíč."""
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
# 3. LEVÝ PANEL (SIDEBAR)
# ==============================================================================
with st.sidebar:
    st.title("📌 Informace")
    
    if not data.empty and 'zprava' in data.columns:
        for zpr in data['zprava'].dropna():
            st.info(zpr)
    
    st.divider()
    
    if st.button("🗑️ Smazat historii chatu"):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    
    heslo_input = st.text_input("Správa (heslo)", type="password")
    if heslo_input == "mojeheslo":
        st.success(f"Aktivní model: {MODEL_NAME}")
        if 'tajne' in data.columns:
            for t in data['tajne'].dropna():
                st.warning(t)

# ==============================================================================
# 4. HLAVNÍ CHAT
# ==============================================================================
st.title("🤖 Kvádr AI Asistent")

st.markdown("<p style='color: white; font-weight: bold; font-size: 1.1rem; margin-bottom: 5px;'>Tvůj inteligentní průvodce projektem Kvadr, který ti pomůže v reálném čase odpovědět na otázky!</p>", unsafe_allow_html=True)
st.markdown("<p style='color: gray; font-style: italic; font-size: 0.9rem; margin-top: 0px;'>POZOR MOHU DĚLAT CHYBY A NĚKTERÉ INFORMACE NEMUSÍM ZNÁT !</p>", unsafe_allow_html=True)

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
        with st.spinner("Hledám odpověď..."):
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
            
            # --- POSÍLENÉ OPAKOVÁNÍ PŘI VYTÍŽENÍ ---
            uspech = False
            for pokus in range(5):
                try:
                    response = requests.post(url_ai, json=payload)
                    res = response.json()
                    
                    if 'candidates' in res:
                        odpoved = res['candidates'][0]['content']['parts'][0]['text']
                        st.markdown(odpoved)
                        st.session_state.messages.append({"role": "assistant", "content": odpoved})
                        uspech = True
                        break
                    elif 'error' in res and res['error'].get('code') in [429, 503]:
                        # Počkáme a zkusíme to znovu
                        time.sleep(2 + pokus * 2)
                        continue
                    else:
                        st.error("AI narazila na technický problém.")
                        with st.expander("Detail chyby"):
                            st.json(res)
                        break
                except Exception as e:
                    st.error(f"Spojení selhalo: {e}")
                    break
            
            if not uspech and 'res' in locals() and 'error' in res and res['error'].get('code') in [429, 503]:
                st.warning("⚠️ Google servery jsou teď přetížené. Počkej prosím minutu a zkus to znovu.")
