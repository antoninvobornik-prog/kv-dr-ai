import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# ==========================================
# 1. KONFIGURACE A STAV
# ==========================================
st.set_page_config(page_title="Kvádr AI", layout="wide")

if "page" not in st.session_state: st.session_state.page = "Domů"
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "news_index" not in st.session_state: st.session_state.news_index = 0

@st.cache_resource
def najdi_model():
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        dostupne = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return next((n for n in dostupne if '1.5-flash' in n), dostupne[0])
    except: return None

MODEL_ID = najdi_model()

# ==========================================
# 2. POMOCNÉ FUNKCE
# ==========================================
def nacti_data_sheets(nazev_listu, header=None):
    try:
        base_url = st.secrets["GSHEET_URL"]
        sid = base_url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(nazev_listu)}"
        return pd.read_csv(csv_url, header=header)
    except: return pd.DataFrame()

def get_wmo_description(code):
    mapping = {0: "Jasno", 1: "Převážně jasno", 2: "Polojasno", 3: "Zataženo", 45: "Mlha", 61: "Slabý déšť", 71: "Sněžení", 95: "Bouřka"}
    return mapping.get(code, "Oblačno")

@st.cache_data(ttl=1800)
def nacti_kompletni_pocasi():
    mesta = {"Nové Město n. M.": (50.344, 16.151), "Bělá": (50.534, 14.807), "Praha": (50.075, 14.437), "Hradec Králové": (50.210, 15.832)}
    output = {}
    for m, (lat, lon) in mesta.items():
        try:
            res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=auto", timeout=5).json()
            output[m] = {
                "teplota": f"{round(res['current']['temperature_2m'])}°C",
                "stav": get_wmo_description(res['current']['weathercode']),
                "ikona": "☀️" if res['current']['weathercode'] < 3 else "☁️",
                "predpoved": [{"den": (datetime.now() + timedelta(days=i)).strftime("%d.%m."), "stav": get_wmo_description(res['daily']['weathercode'][i]), "teplota": f"{round(res['daily']['temperature_2m_min'][i])}°/{round(res['daily']['temperature_2m_max'][i])}°"} for i in range(5)]
            }
        except: output[m] = {"teplota": "--", "stav": "Nenalezeno", "ikona": "⚠️", "predpoved": []}
    return output

# ==========================================
# 3. DETAILNÍ DESIGN (CSS)
# ==========================================
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #f1f5f9; }
    
    /* Vylepšené karty pro Info */
    .info-card { 
        background: rgba(30, 41, 59, 0.7); 
        backdrop-filter: blur(12px);
        padding: 25px; 
        border-radius: 20px; 
        border: 1px solid rgba(59, 130, 246, 0.3); 
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
        margin-bottom: 25px;
        transition: transform 0.2s;
    }
    .info-card:hover { transform: translateY(-5px); border-color: #3b82f6; }
    
    .info-header { 
        color: #60a5fa; 
        font-size: 1.4rem; 
        font-weight: 800; 
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .news-island { position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%); background: rgba(15, 23, 42, 0.9); border: 1px solid #3b82f6; padding: 10px 20px; border-radius: 20px; z-index: 1000; width: 90%; max-width: 500px; text-align: center; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. NAVIGACE
# ==========================================
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    if st.session_state.page == "Domů":
        if st.button("🗺️ PROZKOUMAT KVÁDR SVĚT", use_container_width=True):
            st.session_state.page = "Info"; st.rerun()
        if st.button("💬 OTEVŘÍT KVÁDR AI CHAT", use_container_width=True, type="primary"):
            st.session_state.page = "AI Chat"; st.rerun()
    else:
        if st.button("🏠 ZPĚT NA ÚVOD", use_container_width=True):
            st.session_state.page = "Domů"; st.rerun()

# ==========================================
# 5. STRÁNKA: DOMŮ
# ==========================================
if st.session_state.page == "Domů":
    st.markdown('<h1 style="text-align:center; font-weight:900; letter-spacing:-1px;">🏙️ KVÁDR PORTÁL</h1>', unsafe_allow_html=True)
    df_oznameni = nacti_data_sheets("List 2", header=0) # Zde necháváme hlavičku pro oznámení
    if not df_oznameni.empty and 'zprava' in df_oznameni.columns:
        for msg in df_oznameni['zprava'].dropna(): st.info(msg)
    
    try:
        res = requests.get("https://ct24.ceskatelevize.cz/rss/hlavni-zpravy", timeout=5)
        root = ET.fromstring(res.content)
        zpravy = [item.find('title').text for item in root.findall('.//item')[:5]]
        idx = st.session_state.news_index % len(zpravy)
        st.markdown(f'<div class="news-island">🗞️ {zpravy[idx]}</div>', unsafe_allow_html=True)
    except: pass
    
    time.sleep(8); st.session_state.news_index += 1; st.rerun()

# ==========================================
# 6. STRÁNKA: INFO (DETAILNÍ DESIGN)
# ==========================================
elif st.session_state.page == "Info":
    df_hist = nacti_data_sheets("List 3", header=None)
    
    if not df_hist.empty:
        # A1 = Nadpis stránky
        hlavni_titulek = str(df_hist.iloc[0, 0]).replace("nan", "Info")
        st.markdown(f'<h1 style="text-align:center; color:#3b82f6;">{hlavni_titulek}</h1>', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🌡️ PŘEDPOVĚĎ", "📄 DETAILNÍ INFO"])
        
        with tab1:
            w_data = nacti_kompletni_pocasi()
            cols = st.columns(2)
            for i, (mesto, d) in enumerate(w_data.items()):
                with cols[i % 2]:
                    st.markdown(f"""
                    <div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:15px; margin-bottom:10px;">
                        <h3 style="margin:0;">{d['ikona']} {mesto}</h3>
                        <h2 style="margin:0; color:#60a5fa;">{d['teplota']}</h2>
                        <p style="opacity:0.8;">{d['stav']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    for f in d['predpoved']:
                        st.write(f"**{f['den']}**: {f['stav']} ({f['teplota']})")
                    st.divider()

        with tab2:
            # Každý řádek od A2 dále
            for i in range(1, len(df_hist)):
                nadpis = str(df_hist.iloc[i, 0]).replace(".0", "").replace("nan", "")
                obsah = str(df_hist.iloc[i, 1]).replace("nan", "")
                
                if nadpis or obsah:
                    st.markdown(f"""
                    <div class="info-card">
                        <div class="info-header">{nadpis}</div>
                        <div style="color: #cbd5e1; font-size: 1.1rem;">{obsah}</div>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.error("Nepodařilo se načíst data z Listu 3.")

# ==========================================
# 7. STRÁNKA: AI CHAT (S KOLEČKEM)
# ==========================================
elif st.session_state.page == "AI Chat":
    st.markdown('<h2 style="text-align:center;">💬 KVÁDR AI</h2>', unsafe_allow_html=True)
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
    if pr := st.chat_input("Napiš něco..."):
        st.session_state.chat_history.append({"role": "user", "content": pr})
        with st.chat_message("user"): st.markdown(pr)
        
        with st.chat_message("assistant"):
            with st.spinner("Kvádr AI přemýšlí..."): # TADY JE TO TOČÍCÍ KOLEČKO
                df_ai = nacti_data_sheets("List 1", header=None)
                ctx = " ".join(df_ai.iloc[:, 0].astype(str).tolist()) if not df_ai.empty else ""
                model = genai.GenerativeModel(MODEL_ID)
                try:
                    res = model.generate_content(f"Jsi asistent Kvádru. Kontext: {ctx}\nUživatel: {pr}")
                    st.markdown(res.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": res.text})
                except Exception as e:
                    st.error(f"AI se unavila: {e}")
