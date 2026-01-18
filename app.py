import streamlit as st
import time

# --- NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="Můj AI Bot", layout="wide")

# Inicializace paměti (aby se zprávy nevymazaly při každém kliknutí)
if "admin_notes" not in st.session_state:
    st.session_state.admin_notes = ["Informace 1: Bot je v testovacím režimu."]
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- LEVÁ ČÁST (SIDEBAR) ---
with st.sidebar:
    st.header("📌 Důležité informace")
    # Zobrazení informací, které uvidí všichni
    for note in st.session_state.admin_notes:
        st.info(note)
    
    st.divider()
    
    # Skrytá sekce pro tebe (Admina)
    heslo = st.text_input("Zadej heslo pro přidání zprávy", type="password")
    if heslo == "mojeheslo":  # TOTO HESLO SI MŮŽEŠ ZMĚNIT
        nova_zprava = st.text_area("Napiš novou informaci:")
        if st.button("Uložit a zveřejnit"):
            st.session_state.admin_notes.append(nova_zprava)
            st.rerun()

# --- HLAVNÍ ČÁST (CHAT) ---
st.title("🤖 Chatbot")

# Zobrazení historie zpráv
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Políčko pro dotaz uživatele
if dotaz := st.chat_input("Zeptej se mě na něco..."):
    st.session_state.messages.append({"role": "user", "content": dotaz})
    with st.chat_message("user"):
        st.markdown(dotaz)

    # Efekt přemýšlení
    with st.chat_message("assistant"):
        with st.status("Přemýšlím a prohledávám tvoje informace...", expanded=True) as status:
            time.sleep(3) # Tady bot "přemýšlí"
            
            # Kontrola souvislosti s tvými informacemi
            vsechny_info = " ".join(st.session_state.admin_notes).lower()
            if any(slovo in dotaz.lower() for slovo in vsechny_info.split()):
                odpoved = f"Našel jsem souvislost s informacemi v levém panelu! K tvému dotazu '{dotaz}' mohu říct, že se to shoduje s mým nastavením."
            else:
                odpoved = "O tomto tématu v mých informacích nic není, zkus se zeptat na něco, co vidíš vlevo."
            
            status.update(label="Mám to!", state="complete", expanded=False)
        
        st.markdown(odpoved)
        st.session_state.messages.append({"role": "assistant", "content": odpoved})
