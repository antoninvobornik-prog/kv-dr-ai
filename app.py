import streamlit as st
import pandas as pd
import requests
import base64

# --- 1. DESIGN (BEZ ZMĚN V LOGICE) ---
st.set_page_config(page_title="KVÁDR AI", layout="wide")

JMENO_SOUBORU = "pozadí.png.png"

def inject_styles(image_file):
    try:
        with open(image_file, "rb") as f:
            data = f.read()
        bin_str = base64.b64encode(data).decode()
        st.markdown(f"""
        <style>
        .stApp {{
            background-color: #0e1117;
            background-image: linear-gradient(rgba(0,0,0,0.88), rgba(0,0,0,0.88)), url("data:image/png;base64,{bin_str}");
            background-size: contain;
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-position: center;
        }}
        h1, h2, h3, p, span, div, .stMarkdown, label {{ color: #ffffff !important; }}
        .header-container {{ display: flex; flex-direction: row; align-items: center; gap: 12px; padding-bottom: 20px; }}
        .header-container img {{ width: 45px !important; height: auto; }}
        .header-container h1 {{ margin: 0 !important; font-size: 1.8rem !important; }}
        .header-container p {{ margin: 0 !important; color: #4facfe !important; font-weight: bold; letter-spacing: 2px; font-size: 0.8rem !important; }}
        [data-testid="stSidebar"] {{ background-color: #111111; }}
        </style>
        """, unsafe_allow_html=True)
    except: pass

inject_styles(JMENO_SOUBORU)

# --- 2. DATA (TVÁ PŮVODNÍ FUNKČNÍ LOGIKA) ---
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
    except: return pd.DataFrame(columns=['zprava', 'tajne'])

data = nacti_data()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("📌 Informace")
    if not data.empty and 'zprava' in data.columns:
        for zpr in data['zprava'].dropna():
            st.info(zpr)
    if st.button("🗑️ Smazat historii"):
        st.session_state.messages = []
        st.rerun()

# --- 4. HLAVIČKA ---
try:
    with open(JMENO_SOUBORU, "rb") as f:
        logo_base = base64.b64encode(f.read()).decode()
    logo_src = f'data:image/png;base64,{logo_base}'
except: logo_src = ""

st.markdown(f"""
    <div class="header-container">
        <img src="{logo_src}">
        <div><h1>KVÁDR</h1><p>AI ASISTENT</p></div>
    </div>
""", unsafe_allow_html=True)

# --- 5. CHAT A ROBUSTNÍ VOLÁNÍ MODELŮ ---
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
        v_info = " ".join(data['zprava'].dropna().astype(str).tolist())
        t_info = " ".join(data['tajne'].dropna().astype(str).tolist()) if 'tajne' in data.columns else ""
        payload = {"contents": [{"parts": [{"text": f"Instrukce: {t_info}\nData: {v_info}\nDotaz: {prompt}"}]}]}
        
        # TADY JSOU VŠECHNY MOŽNÉ KOMBINACE, KTERÉ GOOGLE POUŽÍVÁ
        test_urls = [
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={API_KEY}",
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}",
            f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}",
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={API_KEY}",
            f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={API_KEY}"
        ]
        
        success = False
        last_error = ""
        
        for url in test_urls:
            try:
                response = requests.post(url, json=payload, timeout=10)
                res = response.json()
                if 'candidates' in res:
                    odpoved = res['candidates'][0]['content']['parts'][0]['text']
                    st.markdown(odpoved)
                    st.session_state.messages.append({"role": "assistant", "content": odpoved})
                    success = True
                    break
                else:
                    last_error = str(res)
            except Exception as e:
                last_error = str(e)
                continue
        
        if not success:
            st.error(f"Ani jeden model neodpovídá. Poslední chyba: {last_error}")
