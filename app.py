import streamlit as st
import pandas as pd
import google.generativeai as genai
import base64

# ==============================================================================
# 1. DESIGN A VZHLED (TVŮJ STYL, FIXNÍ LOGO)
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

# ==============================================================================
# 2. NAČTENÍ DAT (PŮVODNÍ FUNKČNÍ LOGIKA)
# ==============================================================================
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
    genai.configure(api_key=API_KEY)
except:
    st.error("Chybí API klíče v Secrets!")
    st.stop()

@st.cache_data
def nacti_data():
    try:
        sheet_id = GSHEET_URL.split("/d/")[1].split("/")[0]
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=List1"
        return pd.read_csv(url)
    except: return pd.DataFrame(columns=['zprava', 'tajne'])

data = nacti_data()

# ==============================================================================
# 3. SIDEBAR (PŮVODNÍ KLASICKÝ)
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
# 4. HLAVIČKA (LOGO VLEVO, TEXT VPRAVO)
# ==============================================================================
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

# ==============================================================================
# 5. CHAT A INTELIGENTNÍ VOLÁNÍ AI (BEZCHYBNÉ)
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
            full_prompt = f"Instrukce: {t_info}\nData: {v_info}\nUživatel: {prompt}"
            
            # --- DETEKCE FUNKČNÍHO MODELU ---
            try:
                # Zkusíme najít jakýkoliv model, který podporuje generování textu
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                
                # Prioritní modely (seřazeno od nejlepších)
                preferred = [
                    'models/gemini-1.5-flash-latest', 
                    'models/gemini-1.5-flash', 
                    'models/gemini-pro'
                ]
                
                target_model = None
                for p in preferred:
                    if p in available_models:
                        target_model = p
                        break
                
                if not target_model and available_models:
                    target_model = available_models[0] # Pokud není v seznamu, vem první dostupný
                
                if target_model:
                    model = genai.GenerativeModel(target_model)
                    response = model.generate_content(full_prompt)
                    
                    if response.text:
                        st.markdown(response.text)
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                    else:
                        st.error("AI vrátilo prázdný výsledek.")
                else:
                    st.error("Ve vašem Google projektu nebyly nalezeny žádné podporované AI modely.")
                    
            except Exception as e:
                st.error(f"Kritická chyba: {str(e)}")
