import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import time
import streamlit.components.v1 as components

# =================================================================
# 1. KONFIGURACE A EXTRÉMNÍ STYLOVÁNÍ (CSS)
# =================================================================
st.set_page_config(
    page_title="KVÁDR PORTÁL 8.0",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Nastavení Gemini API
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    # Pokud není klíč v secrets, zkusíme ho najít jinde nebo upozornit
    pass

st.markdown("""
<style>
    /* Celkové pozadí a font */
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap');
    
    section[data-testid="stSidebar"] {display: none;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .stApp {
        background: radial-gradient(circle at top, #0a192f 0%, #020617 100%);
        color: #e2e8f0;
        font-family: 'Rajdhani', sans-serif;
    }

    /* Hlavní nadpis portálu */
    .portal-header {
        text-align: center;
        padding: 20px;
        background: linear-gradient(90deg, rgba(0,0,0,0) 0%, rgba(30,58,138,0.5) 50%, rgba(0,0,0,0) 100%);
        border-bottom: 1px solid #1e40af;
        margin-bottom: 25px;
    }
    .portal-header h1 {
        color: #60a5fa;
        text-transform: uppercase;
        letter-spacing: 5px;
        margin: 0;
        font-size: 2.5rem;
        text-shadow: 0 0 15px #3b82f6;
    }

    /* Weather Cards - EXTRÉMNÍ KONTRAST */
    .weather-card {
        background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
        border: 2px solid #3b82f6;
        border-radius: 15px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    .weather-temp {
        font-size: 28px;
        font-weight: 800;
        color: #ffffff !important; /* Čistě bílá pro čitelnost */
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }
    .weather-city {
        color: #93c5fd;
        font-weight: bold;
        font-size: 12px;
        text-transform: uppercase;
    }

    /* Modrá bublina pro zprávy (Fixed bottom) */
    .news-bubble {
        position: fixed;
        bottom: 55px; /* Těch 10 nahoru co jsi chtěl */
        left: 15px;
        right: 15px;
        background: #2563eb; /* Ta hezká modrá */
        color: white;
        padding: 15px 20px;
        border-radius: 20px;
        border: 2px solid #60a5fa;
        z-index: 1000;
        text-align: center;
        box-shadow: 0 -5px 25px rgba(0,0,0,0.6);
        font-weight: 600;
        font-size: 15px;
    }

    /* Design tlačítka AI */
    .stButton>button {
        background: linear-gradient(135deg, #ef4444 0%, #991b1b 100%);
        color: white;
        border: 1px solid #f87171;
        border-radius: 12px;
        padding: 20px;
        font-size: 18px;
        font-weight: bold;
        transition: 0.3s;
        box-shadow: 0 0 20px rgba(239, 68, 68, 0.2);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 25px rgba(239, 68, 68, 0.4);
    }

    /* Chat styling */
    .chat-header {
        background: #1e293b;
        padding: 15px;
        border-radius: 15px 15px 0 0;
        border: 1px solid #334155;
        text-align: center;
        color: #3b82f6;
    }
</style>
""", unsafe_allow_html=True)

# =================================================================
# 2. POMOCNÉ FUNKCE
# =================================================================

def get_weather(city, lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&timezone=auto"
        res = requests.get(url, timeout=5).json()
        temp = round(res['current']['temperature_2m'])
        code = res['current']['weathercode']
        icons = {0:"☀️", 1:"🌤️", 2:"⛅", 3:"☁️", 45:"🌫️", 61:"🌧️", 71:"❄️", 95:"⚡"}
        return temp, icons.get(code, "🌡️")
    except:
        return "--", "❌"

def get_news():
    try:
        rss_url = "https://ct24.ceskatelevize.cz/rss/hlavni-zpravy"
        response = requests.get(rss_url, timeout=5)
        root = ET.fromstring(response.content)
        titles = [item.find('title').text for item in root.findall('.//item')]
        return titles[0] if titles else "Načítám čerstvé zprávy..."
    except:
        return "Zpravodajský kanál je dočasně nedostupný."

# =================================================================
# 3. LOGIKA STRÁNEK
# =================================================================
if "page" not in st.session_state:
    st.session_state.page = "Domů"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- DOMOVSKÁ STRÁNKA ---
if st.session_state.page == "Domů":
    st.markdown('<div class="portal-header"><h1>KVÁDR PORTÁL v8.0</h1></div>', unsafe_allow_html=True)

    # Tlačítko AI
    if st.button("🚀 OTEVŘÍT KVÁDR AI ASISTENTA", use_container_width=True):
        st.session_state.page = "Chat"
        st.rerun()

    st.write("")

    # Počasí buňky
    mesta = {
        "Nové Město": (50.34, 16.15),
        "Rychnov": (50.16, 16.27),
        "Bělá p. B.": (50.53, 14.80),
        "Praha": (50.07, 14.43)
    }
    
    cols = st.columns(4)
    for i, (name, coords) in enumerate(mesta.items()):
        temp, icon = get_weather(name, coords[0], coords[1])
        with cols[i]:
            st.markdown(f"""
                <div class="weather-card">
                    <div class="weather-city">{name}</div>
                    <div class="weather-temp">{temp}°</div>
                    <div style="font-size: 20px;">{icon}</div>
                </div>
            """, unsafe_allow_html=True)

    st.write("")

    # PODROBNÁ PŘEDPOVĚĎ
    with st.expander("📊 DETAILNÍ PŘEDPOVĚĎ PRO VŠECHNA MĚSTA"):
        city_choice = st.selectbox("Vyberte město pro analýzu:", list(mesta.keys()))
        lat, lon = mesta[city_choice]
        
        try:
            res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=auto").json()
            daily = res['daily']
            
            # Formátování tabulky
            df = pd.DataFrame({
                "Den": [datetime.strptime(d, "%Y-%m-%d").strftime("%A %d.%m.") for d in daily['time']],
                "Max Teplota": [f"{t}°C" for t in daily['temperature_2m_max']],
                "Min Teplota": [f"{t}°C" for t in daily['temperature_2m_min']]
            })
            st.table(df)
            st.link_button(f"Otevřít interaktivní radar: {city_choice}", f"https://www.windy.com/{lat}/{lon}")
        except:
            st.error("Nepodařilo se načíst detailní tabulku.")

    # OZNÁMENÍ ZE SHEETU
    st.markdown("### 📌 INTERNÍ OZNÁMENÍ")
    try:
        # Použití tvého odkazu na Google Sheets
        sheet_id = st.secrets["GSHEET_URL"].split("/d/")[1].split("/")[0]
        sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=List%202"
        df_news = pd.read_csv(sheet_url)
        for _, row in df_news.dropna().iterrows():
            st.info(f"**{row['zprava']}**")
    except:
        st.write("Žádná aktuální oznámení.")

    # NEWS TICKER V MODRÉ BUBLINĚ
    aktuální_zprava = get_news()
    st.markdown(f"""
        <div class="news-bubble">
            <span style="opacity: 0.8; font-size: 11px; display: block; margin-bottom: 3px;">AKTUÁLNÍ ZPRÁVY Z DOMOVA I ZE SVĚTA</span>
            {aktuální_zprava}
        </div>
    """, unsafe_allow_html=True)

# --- STRÁNKA CHATU ---
else:
    st.markdown('<div class="chat-header"><h2>🤖 KVÁDR AI INTELLIGENCE</h2></div>', unsafe_allow_html=True)
    
    if st.button("🏠 NÁVRAT NA HLAVNÍ PORTÁL", use_container_width=True):
        st.session_state.page = "Domů"
        st.rerun()

    st.write("")

    # Zobrazení historie
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chatovací vstup
    if prompt := st.chat_input("Napište svůj dotaz pro Kvádr AI..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                model = genai.GenerativeModel('gemini-pro')
                # Přidáme kontext k promptu, aby AI věděla, že je Kvádr asistent
                kvadr_prompt = f"Jsi inteligentní asistent pro portál Kvádr. Odpovídej stručně, věcně a česky. Dotaz uživatele: {prompt}"
                response = model.generate_content(kvadr_prompt)
                full_response = response.text
                st.markdown(full_response)
                st.session_state.chat_history.append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error("AI je momentálně přetížená. Zkuste to za chvíli.")
                # Záložní odpověď pro případ chyby klíče
                # st.write(f"Systémová chyba: {str(e)}")

# =================================================================
# 4. KONEC KÓDU
# =================================================================
