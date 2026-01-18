import streamlit as st
import pandas as pd
import requests

# ==============================================================================
# 1. DESIGN
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

try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
except:
    st.error("Chybí klíče v Secrets!")
    st.stop()

# ==============================================================================
# 2. CHYTRÁ DETEKCE MODELU (OPRAVENÁ)
# ==============================================================================
@st.cache_resource
def ziskej_funkcni_model():
    """Najde model, který umí generovat text a jmenuje se gemini."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    try:
        res = requests.get(url).json()
        if "models" in res:
            # FILTR: Chceme jen modely Gemini, které umí generovat obsah
            modely = [m["name"] for m in res["models"] 
                      if "gemini" in m["name"] and "generateContent" in m["supportedGenerationMethods"]]
            
            if modely:
                # Priorita pro 1.5-flash, pokud je v seznamu
                for m in modely:
                    if "1.5-flash" in m:
                        return m
                return modely[0] # Jinak vezmi první dostupný Gemini
    except:
        pass
    return "models/gemini-1.5-flash-latest" # Poslední záchrana

MODEL_NAME = ziskej_funkcni_model()

def nacti_data():
    try:
        sheet_id = GSHEET_URL.split("/d/")[1].split("/")[0]
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=List1"
        return pd.read_csv(url)
    except:
        return pd.DataFrame(columns=['zprava', 'tajne'])

data = nacti_data()

# ==============================================================================
# 3. SIDEBAR
# ==============================================================================
with st.sidebar:
    st.title("📌 Informace")
    if not data.empty and 'zprava' in data.columns:
        for zpr in data['zprava'].dropna():
            st.info(zpr)
    st.divider()
    heslo = st.text_input("Správa", type="password")
    if heslo == "mojeheslo":
        st.success(f"Používám model: {MODEL_NAME}")
        if 'tajne' in data.columns:
            for t in data['tajne'].dropna():
                st.warning(t)

# ==============================================================================
# 4. CHAT
# ==============================================================================
st.title("🤖 Kvadr AI Asistent")
st.markdown("<p style='color: white; font-weight: bold; font-size: 1.1rem;'>Tvůj inteligentní průvodce projektem Kvadr, který ti pomůže v reálném čase odpovědět na otázky!</p>", unsafe_allow_html=True)
st.markdown("<p style='color: gray; font-style: italic; font-size: 0.9rem;'>POZOR MOHU DĚLAT CHYBY A NĚKTERÉ INFORMACE NEMUSÍM ZNÁT !</p>", unsafe_allow_html=True)

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
        with st.spinner("Odpovídám..."):
            verejne = " ".join(data['zprava'].dropna().astype(str).tolist())
            tajne = " ".join(data['tajne'].dropna().astype(str).tolist()) if 'tajne' in data.columns else ""
            
            url_ai = f"https://generativelanguage.googleapis.com/v1beta/{MODEL_NAME}:generateContent?key={API_KEY}"
            
            payload = {
                "contents": [{"parts": [{"text": f"KONTEXT: {tajne} {verejne}\n\nUživatel: {prompt}"}]}],
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
                    st.error("Chyba vygenerování odpovědi.")
                    st.json(res)
            except Exception as e:
                st.error(f"Spojení selhalo: {e}")
