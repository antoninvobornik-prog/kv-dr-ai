import streamlit as st
import pandas as pd
import google.generativeai as genai
import time
import urllib.parse

# ==========================================
# 1. DESIGN A KONFIGURACE (Tmavý režim)
# ==========================================
st.set_page_config(page_title="KVÁDR AI", layout="wide")

def local_css():
    st.markdown("""
    <style>
        /* Celkové pozadí */
        .stApp {
            background-color: #070b14;
            color: #e0e0e0;
        }
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #0b111e !important;
            border-right: 1px solid #1e293b;
        }
        /* Rámečky pro zprávy na úvodní stránce */
        .news-card {
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        }
        /* Logo a nadpisy */
        .logo-text {
            font-weight: bold;
            font-size: 1.5rem;
            color: white;
            letter-spacing: 2px;
        }
        /* Styl tlačítek v sidebaru */
        .stButton > button {
            width: 100%;
            border-radius: 10px;
            background-color: #1e293b;
            color: white;
            border: 1px solid #334155;
        }
        .stButton > button:hover {
            border-color: #3b82f6;
            color: #3b82f6;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# ==========================================
# 2. FUNKCE PRO NAČÍTÁNÍ TABULEK (S mezerami)
# ==========================================
def nacti_data(nazev_listu):
    try:
        base_url = st.secrets["GSHEET_URL"]
        # Rozsekání URL pro získání ID tabulky
        sheet_id = base_url.split("/d/")[1].split("/")[0]
        # Ošetření mezery v názvu (List 1 -> List%201)
        nazev_opraveny = urllib.parse.quote(nazev_listu)
        # Finální URL pro CSV export s cache-busterem (t={time})
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nazev_opraveny}&t={int(time.time())}"
        
        return pd.read_csv(csv_url)
    except Exception as e:
        return pd.DataFrame(columns=['zprava'])

# ==========================================
# 3. SIDEBAR - NAVIGACE
# ==========================================
if "page" not in st.session_state:
    st.session_state.page = "Domů"

with st.sidebar:
    st.markdown('<div class="logo-text">✦ KVÁDR AI</div>', unsafe_allow_html=True)
    st.write("---")
    
    if st.button("🏠 DOMŮ"):
        st.session_state.page = "Domů"
    
    if st.button("💬 AI CHAT"):
        st.session_state.page = "AI Chat"
    
    st.write("---")
    st.caption("Verze 2.0 | Stabilní připojení")
    st.info("Kvádr AI může dělat chyby. Vše si ověřujte.")

# ==========================================
# 4. STRÁNKA: DOMŮ (Zprávy z List 2)
# ==========================================
if st.session_state.page == "Domů":
    st.title("Oznámení a novinky")
    
    # Načtení zpráv z Google Sheets (List 2)
    with st.spinner("Načítám čerstvé zprávy..."):
        df_zpravy = nacti_data("List 2")
    
    if not df_zpravy.empty:
        for zprava in df_zpravy['zprava'].dropna():
            st.markdown(f"""
                <div class="news-card">
                    {zprava}
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Zatím tu nejsou žádné zprávy. Přidej je do Google tabulky do Listu 2.")

    # Sekce pro administraci
    st.write("---")
    with st.expander("🔐 Správa zpráv"):
        heslo = st.text_input("Zadejte heslo", type="password")
        if heslo == "Heslo123":
            st.success("Jste přihlášen jako správce.")
            st.write("Pro přidání nebo smazání zprávy klikněte na tlačítko níže a upravte tabulku. Změna se projeví po obnovení stránky.")
            st.link_button("Upravit zprávy v Google Tabulce", st.secrets["GSHEET_URL"])
        elif heslo != "":
            st.error("Špatné heslo.")

# ==========================================
# 5. STRÁNKA: AI CHAT (Data z List 1)
# ==========================================
elif st.session_state.page == "AI Chat":
    st.title("💬 Asistent KVÁDR")

    # Načtení znalostí pro AI (List 1)
    df_ai = nacti_data("List 1")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Zobrazení historie
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Vstup od uživatele
    if prompt := st.chat_input("Zeptejte se mě na cokoliv..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("KVÁDR přemýšlí..."):
                try:
                    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    # Příprava kontextu z Listu 1
                    kontext = " ".join(df_ai['zprava'].astype(str).tolist())
                    full_prompt = f"Jsi asistent KVÁDR AI. Zde jsou tvé znalosti: {kontext}. Odpověz na: {prompt}"
                    
                    response = model.generate_content(full_prompt)
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error("Momentálně mám moc práce (limit API). Zkus to za 30 sekund.")
