# --- AI CHAT STRÁNKA (S FUNKČNÍ PAMĚTÍ) ---
elif st.session_state.page == "AI Chat":
    # Hlavička chatu s košem pro smazání historie
    col_t1, col_t2 = st.columns([0.9, 0.1])
    with col_t1:
        st.title("💬 Chat s Kvádr AI")
    with col_t2:
        st.write("##") 
        if st.button("🗑️", help="Vymazat historii"):
            st.session_state.chat_history = []
            st.rerun()
    
    st.caption("Ptejte se na projekt Kvádr, počasí nebo cokoliv ze světa.")

    # Zobrazení historie zpráv
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Napište zprávu..."):
        # Uložení zprávy uživatele do historie
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Kvádr AI přemýšlí..."):
                try:
                    # Příprava dat (počasí a info z listu)
                    w_data = nacti_kompletni_pocasi()
                    p_txt = ""
                    for m, d in w_data.items():
                        pred = ", ".join([f"{x['den']}: {x['teplota']}" for x in d['predpoved'][:3]])
                        p_txt += f"{m} (Dnes: {d['aktualni_teplota']}, Předpověď: {pred}). "
                    
                    df_ai = nacti_data_sheets("List 1")
                    kontext_sheets = " ".join(df_ai['zprava'].astype(str).tolist())
                    
                    # Systémové instrukce (osobnost AI)
                    sys_prompt = (
                        f"Jsi Kvádr AI, asistent organizace Kvádr. "
                        f"DŮLEŽITÉ: Kvádr je náš projekt, NE geometrický tvar. "
                        f"Zdroje dat: {kontext_sheets}. "
                        f"Data o počasí: {p_txt}. "
                        f"Pravidla: 1. Používej data. 2. Používej internet pro věci mimo data. "
                        f"3. Jsi v probíhající konverzaci, reaguj na minulé zprávy."
                    )
                    
                    model = genai.GenerativeModel(
                        model_name=st.session_state.model_name,
                        system_instruction=sys_prompt
                    )
                    
                    # PŘEVOD HISTORIE PRO GEMINI (klíč k paměti)
                    # Gemini vyžaduje roli 'user' a 'model' (místo 'assistant')
                    formatted_history = []
                    for h in st.session_state.chat_history[:-1]: # vezmeme vše kromě aktuální zprávy
                        role = "user" if h["role"] == "user" else "model"
                        formatted_history.append({"role": role, "parts": [h["content"]]})
                    
                    # Spuštění chatu s historií
                    chat_session = model.start_chat(history=formatted_history)
                    res = chat_session.send_message(prompt)
                    
                    if res.text:
                        st.markdown(res.text)
                        st.session_state.chat_history.append({"role": "assistant", "content": res.text})
                        st.rerun()
                except Exception as e:
                    st.error(f"Chyba: {e}")
