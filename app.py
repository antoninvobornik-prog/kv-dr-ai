import streamlit as st
import pandas as pd
import requests
import json
import time
from gspread_pandas import Spread

# ==============================================================================
# 1. KONFIGURACE STRÁNKY A VZHLEDU
# ==============================================================================
st.set_page_config(
    page_title="Master AI Asistent",
    page_icon="🧠",
    layout="wide"
)

# Vlastní CSS pro hezčí chat a bubliny
st.markdown("""
    <style>
    .stChatMessage { border-radius: 10px; padding: 15px; margin-bottom: 5px; }
    .stAlert { border-radius: 10px; }
    .sidebar-text { font-size: 14px; color: #555; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 2. NAČTENÍ KLÍČŮ (SECRETS)
# ==============================================================================
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    GSHEET_URL = st.secrets["GSHEET_URL"]
except Exception as e:
    st.error("❌ CHYBA: Chybí klíče v nastavení Streamlitu (Secrets).")
    st.stop()

# ==============================================================================
# 3. PRÁCE S GOOGLE TABULKOU (PAMĚŤ)
# ==============================================================================
def nacti_trvale_znalosti():
    """Načte data z Google tabulky. Pokud selže, vrátí prázdnou tabulku."""
    try:
        # Používáme odkaz přímo ze Secrets
        s = Spread(GSHEET_URL)
        # Předpokládáme, že list se jmenuje List1
        df = s.sheet_to_df(sheet='List1', index=None)
        # Ujistíme se, že máme sloupec 'zprava'
        if 'zprava' not in df.columns:
            return pd.DataFrame(columns=['zprava'])
        return df
    except Exception as e:
        # V případě chyby (např. špatná práva k tabulce) nepadá celá appka
        return pd.DataFrame(columns=['zprava'])

def pridej_do_tabulky(text):
    """Přidá nový záznam do Google tabulky."""
    try:
        s = Spread(GSHEET_URL)
        df_aktualni = nacti_trvale_znalosti()
        
        # Vytvoření nového řádku
        novy_df = pd.DataFrame([[str(text)]], columns=['zprava'])
        
        # Spojení a uložení
        df_final = pd.concat([df_aktualni, novy_df], ignore_index=True)
        s.df_to_sheet(df_final, index=False, sheet='List1', replace=True)
        return True
    except Exception as e:
        st.error(f"Nepodařilo se uložit do tabulky: {e}")
        return False

# ==============================================================================
# 4. KOMUNIKACE S GOOGLE AI (GEMINI) - PŘÍMÁ CESTA
# ==============================================================================
def dotaz_na_ai(user_input, kontext_z_tabulky):
    """
    Posílá dotaz přímo na API Googlu bez použití nespolehlivých knihoven.
    Zkouší automaticky různé verze modelů, aby se vyhnul chybě 404.
    """
    # Seznam modelů, které zkusíme (pokud jeden hodí 404, zkusíme druhý)
    modely_k_vyzkouseni = ["gemini-1.5-flash", "gemini-pro"]
    
    posledni_chyba = ""

    for model_name in modely_k_vyzkouseni:
        # POUŽÍVÁME VERZI v1 (STABILNÍ)
        url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent?key={API_KEY}"
        
        headers = {'Content-Type': 'application/json'}
        
        # Sestavení zprávy včetně kontextu z tabulky
        instrukce = f"Jsi inteligentní asistent. Zde jsou tvoje trvalé znalosti: {kontext_z_tabulky}. "
        cely_prompt = f"{instrukce}\n\nUživatel se ptá: {user_input}"
        
        payload = {
            "contents": [{
                "parts": [{"text": cely_prompt}]
            }]
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            data = response.json()

            if response.status_code == 200:
                # Úspěšná odpověď
                return data['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 404:
                # Model nenalezen, zkusíme další v seznamu
                posledni_chyba = data.get('error', {}).get('message', 'Neznámá 404')
                continue
            else:
                return f"Chyba AI ({response.status_code}): {data.get('error', {}).get('message', 'Neznámý problém')}"
        
        except Exception as e:
            return f"Chyba připojení: {e}"

    return f"❌ Ani jeden model (Flash ani Pro) nefunguje. Poslední chyba: {posledni_chyba}"

# ==============================================================================
# 5. UŽIVATELSKÉ ROZHRANÍ (SIDEBAR)
# ==============================================================================
data_z_tabulky = nacti_trvale_znalosti()

with st.sidebar:
    st.title("💾 Paměť Asistenta")
    st.markdown("Tyto informace si AI pamatuje napříč všemi chaty.")
    
    # Zobrazení aktuálních znalostí
    st.subheader("Aktuálně uloženo:")
    if not data_z_tabulky.empty:
        for info in data_z_tabulky['zprava']:
            st.info(info)
    else:
        st.write("V paměti zatím nic není.")

    st.divider()
    
    # Administrace pro přidávání
    st.subheader("➕ Přidat do paměti")
    vlozene_heslo = st.text_input("Zadej heslo (mojeheslo)", type="password")
    
    if vlozene_heslo == "mojeheslo":
        nova_info = st.text_area("Co si má AI pamatovat?", placeholder="Např.: Moje oblíbená barva je modrá.")
        if st.button("Uložit do Google tabulky"):
            if nova_info:
                if pridej_do_tabulky(nova_info):
                    st.success("Uloženo! Restartuji paměť...")
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("Napiš nejdřív nějaký text.")

# ==============================================================================
# 6. HLAVNÍ CHAT OKNO
# ==============================================================================
st.title("🤖 Tvůj Osobní AI Asistent")
st.write("Ptej se na cokoliv. AI využívá znalosti z tvé Google tabulky.")

# Inicializace historie zpráv v prohlížeči
if "messages" not in st.session_state:
    st.session_state.messages = []

# Zobrazení historie chatu
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Vstup od uživatele
if prompt := st.chat_input("Napiš svou otázku..."):
    # Uložení zprávy uživatele
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Reakce AI
    with st.chat_message("assistant"):
        with st.spinner("Hledám odpověď..."):
            # Příprava kontextu z tabulky pro AI
            vsechny_znalosti = " ".join(data_z_tabulky['zprava'].tolist()) if not data_z_tabulky.empty else "Žádné znalosti nejsou k dispozici."
            
            # Volání funkce pro Gemini
            odpoved = dotaz_na_ai(prompt, vsechny_znalosti)
            
            # Zobrazení a uložení odpovědi
            st.markdown(odpoved)
            st.session_state.messages.append({"role": "assistant", "content": odpoved})

# ==============================================================================
# KONEC KÓDU
# ==============================================================================
