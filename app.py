import streamlit as st
import pandas as pd
import requests
import time

# ==============================================================================
# 1. ZÁKLADNÍ NASTAVENÍ A VZHLED (TMAVÝ REŽIM)
# ==============================================================================
st.set_page_config(page_title="Kvadr AI Asistent", layout="wide")

# Vynucení tmavého režimu a úprava barev pomocí CSS
st.markdown("""
    <style>
    /* Hlavní pozadí aplikace */
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    /* Sidebar (levý panel) */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    /* Styl pro modré informační bubliny */
    .stInfo {
        background-color: #1f2937;
        color: #e5e7eb;
        border: 1px solid #3b82f6;
    }
    /* Styl pro tajné žluté bubliny */
    .stWarning {
        background-color: #2d2d00;
        color: #fef08a;
        border: 1px solid #ca8a04;
    }
    /* Úprava nadpisů na čistě bílou */
    h1, h2, h3 {
        color: #ffffff !important;
    }
    /* Odstranění horní mezery pro lepší design */
    .block-container {
        padding-top: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

# Načtení klíčů ze Secrets
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
except:
    st.error("Chybí klíče v Secrets (nastavení Streamlitu)!")
    st.stop()

# ==============================================================================
# 2. FUNKCE PRO PRÁCI S DATY A AI
# ==============================================================================

def nacti_data():
    """Načte data z Google tabulky (sloupce 'zprava' a 'tajne')."""
    try:
        sheet_id = GSHEET_URL.split("/d/")[1].split("/")[0]
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=List1"
        df = pd.read_csv(url)
        return df
    except:
        return pd.DataFrame(columns=['zprava', 'tajne'])

@st.cache_resource
def najdi_funkcni_model():
    """Diagnostika, která najde správný název modelu pro tvůj API klíč."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    try:
        res = requests.get(url).json()
        for m in res.get("models", []):
            if "generateContent" in m["supportedGenerationMethods"] and "gemini" in m["name"]:
                return m["name"]
        return "models/gemini-1.5-flash"
    except:
        return "models/gemini-1.5-flash"

# Inicializace dat a modelu
data = nacti_data()
funkcni_model = najdi_funkcni_model()

# ==============================================================================
# 3. LEVÝ PANEL (SIDEBAR) - INFO A SPRÁVA
# ==============================================================================
with st.sidebar:
    st.title("📌 Informace")
    
    # VEŘEJNÉ INFORMACE (Vidí všichni uživatelé)
    st.subheader("O projektu:")
    if not data.empty and 'zprava' in data.columns:
        for zpr in data['zprava'].dropna():
            st.info(zpr)
    else:
        st.caption("Tabulka 'zprava' je prázdná.")
    
    st.divider()
    
    # SEKCE PRO SPRÁVCE (Chráněno heslem)
    heslo_input = st.text_input("Správa (zadej heslo)", type="password")
    
    if heslo_input == "mojeheslo":
        st.success("Režim správce aktivní")
        st.subheader("🕵️ Tajné instrukce pro AI:")
        if 'tajne' in data.columns:
            for t in data['tajne'].dropna():
                st.warning(t)
        else:
            st.caption("Sloupec 'tajne' nebyl nalezen.")
    else:
        st.caption("Zadej heslo pro zobrazení tajných instrukcí.")

# ==============================================================================
# 4. HLAVNÍ CHAT - ROZHRANÍ A LOGIKA
# ==============================================================================

# HLAVNÍ NADPIS
st.title("🤖 Kvadr AI Asistent")

# PRVNÍ PODNADPIS (Bílý a zvýrazněný)
st.markdown("<p style='color: white; font-weight: bold; font-size: 1.1rem; margin-bottom: 5px;'>Tvůj inteligentní průvodce projektem Kvadr, který ti pomůže v reálném čase odpovědět na otázky ohledně Kvádru a ještě více!</p>", unsafe_allow_html=True)

# DRUHÝ PODNADPIS / VAROVÁNÍ (Šedý a kurzíva)
st.markdown("<p style='color: gray; font-style: italic; font-size: 0.9rem; margin-top: 0px;'>POZOR MOHU DĚLAT CHYBY A NĚKTERÉ INFORMACE S KVÁDREM NEMUSÍM ZNÁT !</p>", unsafe_allow_html=True)

# Historie chatu
if "messages" not in st.session_state:
    st.session_state.messages = []

# Zobrazení zpráv z historie
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Vstup od uživatele
if prompt := st.chat_input("Napiš svou otázku..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Přemýšlím..."):
            # Příprava kontextu (Veřejné + Tajné informace)
            verejne_text = " ".join(data['zprava'].astype(str).tolist()) if not data.empty else ""
            tajne_text = ""
            if 'tajne' in data.columns:
                tajne_text = " ".join(data['tajne'].astype(str).tolist())
            
            # Sestavení dotazu pro AI
            kontext = f"INSTRUKCE PRO TEBE: {tajne_text} | INFORMACE PRO VEŘEJNOST: {verejne_text}"
            url_ai = f"https://generativelanguage.googleapis.com/v1beta/{funkcni_model}:generateContent?key={API_KEY}"
            payload = {
                "contents": [{
                    "parts": [{"text": f"{kontext}\n\nUživatel se ptá: {prompt}"}]
                }]
            }
            
            try:
                res = requests.post(url_ai, json=payload).json()
                odpoved = res['candidates'][0]['content']['parts'][0]['text']
                st.markdown(odpoved)
                st.session_state.messages.append({"role": "assistant", "content": odpoved})
            except Exception as e:
                st.error(f"AI se nepodařilo odpovědět. (Chyba: {e})")

# ==============================================================================
# KONEC KÓDU
# ==============================================================================
