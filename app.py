# ==========================================
# KOMPLEXNÍ AI ASISTENT S PAMĚTÍ V TABULCE
# Verze: 2.0 - Stabilní (Anti-404 Edition)
# ==========================================

import streamlit as st
import google.generativeai as genai
import pandas as pd
import time
from gspread_pandas import Spread
from google.api_core import exceptions

# 1. ZÁKLADNÍ KONFIGURACE STREAMLITU
# Nastavení musí být na úplně prvním řádku kódu
st.set_page_config(
    page_title="Můj Profesionální AI Asistent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STYLOVÁNÍ (CSS) ---
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    .stAlert { border-radius: 10px; }
    </style>
    """, unsafe_allow_name=True)

# 2. NAČTENÍ KONFIGURACE ZE SECRETS
# Používáme try-except blok, aby aplikace nespadla při chybějících klíčích
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
except Exception as e:
    st.error("❌ KRITICKÁ CHYBA: Chybí konfigurační údaje v Secrets!")
    st.info("Přejděte do Settings -> Secrets a vložte GOOGLE_API_KEY a GSHEET_URL.")
    st.stop()

# 3. INICIALIZACE GOOGLE AI (GEMINI)
# Používáme transport='rest', což je nejjistější cesta proti chybám 404
try:
    genai.configure(api_key=API_KEY, transport='rest')
    
    # Nastavení generování - omezíme kreativitu pro větší přesnost
    generation_config = {
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 2048,
    }
    
    # Inicializace modelu
    # Poznámka: gemini-1.5-flash je nejrychlejší a nejlevnější
    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        generation_config=generation_config
    )
except Exception as e:
    st.error(f"❌ Chyba při inicializaci Gemini: {e}")
    st.stop()

# 4. FUNKCE PRO PRÁCI S GOOGLE TABULKOU
# Funkce jsou obaleny do cache, aby se tabulka nenačítala při každém kliknutí
def nacti_data_z_tabulky():
    """Načte všechny informace z Google tabulky."""
    try:
        # Připojení k tabulce pomocí odkazu ze Secrets
        s = Spread(GSHEET_URL)
        # Načtení listu s názvem 'List1' (ujisti se, že se tak v Excelu jmenuje!)
        df = s.sheet_to_df(sheet='List1', index=None)
        return df
    except Exception as e:
        # Pokud tabulka neexistuje nebo je prázdná, vrátíme prázdný DataFrame
        return pd.DataFrame(columns=['zprava'])

def uloz_novou_informaci(text):
    """Přidá nový řádek do Google tabulky a uloží ho."""
    try:
        with st.spinner("Ukládám do věčné paměti..."):
            s = Spread(GSHEET_URL)
            df_stary = nacti_data_z_tabulky()
            
            # Vytvoření nového řádku
            novy_radek = pd.DataFrame([[str(text)]], columns=['zprava'])
            
            # Spojení starých dat s novými
            df_novy = pd.concat([df_stary, novy_radek], ignore_index=True)
            
            # Zápis zpět do tabulky (přepíše list čerstvými daty)
            s.df_to_sheet(df_novy, index=False, sheet='List1', replace=True)
            return True
    except Exception as e:
        st.error(f"Chyba při zápisu do tabulky: {e}")
        return False

# 5. LOGIKA UŽIVATELSKÉHO ROZHRANÍ (SIDEBAR)
with st.sidebar:
    st.title("⚙️ Správa paměti")
    st.write("Zde můžete AI naučit nové věci, které si bude pamatovat navždy.")
    
    # Načtení dat pro zobrazení v panelu
    data = nacti_data_z_tabulky()
    
    st.subheader("📌 Co už vím:")
    if not data.empty:
        for i, radek in data.iterrows():
            st.info(radek['zprava'])
    else:
        st.caption("Zatím nemám žádné trvalé znalosti.")

    st.divider()
    
    # Sekce pro přidávání nových informací
    heslo = st.text_input("🔑 Heslo pro úpravy", type="password")
    if heslo == "mojeheslo":
        st.success("Přístup povolen")
        nova_zprava = st.text_area("Napiš informaci k zapamatování:", placeholder="Např.: Moje auto je červené.")
        if st.button("💾 Uložit do AI paměti"):
            if nova_zprava:
                if uloz_novou_informaci(nova_zprava):
                    st.toast("Informace byla uložena!", icon="✅")
                    time.sleep(1) # Krátká pauza pro UI
                    st.rerun() # Refresh stránky pro zobrazení nové info
            else:
                st.warning("Nelze uložit prázdný text.")
    elif heslo != "":
        st.error("Špatné heslo")

# 6. HLAVNÍ CHATOVÉ ROZHRANÍ
st.header("🤖 Tvůj Osobní AI Asistent")
st.caption("Vybaven trvalou pamětí z Google Sheets")

# Inicializace historie chatu v session_state (aby nezmizela při refreshu)
if "messages" not in st.session_state:
    st.session_state.messages = []

# Zobrazení historie zpráv
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Vstup od uživatele
if prompt := st.chat_input("Jak ti mohu dnes pomoci?"):
    # Přidání zprávy uživatele do historie
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generování odpovědi asistenta
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # PŘÍPRAVA KONTEXTU
            # Vezmeme všechna data z tabulky a uděláme z nich úvodní instrukci
            znalosti_seznam = data['zprava'].tolist() if not data.empty else []
            kontext = "Jsi užitečný asistent. Tvoje trvalé znalosti (použij je, pokud jsou relevantní): "
            kontext += " | ".join(znalosti_seznam)
            
            # Sestavení finálního dotazu pro AI
            finalni_dotaz = f"{kontext}\n\nAktuální dotaz uživatele: {prompt}"
            
            # Volání AI s ošetřením chyb
            with st.spinner("Přemýšlím..."):
                response = model.generate_content(finalni_dotaz)
                
                if response.text:
                    full_response = response.text
                else:
                    full_response = "Omlouvám se, ale nepodařilo se mi vygenerovat žádný text."
            
            # Zobrazení odpovědi
            message_placeholder.markdown(full_response)
            
            # Uložení odpovědi do historie
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except exceptions.InvalidArgument as e:
            st.error(f"Chyba: Neplatné parametry (pravděpodobně problém s modelem). {e}")
        except exceptions.ResourceExhausted as e:
            st.error("Chyba: Překročili jste limit požadavků. Počkejte minutu.")
        except Exception as e:
            st.error(f"Neočekávaná chyba: {e}")
            st.info("Tip: Zkuste v pravém horním rohu 'Manage app' -> 'Reboot app'.")

# 7. PATIČKA
st.divider()
st.caption("Vytvořeno s ❤️ jako ultimátní AI pomocník.")
