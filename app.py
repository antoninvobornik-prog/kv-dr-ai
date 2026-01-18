import streamlit as st
import time
from datetime import datetime
from duckduckgo_search import DDGS

st.set_page_config(page_title="Chytrý Bot", layout="wide")

if "admin_notes" not in st.session_state:
    st.session_state.admin_notes = ["Bot je připraven."]
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- LEVÁ ČÁST ---
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
st.title("🤖 Normální AI")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if dotaz := st.chat_input("Napiš zprávu..."):
    st.session_state.messages.append({"role": "user", "content": dotaz})
    with st.chat_message("user"):
        st.markdown(dotaz)

    with st.chat_message("assistant"):
        with st.status("Přemýšlím...", expanded=True) as status:
            time.sleep(1)
            d = dotaz.lower()
            
            # --- 1. LIDSKÉ POZDRAVY (Aby nepsal, že nic nenašel) ---
            if d in ["ahoj", "čau", "dobrý den", "zdravím"]:
                odpoved = "Ahoj! Jsem tvůj AI asistent. Můžeš se mě na cokoliv zeptat nebo se podívat na informace vlevo."
            elif "jak se máš" in d:
                odpoved = "Mám se skvěle, zrovna jsem promazal své obvody a jsem připraven ti pomoci!"
            elif "kdo jsi" in d:
                odpoved = "Jsem chatbot, kterého vytvořil Tonda. Umím číst informace vlevo a hledat na internetu."
            
            # --- 2. KONTROLA TVÝCH DAT ---
            elif any(slovo in " ".join(st.session_state.admin_notes).lower() for slovo in d.split() if len(slovo) > 3):
                odpoved = "V mých datech jsem našel toto: " + [n for n in st.session_state.admin_notes if any(s in n.lower() for s in d.split())][0]
            
            # --- 3. VYHLEDÁVÁNÍ NA WEBU ---
            else:
                try:
                    with DDGS() as ddgs:
                        results = list(ddgs.text(dotaz, max_results=3))
                        if results:
                            odpoved = results[0]['body']
                        else:
                            odpoved = "Bohužel jsem o tom nic nenašel v datech ani na webu."
                except:
                    odpoved = "Teď se mi nepodařilo připojit k internetu, zkus to prosím znovu."

            status.update(label="Odpověď hotova!", state="complete", expanded=False)
        
        st.markdown(odpoved)
        st.session_state.messages.append({"role": "assistant", "content": odpoved})
