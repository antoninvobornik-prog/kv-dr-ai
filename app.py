import streamlit as st
import pandas as pd
import google.generativeai as genai
import base64
import time

# ==============================================================================
# 1. NASTAVENÍ A DESIGN (CSS PRO PŘESNÝ VZHLED)
# ==============================================================================
st.set_page_config(page_title="KVÁDR AI", layout="wide", initial_sidebar_state="expanded")

def inject_styles():
    st.markdown("""
    <style>
    /* Hlavní pozadí a barva textu */
    .stApp {
        background: radial-gradient(circle at center, #101d33 0%, #070b14 100%);
        color: #e0e0e0;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #0b111e !important;
        border-right: 1px solid #1e293b;
        min-width: 250px !important;
    }
    
    /* Sidebar disclaimer - přišpendlený dolů */
    .sidebar-footer {
        position: fixed;
        bottom: 20px;
        left: 20px;
        width: 210px;
        font-size: 0.7rem;
        color: #475569;
        font-style: italic;
    }

    /* Hlavička loga v sidebaru */
    .sidebar-header {
        padding: 10px 0px 30px 0px;
        display: flex;
        align-items: center;
        gap: 15px;
    }
    .logo-box {
        background: linear-gradient(135deg, #3b82f6, #06b6d4);
        width: 40px;
        height: 40px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 0 15px rgba(59, 130, 246, 0.5);
    }

    /* Úprava tlačítek navigace */
    .stButton > button {
        width: 100%;
        background-color: transparent;
        border: none;
        color: #94a3b8;
        text-align: left;
        padding: 10px 15px;
        border-radius: 10px;
        transition: 0.3s;
    }
    .stButton > button:hover {
        background-color: rgba(59, 130, 246, 0.1);
        color: #3b82f6;
    }
    
    /* Aktivní stránka (simulace) */
    .active-nav {
        background-color: rgba(59, 130, 246, 0.2) !important;
        color: #3b82f6 !important;
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
    }

    /* Chat input box - dole */
    .stChatInputContainer {
        padding-bottom: 30px !important;
        background: transparent !important;
    }

    /* Welcome screen v chatu */
    .welcome-container {
        text-align: center;
        margin-top: 100px;
    }
    .welcome-icon {
        font-size: 50px;
        background: rgba(59, 130, 246, 0.1);
        padding: 20px;
        border-radius: 20px;
        display: inline-block;
        margin-bottom: 20px;
        border: 1px solid rgba(59, 130, 246, 0.2);
    }
    
    /* Odstranění dekorace v sidebaru */
    [data-testid="stSidebarNav"] {display: none;}
    </style>
    """, unsafe_allow_html=True)

inject_styles()

# ==============================================================================
# 2. DATA A SESSION STATE (PAMĚŤ APLIKACE)
# ==============================================================================
if "page" not in st.session_state:
    st.session_state.page = "Domů"
if "home_messages" not in st.session_state:
    st.session_state.home_messages = ["Vítejte na domovské stránce Kvádru!", "Zde najdete důležité novinky."]
if "messages" not in st.session_state:
    st.session_state.messages = []

# Načtení klíčů a AI (zůstává stejné)
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
    genai.configure(api_key=API_KEY)
except:
    st.error("Chybí API klíče v Secrets!")
    st.stop()

def nacti_data_pro_ai():
    try:
        sheet_id = GSHEET_URL.split("/d/")[1].split("/")[0]
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=List1&t={int(time.time())}"
        return pd.read_csv(url)
    except: return pd.DataFrame(columns=['zprava', 'tajne'])

data_ai = nacti_data_pro_ai()

# ==============================================================================
# 3. SIDEBAR (NAVIGACE PODLE OBRÁZKU)
# ==============================================================================
with st.sidebar:
    # Logo a Název
    st.markdown("""
        <div class="sidebar-header">
            <div class="logo-box"><span style="color:white; font-weight:bold;">✦</span></div>
            <div>
                <div style="font-weight:bold; font-size:1.2rem; color:white; line-height:1;">KVÁDR</div>
                <div style="font-size:0.7rem; color:#3b82f6; font-weight:bold; letter-spacing:1px;">AI ASISTENT</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Navigační tlačítka
    if st.button("🏠 Domů", key="nav_home", use_container_width=True):
        st.session_state.page = "Domů"
        st.rerun()
    
    if st.button("💬 AI Chat", key="nav_chat", use_container_width=True):
        st.session_state.page = "AI Chat"
        st.rerun()

    # Footer s disclaimerem
    st.markdown("""
        <div class="sidebar-footer">
            Kvádr AI může dělat chyby, takže vše kontrolujte.
        </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# 4. OBSAH STRÁNEK
# ==============================================================================

# --- STRÁNKA: DOMŮ ---
if st.session_state.page == "Domů":
    st.title("🏠 Domovská stránka")
    st.write("Aktuální zprávy a novinky:")
    
    # Zobrazení zpráv
    for i, msg in enumerate(st.session_state.home_messages):
        st.info(msg)
    
    st.divider()
    
    # Administrace (Heslo123)
    with st.expander("🔐 Správa zpráv (pro adminy)"):
        heslo = st.text_input("Zadejte heslo pro úpravy", type="password")
        if heslo == "Heslo123":
            nova_zprava = st.text_area("Napsat novou zprávu na domovskou zeď:")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➕ Přidat zprávu"):
                    if nova_zprava:
                        st.session_state.home_messages.append(nova_zprava)
                        st.rerun()
            with col2:
                index_ke_smazani = st.number_input("Index zprávy ke smazání (0, 1...)", min_value=0, step=1)
                if st.button("🗑️ Smazat zprávu"):
                    if 0 <= index_ke_smazani < len(st.session_state.home_messages):
                        st.session_state.home_messages.pop(int(index_ke_smazani))
                        st.rerun()
        elif heslo != "":
            st.error("Nesprávné heslo.")

# --- STRÁNKA: AI CHAT ---
elif st.session_state.page == "AI Chat":
    # Hlavička chatu podle obrázku
    st.markdown("""
        <div style="display:flex; align-items:center; gap:15px; margin-bottom:20px;">
            <div class="logo-box" style="width:35px; height:35px;">✦</div>
            <div>
                <div style="font-weight:bold; font-size:1.1rem; color:white;">KVÁDR AI Chat</div>
                <div style="font-size:0.7rem; color:#64748b;">AI asistent k vašim službám</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Pokud je chat prázdný, ukážeme uvítání jako na obrázku
    if not st.session_state.messages:
        st.markdown("""
            <div class="welcome-container">
                <div class="welcome-icon">✦</div>
                <h2 style="margin-bottom:10px;">Vítejte v KVÁDR AI</h2>
                <p style="color:#94a3b8;">Jsem váš AI asistent. Zeptejte se mě na cokoliv a rád vám pomohu.</p>
                <p style="font-size:0.8rem; color:#475569; margin-top:30px;">
                   ⓘ Kvádr AI může dělat chyby, takže vše kontrolujte.
                </p>
            </div>
        """, unsafe_allow_html=True)
    
    # Zobrazení historie zpráv
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Napište svou zprávu..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("KVÁDR přemýšlí..."):
                v_info = " ".join(data_ai['zprava'].dropna().astype(str).tolist())
                system_instrukce = f"Jsi KVÁDR AI. Info: {v_info}. Odpovídej stručně a profesionálně."
                
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    response = model.generate_content(f"{system_instrukce}\n\nDotaz: {prompt}")
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error("KVÁDR má teď pauzu (limit). Zkuste to za chvíli.")
