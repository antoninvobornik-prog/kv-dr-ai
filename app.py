import streamlit as st
import time
from datetime import datetime

# --- NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="Chytrý AI Bot", layout="wide")

if "admin_notes" not in st.session_state:
    st.session_state.admin_notes = ["Dnes je krásný den a bot je připraven."]
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- LEVÁ ČÁST ---
with st.sidebar:
    st.header("📌 Vaše vložené informace")
    for note in st.session_state.admin_notes:
        st.info(note)
    
    st.divider()
    heslo = st.text_input("Admin heslo", type="password")
    if heslo == "mojeheslo":
        nova_zprava = st.text_area("Nová informace pro bota:")
        if st.button("Uložit"):
            st.session_state.admin_notes.append(nova_zprava)
            st.rerun()

# --- HLAVNÍ CHAT ---
st.title("🤖 Inteligentní asistent")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if dotaz := st.chat_input("Napiš zprávu..."):
    st.session_state.messages.append({"role": "user", "content": dotaz})
    with st.chat_message("user"):
        st.markdown(dotaz)

    with st.chat_message("assistant"):
        with st.status("Přemýšlím...", expanded=True) as status:
            time.sleep(2)
            
            # Logika pro speciální dotazy (datum atd.)
            nizky_dotaz = dotaz.lower()
            if "den" in nizky_dotaz or "datum" in nizky_dotaz or "čas" in nizky_dotaz:
                odpoved = f"Dnes je {datetime.now().strftime('%A, %d. %m. %Y')}. Čas je {datetime.now().strftime('%H:%M')}."
            
            # Kontrola tvých informací vlevo
            else:
                nalezeno = False
                for note in st.session_state.admin_notes:
                    if any(slovo in note.lower() for slovo in nizky_dotaz.split() if len(slovo) > 3):
                        odpoved = f"K tvému dotazu jsem v mých informacích našel toto: {note}"
                        nalezeno = True
                        break
                
                if not nalezeno:
                    odpoved = "Omlouvám se, ale o tomto tématu nemám v levém panelu žádné informace a na internetu zatím nemohu vyhledávat bez API klíče."

            status.update(label="Odpověď připravena!", state="complete", expanded=False)
        
        st.markdown(odpoved)
        st.session_state.messages.append({"role": "assistant", "content": odpoved})
