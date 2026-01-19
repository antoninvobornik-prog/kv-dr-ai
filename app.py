import streamlit as st
import pandas as pd
import requests
import base64

# --- 1. ZÁKLADNÍ NASTAVENÍ (JAKO PŘEDTÍM) ---
st.set_page_config(page_title="KVÁDR AI", layout="wide")

# Název tvého souboru
JMENO_SOUBORU = "pozadí.png.png"

# --- 2. PŘIDÁNÍ POZADÍ A STYLŮ (UPRAVENO PRO CELÉ LOGO) ---
def add_bg_and_styles(image_file):
    try:
        with open(image_file, "rb") as f:
            data = f.read()
        bin_str = base64.b64encode(data).decode()
        
        st.markdown(f"""
        <style>
        /* Pozadí s celým logem (contain) */
        .stApp {{
            background-image: linear-gradient(rgba(0,0,0,0.85), rgba(0,0,0,0.85)), url("data:image/png;base64,{bin_str}");
            background-size: contain;
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-position: center;
            background-color: #0e1117;
        }}
        
        /* Vynucení bílého textu a Dark Mode */
        h1, h2, h3, p, span, div, .stMarkdown {{
            color: #ffffff !important;
        }}
        
        /* Flexbox pro logo a nadpis v jedné řadě */
        .custom-header {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 20px;
        }}
        .custom-header img {{
            width: 50px;
            height: auto;
        }}
        .custom-header div {{
            display: flex;
            flex-direction: column;
        }}
        .custom-header h1 {{
            margin: 0 !important;
            font-size: 1.8rem !important;
        }}
        .custom-header p {{
            margin: 0 !important;
            color: #4facfe !important;
            font-weight: bold;
            letter-spacing: 2px;
            font-size: 0.8rem;
        }}
        </style>
        """, unsafe_allow_html=True)
    except:
        pass

add_bg_and_styles(JMENO_SOUBORU)

# --- 3. LOGIKA DAT (PŮVODNÍ FUNKČNÍ) ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
except:
    st.error("Chybí klíče v Secrets!")
    st.stop()

def nacti_data():
    try:
        sheet_id = GSHEET_URL.split("/d/")[1].split("/")[0]
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=List1"
        return pd.read_csv(url)
    except:
        return pd.DataFrame(columns=['zprava', 'tajne'])

data = nacti_data()

# --- 4. POSTRANNÍ PANEL (PŮVODNÍ FUNKČNÍ STYL) ---
with st.sidebar:
    st.title("📌 Informace")
    if not data.empty and 'zprava' in data.columns:
        for zpr in data['zprava'].dropna():
            st.info(zpr)
    
    if st.button("🗑️ Smazat historii"):
        st.session_state.messages = []
        st.rerun()

# --- 5. HLAVNÍ ČÁST (LOGO + NADPIS V JEDNÉ LINCE) ---
try:
    with open(JMENO_SOUBORU, "rb") as f:
        logo_data = base64.b64encode(f.read()).decode()
    logo_html = f'data:image/png;base64,{logo_data}'
except:
    logo_html = ""

st.markdown(f"""
    <div class="custom-header">
        <img src="{logo_html}">
        <div>
            <h1>KVÁDR</h1>
            <p>AI ASISTENT</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 6. CHAT (PŮVODNÍ FUNKČNÍ LOGIKA) ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Napiš zprávu..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Tady používáme tu verzi URL, která ti fungovala na úplném začátku
        url_ai = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
        
        v_info = " ".join(data['zprava'].dropna().astype(str).tolist())
        t_info = " ".join(data['tajne'].dropna().astype(str).tolist()) if 'tajne' in data.columns else ""
        
        payload = {
            "contents": [{"parts": [{"text": f"Instrukce: {t_info}\nInfo: {v_info}\nDotaz: {prompt}"}]}]
        }
        
        try:
            res = requests.post(url_ai, json=payload).json()
            if 'candidates' in res:
                odpoved = res['candidates'][0]['content']['parts'][0]['text']
                st.markdown(odpoved)
                st.session_state.messages.append({"role": "assistant", "content": odpoved})
            else:
                st.error("AI neodpovídá, zkontroluj nastavení.")
        except:
            st.error("Chyba spojení.")
