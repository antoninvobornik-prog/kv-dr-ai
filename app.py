import streamlit as st
import pandas as pd
import requests
import base64

# --- 1. NASTAVENÍ A DESIGN ---
st.set_page_config(page_title="KVÁDR AI", layout="wide")

JMENO_SOUBORU = "pozadí.png.png"

def inject_styles(image_file):
    try:
        with open(image_file, "rb") as f:
            data = f.read()
        bin_str = base64.b64encode(data).decode()
        
        st.markdown(f"""
        <style>
        /* Pozadí - contain (celé logo bez ořezu) */
        .stApp {{
            background-color: #0e1117;
            background-image: linear-gradient(rgba(0,0,0,0.88), rgba(0,0,0,0.88)), url("data:image/png;base64,{bin_str}");
            background-size: contain;
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-position: center;
        }}
        
        /* Vynucení bílého textu */
        h1, h2, h3, p, span, div, .stMarkdown, label {{
            color: #ffffff !important;
        }}

        /* FIX HLAVIČKY: Logo a název VŽDY vedle sebe */
        .header-container {{
            display: flex;
            flex-direction: row;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
        }}
        .header-container img {{
            width: 45px !important;
            height: auto;
        }}
        .header-container div {{
            display: flex;
            flex-direction: column;
        }}
        .header-container h1 {{
            margin: 0 !important;
            font-size: 1.7rem !important;
            line-height: 1.1 !important;
        }}
        .header-container p {{
            margin: 0 !important;
            color: #4facfe !important;
            font-weight: bold;
            letter-spacing: 2px;
            font-size: 0.8rem !important;
            text-transform: uppercase;
        }}
        </style>
        """, unsafe_allow_html=True)
    except:
        pass

inject_styles(JMENO_SOUBORU)

# --- 2. DATA (PŮVODNÍ FUNKČNÍ) ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
except:
    st.error("⚠️ Chybí klíče v Secrets!")
    st.stop()

def nacti_data():
    try:
        sheet_id = GSHEET_URL.split("/d/")[1].split("/")[0]
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=List1"
        return pd.read_csv(url)
    except:
        return pd.DataFrame(columns=['zprava', 'tajne'])

data = nacti_data()

# --- 3. POSTRANNÍ PANEL (PŮVODNÍ STYL) ---
with st.sidebar:
    st.title("📌 Informace")
    if not data.empty and 'zprava' in data.columns:
        for zpr in data['zprava'].dropna():
            st.info(zpr)
    
    st.divider()
    if st.button("🗑️ Smazat historii"):
        st.session_state.messages = []
        st.rerun()

# --- 4. HLAVNÍ HLAVIČKA ---
try:
    with open(JMENO_SOUBORU, "rb") as f:
        logo_data = base64.b64encode(f.read()).decode()
    logo_src = f'data:image/png;base64,{logo_data}'
except:
    logo_src = ""

st.markdown(f"""
    <div class="header-container">
        <img src="{logo_src}">
        <div>
            <h1>KVÁDR</h1>
            <p>AI ASISTENT</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 5. CHAT A AI LOGIKA ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Napište zprávu pro KVÁDR..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Zkusíme v1beta, která je pro Flash nejčastější
        url_ai = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
        
        v_info = " ".join(data['zprava'].dropna().astype(str).tolist())
        t_info = " ".join(data['tajne'].dropna().astype(str).tolist()) if 'tajne' in data.columns else ""
        
        payload = {
            "contents": [{"parts": [{"text": f"Instrukce: {t_info}\nInfo: {v_info}\nDotaz: {prompt}"}]}]
        }
        
        try:
            response = requests.post(url_ai, json=payload)
            res = response.json()
            
            if 'candidates' in res and len(res['candidates']) > 0:
                odpoved = res['candidates'][0]['content']['parts'][0]['text']
                st.markdown(odpoved)
                st.session_state.messages.append({"role": "assistant", "content": odpoved})
            else:
                # ZOBRAZENÍ CHYBY PRO DIAGNOSTIKU
                if 'error' in res:
                    st.error(f"Chyba od Google: {res['error']['message']}")
                else:
                    st.error("AI neodpovídá. Zkuste to znovu za chvíli.")
        except Exception as e:
            st.error(f"Chyba spojení: {e}")
