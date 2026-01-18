import streamlit as st
import time
from datetime import datetime
from duckduckgo_search import DDGS

st.set_page_config(page_title="Chytrý Bot s vyhledáváním", layout="wide")

# Inicializace paměti
if "admin_notes" not in st.session_state:
    st.session_state.admin_notes = ["Vítejte! Přidejte sem informace přes heslo."]
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- LEVÁ ČÁST (ADMIN) ---
with st.sidebar:
    st.header("📌 Vaše data")
    for note in st.session_state.admin_notes:
        st.info(note)
    
    st.divider()
    heslo = st.text_input("Admin heslo", type="password")
    if heslo == "mojeheslo":
        nova_zprava = st.text_area("Nová informace:")
        if st.button("Uložit"):
            st.session_state.admin_notes.append(nova_zprava)
            st.rerun()

# --- HLAVNÍ CHAT ---
st.title("🤖 AI s připojením k internetu")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if dotaz := st.chat_input("Zeptej se mě na cokoliv..."):
    st.session_state.messages.append({"role": "user", "content": dotaz})
    with st.chat_message("user"):
        st.markdown(dotaz)

    with st.chat_message("assistant"):
        with st.status("Prohledávám web a vaše data...", expanded=True) as status:
            time.sleep(1)
            
            # 1. Kontrola tvých dat vlevo
            vsechna_data = " ".join(st.session_state.admin_notes).lower()
            if any(slovo in vsechna_data for slovo in dotaz.lower().split() if len(slovo) > 3):
                odpoved = f"V mých informacích jsem našel shodu! Týká se to tohoto: " + [n for n in st.session_state.admin_notes if any(s in n.lower() for s in dotaz.lower().split())][0]
            
            # 2. Pokud to v datech není, hledá na internetu
            else:
                try:
                    with DDGS() as ddgs:
                        results = list(ddgs.text(dotaz, max_results=3))
                        if results:
                            odpoved = f"Na webu jsem o '{dotaz}' zjistil toto: \n\n" + results[0]['body']
                        else:
                            odpoved = "Bohužel jsem o tom nic nenašel ani na internetu."
                except Exception as e:
                    odpoved = "Omlouvám se, nastala chyba při vyhledávání na webu."

            status.update(label="Hledání dokončeno!", state="complete", expanded=False)
        
        st.markdown(odpoved)
        st.session_state.messages.append({"role": "assistant", "content": odpoved})
