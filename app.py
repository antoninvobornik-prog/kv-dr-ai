import streamlit as st
import google.generativeai as genai
# ... další importy ...

# Nastavení modelu - NESMÍ MÍT PŘED SEBOU MEZERU
model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    st.error(f"Chyba nastavení AI: Zkontrolujte API klíč v Secrets. ({e})")

# --- 2. NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="Chytrý Bot s pamětí", layout="wide")

# --- 3. PŘIPOJENÍ KE GOOGLE SHEETS ---
# Vytvoření spojení
conn = st.connection("gsheets", type=GSheetsConnection)

# Funkce pro načtení dat
@st.cache_data(ttl=5) # Obnovuje data každých 5 sekund
def load_data():
    try:
        # Načte tabulku z URL v Secrets
        return conn.read(spreadsheet=st.secrets["GSHEET_URL"], worksheet="0")
    except Exception as e:
        st.error(f"Nepodařilo se načíst Google Tabulku: {e}")
        return pd.DataFrame(columns=["zprava"])

# Načtení dat do proměnné
df = load_data()
# Vyčištění dat od prázdných řádků
admin_notes = df["zprava"].dropna().tolist() if "zprava" in df.columns else []

# Paměť pro aktuální chat (smaže se po obnovení)
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. LEVÝ PANEL (ADMINISTRACE) ---
with st.sidebar:
    st.header("📌 Trvalé informace")
    
    # Zobrazení uložených zpráv z tabulky
    if not admin_notes:
        st.write("V databázi zatím nejsou žádné zprávy.")
    else:
        for note in admin_notes:
            st.info(note)
    
    st.divider()
    
    # Sekce pro přidávání nových zpráv
    heslo = st.text_input("Zadej heslo pro úpravy", type="password")
    if heslo == "mojeheslo":
        nova_zprava = st.text_area("Napiš informaci, kterou si má bot pamatovat:")
        if st.button("Uložit navždy"):
            if nova_zprava:
                try:
                    # Vytvoření nového řádku
                    new_row = pd.DataFrame([{"zprava": nova_zprava}])
                    # Spojení se stávajícími daty
                    updated_df = pd.concat([df, new_row], ignore_index=True)
                    # Odeslání do Google Tabulky
                    conn.update(spreadsheet=st.secrets["GSHEET_URL"], data=updated_df)
                    
                    st.success("Uloženo do Google Tabulky!")
                    st.cache_data.clear() # Vymaže mezipaměť, aby se data hned načetla
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Chyba při zápisu do tabulky: {e}")
                    st.info("Tip: Máte v tabulce v buňce A1 nadpis 'zprava' a je tabulka sdílená jako Editor?")
            else:
                st.warning("Napište nějaký text.")

# --- 5. HLAVNÍ CHAT ---
st.title("🤖 Tvůj AI Asistent")
st.caption("Informace vlevo se berou z Google Tabulky a bot si je pamatuje navždy.")

# Zobrazení historie chatu
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Vstup pro uživatele
if prompt := st.chat_input("Zeptej se mě na cokoliv..."):
    # Přidání zprávy uživatele
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generování odpovědi AI
    with st.chat_message("assistant"):
        with st.spinner("Přemýšlím..."):
            # Složení kontextu pro AI z informací vlevo
            kontext = "\n".join([str(n) for n in admin_notes])
            
            plna_instrukce = f"""
            Jsi užitečný asistent. Zde jsou důležité informace, které ti dal majitel:
            {kontext}
            
            Uživatel se ptá: {prompt}
            
            Odpověz přátelsky a česky. Pokud odpověď najdeš v informacích od majitele, použij je.
            """
            
            try:
                response = model.generate_content(plna_instrukce)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"AI se nepodařilo odpovědět: {e}")
